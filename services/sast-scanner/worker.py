"""
PSD Cloud – SAST Scanner Worker
Subscribes to scan.sast.requested NATS subjects.
For each job:
  1. Clones the target repository
  2. Runs SonarQube analysis via sonar-scanner-cli
  3. Polls SonarQube API for results
  4. Normalises findings and forwards them to the compliance engine
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

import httpx
import nats
from prometheus_client import Counter, Histogram, start_http_server

# ─── Config ───────────────────────────────────────────────────────────────────

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://scan-orchestrator:8000")
COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://compliance-engine:8000")
SONARQUBE_URL = os.getenv("SONARQUBE_URL", "http://sonarqube:9000")
SONARQUBE_TOKEN = os.getenv("SONARQUBE_TOKEN", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))
SONAR_POLL_TIMEOUT = int(os.getenv("SONAR_POLL_TIMEOUT", "300"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("sast-scanner")

# ─── Metrics ──────────────────────────────────────────────────────────────────

scans_total = Counter("sast_scans_total", "Total SAST scans processed", ["status"])
scan_duration = Histogram("sast_scan_duration_seconds", "SAST scan duration in seconds")

# ─── Severity mapping ─────────────────────────────────────────────────────────

_SONAR_SEVERITY_MAP = {
    "BLOCKER": "CRITICAL",
    "CRITICAL": "HIGH",
    "MAJOR": "MEDIUM",
    "MINOR": "LOW",
    "INFO": "INFO",
}

# ─── Core scan logic ──────────────────────────────────────────────────────────

def _clone_repository(repo_url: str, dest: str) -> bool:
    """Clone the repository using git. Returns True on success."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, dest],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.error("git clone timed out for %s", repo_url)
        return False


def _run_sonar_scanner(source_dir: str, project_key: str) -> bool:
    """Run sonar-scanner-cli against the cloned source directory.
    Returns True on success.
    """
    cmd = [
        "sonar-scanner",
        f"-Dsonar.projectKey={project_key}",
        f"-Dsonar.sources={source_dir}",
        f"-Dsonar.host.url={SONARQUBE_URL}",
        f"-Dsonar.projectBaseDir={source_dir}",
    ]

    if SONARQUBE_TOKEN:
        cmd.append(f"-Dsonar.token={SONARQUBE_TOKEN}")

    # For .NET projects, use dotnet-sonarscanner if a .csproj/.sln is detected
    has_dotnet = any(
        f.endswith((".csproj", ".sln"))
        for root, _, files in os.walk(source_dir)
        for f in files
    )

    if has_dotnet:
        log.info("Detected .NET project – using dotnet sonarscanner")
        begin_cmd = [
            "dotnet", "sonarscanner", "begin",
            f"/k:{project_key}",
            f"/d:sonar.host.url={SONARQUBE_URL}",
        ]
        if SONARQUBE_TOKEN:
            begin_cmd.append(f"/d:sonar.token={SONARQUBE_TOKEN}")

        result = subprocess.run(begin_cmd, cwd=source_dir, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            log.error("sonarscanner begin failed: %s", result.stderr)
            return False

        result = subprocess.run(["dotnet", "build"], cwd=source_dir, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            log.warning("dotnet build had issues: %s", result.stderr)

        result = subprocess.run(
            ["dotnet", "sonarscanner", "end"] + ([f"/d:sonar.token={SONARQUBE_TOKEN}"] if SONARQUBE_TOKEN else []),
            cwd=source_dir, capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    else:
        # Retry sonar-scanner up to 2 times on transient connection errors
        for attempt in range(1, 3):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                return True
            stderr = result.stderr or ""
            if ("Connection reset" in stderr or "EOF reached" in stderr) and attempt < 2:
                log.warning("sonar-scanner failed with transient error (attempt %d/2), retrying in 15s...", attempt)
                time.sleep(15)
                continue
            log.error("sonar-scanner failed (rc=%d)\nSTDOUT: %s\nSTDERR: %s",
                      result.returncode, result.stdout[-2000:], result.stderr[-2000:])
            return False
        return False


def _poll_sonarqube_results(project_key: str) -> list[dict]:
    """Poll SonarQube API until the analysis task completes, then retrieve issues."""
    import urllib.request
    import urllib.error

    headers = {}
    if SONARQUBE_TOKEN:
        import base64
        creds = base64.b64encode(f"{SONARQUBE_TOKEN}:".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"

    # Wait for the analysis to complete
    deadline = time.time() + SONAR_POLL_TIMEOUT
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"{SONARQUBE_URL}/api/ce/component?component={project_key}",
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                queue = data.get("queue", [])
                current = data.get("current", {})

                if current.get("status") == "SUCCESS" and not queue:
                    break
                if current.get("status") == "FAILED":
                    log.error("SonarQube analysis task failed for %s", project_key)
                    return []
        except urllib.error.URLError:
            pass
        time.sleep(5)

    # Retrieve all issues
    findings = []
    page = 1
    while True:
        try:
            url = (
                f"{SONARQUBE_URL}/api/issues/search"
                f"?componentKeys={project_key}&ps=500&p={page}"
                f"&types=VULNERABILITY,BUG,CODE_SMELL"
                f"&statuses=OPEN,CONFIRMED,REOPENED"
            )
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                issues = data.get("issues", [])

                for issue in issues:
                    findings.append({
                        "rule_id": issue.get("rule", ""),
                        "severity": _SONAR_SEVERITY_MAP.get(issue.get("severity", "INFO"), "INFO"),
                        "message": issue.get("message", ""),
                        "file": issue.get("component", "").split(":")[-1] if issue.get("component") else "",
                        "line_start": issue.get("line"),
                        "line_end": issue.get("textRange", {}).get("endLine"),
                        "cwe": _extract_cwe(issue),
                        "category": issue.get("type", "VULNERABILITY"),
                        "effort": issue.get("effort", ""),
                        "tags": issue.get("tags", []),
                        "source": "sonarqube",
                    })

                total = data.get("total", 0)
                if page * 500 >= total:
                    break
                page += 1
        except Exception as exc:
            log.warning("Failed to fetch SonarQube issues page %d: %s", page, exc)
            break

    return findings


def _extract_cwe(issue: dict) -> str:
    """Extract CWE ID from SonarQube issue tags (e.g., 'cwe-89' → 'CWE-89')."""
    for tag in issue.get("tags", []):
        if tag.startswith("cwe"):
            return tag.upper().replace("CWE", "CWE-") if "-" not in tag else tag.upper()
    return ""


async def _process_job(job: dict) -> None:
    scan_id = job["scan_id"]
    repo_url = job.get("repository_url")
    project_name = job.get("project_name", scan_id)

    if not repo_url:
        log.warning("Scan %s has no repository_url – skipping SAST", scan_id)
        return

    # Use scan_id as SonarQube project key for uniqueness
    project_key = f"psd-{project_name}-{scan_id[:8]}".replace(" ", "-").lower()

    log.info("Starting SAST scan for scan_id=%s repo=%s project_key=%s", scan_id, repo_url, project_key)

    with scan_duration.time():
        tmpdir = tempfile.mkdtemp(prefix="psd_sast_")
        try:
            cloned = _clone_repository(repo_url, tmpdir)
            if not cloned:
                scans_total.labels(status="failed").inc()
                await _notify_failure(scan_id, "Repository clone failed")
                return

            success = _run_sonar_scanner(tmpdir, project_key)
            if not success:
                scans_total.labels(status="failed").inc()
                await _notify_failure(scan_id, "SonarQube scanner execution failed")
                return

            # Poll for results from SonarQube API
            findings = _poll_sonarqube_results(project_key)
            scans_total.labels(status="success").inc()
            log.info("Scan %s complete – %d findings from SonarQube", scan_id, len(findings))

            # Forward findings to the compliance engine
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{COMPLIANCE_URL}/compliance/evaluate",
                    json={
                        "scan_id": scan_id,
                        "scan_type": "sast",
                        "findings": findings,
                    },
                )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


async def _notify_failure(scan_id: str, reason: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{ORCHESTRATOR_URL}/scans/{scan_id}/result",
            json={"scan_id": scan_id, "status": "failed", "error_message": reason},
        )


# ─── NATS subscription ────────────────────────────────────────────────────────

async def main() -> None:
    start_http_server(METRICS_PORT)
    log.info("SAST Scanner worker starting (SonarQube), connecting to NATS at %s", NATS_URL)

    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    # Ensure stream exists
    try:
        await js.add_stream(name="SCANS", subjects=["scan.>"])
    except Exception:
        pass

    async def handler(msg):
        try:
            job = json.loads(msg.data.decode())

            # Run the scan in a background task while sending periodic
            # in_progress acks so NATS does not redeliver during long scans.
            task = asyncio.create_task(_process_job(job))
            while not task.done():
                await msg.in_progress()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=15)
                except asyncio.TimeoutError:
                    pass  # scan still running – loop and send another in_progress
            # Re-raise any exception from the task
            task.result()
            await msg.ack()
        except Exception as exc:
            log.exception("Error processing SAST job: %s", exc)
            await msg.nak()

    # Delete stale consumer if it exists (config may have changed)
    try:
        await js.delete_consumer("SCANS", "sast-scanner-worker")
    except Exception:
        pass

    await js.subscribe(
        "scan.sast.requested",
        durable="sast-scanner-worker",
        cb=handler,
        config=nats.js.api.ConsumerConfig(
            ack_wait=120,           # 2 min ack window (in_progress resets this)
            max_deliver=3,          # give up after 3 attempts
            max_ack_pending=1,      # process one scan at a time
        ),
    )

    log.info("SAST Scanner worker subscribed and ready")
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
