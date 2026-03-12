"""
PSD Cloud – DAST Scanner Worker
Subscribes to scan.dast.requested NATS subjects.
For each job:
  1. Triggers OWASP ZAP spider + active scan against the target URL
  2. Retrieves findings via the ZAP REST API
  3. Forwards structured findings to the compliance engine
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

import httpx
import nats
from prometheus_client import Counter, Histogram, start_http_server

# ─── Config ───────────────────────────────────────────────────────────────────

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://scan-orchestrator:8000")
COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://compliance-engine:8000")
ZAP_BASE_URL = os.getenv("ZAP_BASE_URL", "http://zap:8080")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "zap-dev-key")
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))

SPIDER_TIMEOUT_SECS = int(os.getenv("SPIDER_TIMEOUT_SECS", "120"))
SCAN_TIMEOUT_SECS = int(os.getenv("SCAN_TIMEOUT_SECS", "300"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("dast-scanner")

scans_total = Counter("dast_scans_total", "Total DAST scans processed", ["status"])
scan_duration = Histogram("dast_scan_duration_seconds", "DAST scan duration in seconds")


# ─── ZAP REST API client ──────────────────────────────────────────────────────

class ZapClient:
    def __init__(self, base_url: str, api_key: str):
        self.base = base_url
        self.key = api_key

    async def _get(self, client: httpx.AsyncClient, path: str, **params) -> dict:
        params["apikey"] = self.key
        resp = await client.get(f"{self.base}{path}", params=params, timeout=120.0)
        resp.raise_for_status()
        return resp.json()

    async def spider_scan(self, client: httpx.AsyncClient, target_url: str) -> str:
        data = await self._get(client, "/JSON/spider/action/scan/", url=target_url)
        return data.get("scan", "0")

    async def spider_status(self, client: httpx.AsyncClient, scan_id: str) -> int:
        data = await self._get(client, "/JSON/spider/view/status/", scanId=scan_id)
        return int(data.get("status", 0))

    async def set_scan_strength(self, client: httpx.AsyncClient, strength: str) -> None:
        """Set active scan strength: LOW, MEDIUM, HIGH, INSANE."""
        policy_id = 0
        for scanner in (await self._get(client, "/JSON/ascan/view/scanners/", policyId=str(policy_id))).get("scanners", []):
            await self._get(
                client, "/JSON/ascan/action/setScannerAlertThreshold/",
                id=scanner["id"], alertThreshold="DEFAULT", scanPolicyName=""
            )
            await self._get(
                client, "/JSON/ascan/action/setScannerAttackStrength/",
                id=scanner["id"], attackStrength=strength, scanPolicyName=""
            )
        log.info("ZAP scan strength set to %s", strength)

    async def active_scan(self, client: httpx.AsyncClient, target_url: str) -> str:
        data = await self._get(client, "/JSON/ascan/action/scan/", url=target_url)
        return data.get("scan", "0")

    async def active_scan_status(self, client: httpx.AsyncClient, scan_id: str) -> int:
        data = await self._get(client, "/JSON/ascan/view/status/", scanId=scan_id)
        return int(data.get("status", 0))

    async def import_openapi(self, client: httpx.AsyncClient, spec_url: str, target_url: str) -> None:
        """Import an OpenAPI/Swagger spec so ZAP discovers API endpoints."""
        await self._get(client, "/JSON/openapi/action/importUrl/", url=spec_url, hostOverride="")
        log.info("Imported OpenAPI spec from %s", spec_url)

    async def get_alerts(self, client: httpx.AsyncClient, target_url: str) -> list[dict]:
        data = await self._get(client, "/JSON/alert/view/alerts/", baseurl=target_url)
        return data.get("alerts", [])


_SEVERITY_ORDER = {"HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFORMATIONAL": 1}

# ZAP self-diagnostic alerts that are not findings in the target application
_EXCLUDED_PLUGIN_IDS = {"10116"}  # "ZAP is Out of Date"


def _normalise_alert(alert: dict) -> dict:
    # ZAP returns "risk" as a string: "High", "Medium", "Low", "Informational"
    raw_risk = alert.get("risk", "Informational").upper()
    return {
        "rule_id": alert.get("pluginId", ""),
        "name": alert.get("name", ""),
        "severity": raw_risk,
        "confidence": alert.get("confidence", "").upper(),
        "description": alert.get("description", ""),
        "url": alert.get("url", ""),
        "param": alert.get("param", ""),
        "evidence": alert.get("evidence", ""),
        "solution": alert.get("solution", ""),
        "cwe": alert.get("cweid", ""),
        "wasc": alert.get("wascid", ""),
        "source": "zap",
    }


def _deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Group findings by rule_id, keeping the highest severity instance
    and collecting all affected URLs as instances."""
    grouped: dict[str, dict] = {}
    for f in findings:
        rid = f["rule_id"]
        if rid not in grouped:
            grouped[rid] = {**f, "instances": [{"url": f["url"], "param": f["param"], "evidence": f["evidence"]}]}
        else:
            existing = grouped[rid]
            existing["instances"].append({"url": f["url"], "param": f["param"], "evidence": f["evidence"]})
            if _SEVERITY_ORDER.get(f["severity"], 0) > _SEVERITY_ORDER.get(existing["severity"], 0):
                existing["severity"] = f["severity"]
            if f.get("confidence", "") and not existing.get("confidence", ""):
                existing["confidence"] = f["confidence"]
    for entry in grouped.values():
        entry["instance_count"] = len(entry["instances"])
    return list(grouped.values())


async def _process_job(job: dict, msg=None) -> None:
    scan_id = job["scan_id"]
    target_url = job.get("target_url")

    if not target_url:
        log.warning("Scan %s has no target_url – skipping DAST", scan_id)
        return

    scan_strength = job.get("scan_strength", "HIGH").upper()
    if scan_strength not in ("LOW", "MEDIUM", "HIGH", "INSANE"):
        scan_strength = "LOW"

    log.info("Starting DAST scan for scan_id=%s target=%s strength=%s", scan_id, target_url, scan_strength)
    zap = ZapClient(ZAP_BASE_URL, ZAP_API_KEY)

    with scan_duration.time():
        async with httpx.AsyncClient() as client:
            try:
                # Configure scan strength
                await zap.set_scan_strength(client, scan_strength)

                # Try to import OpenAPI/Swagger spec for API targets
                for swagger_path in ["/swagger/v1/swagger.json", "/swagger.json", "/openapi.json"]:
                    try:
                        probe = await client.get(f"{target_url.rstrip('/')}{swagger_path}", timeout=5.0)
                        if probe.status_code == 200:
                            await zap.import_openapi(client, f"{target_url.rstrip('/')}{swagger_path}", target_url)
                            break
                    except Exception:
                        continue

                # Spider phase
                spider_id = await zap.spider_scan(client, target_url)
                deadline = time.time() + SPIDER_TIMEOUT_SECS
                while time.time() < deadline:
                    progress = await zap.spider_status(client, spider_id)
                    if progress >= 100:
                        break
                    if msg:
                        await msg.in_progress()
                    await asyncio.sleep(5)

                # Active scan phase
                ascan_id = await zap.active_scan(client, target_url)
                deadline = time.time() + SCAN_TIMEOUT_SECS
                while time.time() < deadline:
                    progress = await zap.active_scan_status(client, ascan_id)
                    if progress >= 100:
                        break
                    if msg:
                        await msg.in_progress()
                    await asyncio.sleep(10)

                # Collect findings
                alerts = await zap.get_alerts(client, target_url)
                alerts = [a for a in alerts if a.get("pluginId") not in _EXCLUDED_PLUGIN_IDS]
                raw_findings = [_normalise_alert(a) for a in alerts]
                findings = _deduplicate_findings(raw_findings)
                scans_total.labels(status="success").inc()
                log.info("DAST scan %s complete – %d raw alerts, %d unique findings", scan_id, len(raw_findings), len(findings))

                # Forward to compliance engine
                await client.post(
                    f"{COMPLIANCE_URL}/compliance/evaluate",
                    json={
                        "scan_id": scan_id,
                        "scan_type": "dast",
                        "findings": findings,
                    },
                    timeout=30.0,
                )

            except Exception as exc:
                scans_total.labels(status="failed").inc()
                log.exception("DAST scan %s failed: %s", scan_id, exc)
                await _notify_failure(scan_id, str(exc))


async def _notify_failure(scan_id: str, reason: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{ORCHESTRATOR_URL}/scans/{scan_id}/result",
            json={"scan_id": scan_id, "status": "failed", "error_message": reason},
        )


# ─── NATS subscription ────────────────────────────────────────────────────────

async def main() -> None:
    start_http_server(METRICS_PORT)
    log.info("DAST Scanner worker starting, connecting to NATS at %s", NATS_URL)

    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    try:
        await js.add_stream(name="SCANS", subjects=["scan.>"])
    except Exception:
        pass

    async def handler(msg):
        try:
            job = json.loads(msg.data.decode())
            await _process_job(job, msg)
            await msg.ack()
        except Exception as exc:
            log.exception("Error processing DAST job: %s", exc)
            await msg.nak()

    await js.subscribe(
        "scan.dast.requested",
        durable="dast-scanner-worker",
        cb=handler,
    )

    log.info("DAST Scanner worker subscribed and ready")
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
