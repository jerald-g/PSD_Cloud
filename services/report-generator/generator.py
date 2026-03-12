"""
PSD Cloud – Report Generator
Receives enriched scan results from the compliance engine,
renders an HTML report using Jinja2, and stores it in MinIO.
Also serves the report as a downloadable artifact.
"""
from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

log = logging.getLogger("report-generator")

# ─── Config ───────────────────────────────────────────────────────────────────

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "psd-reports")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://notification-service:8000")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://scan-orchestrator:8000")

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# ─── Jinja2 ───────────────────────────────────────────────────────────────────

jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

# ─── MinIO client ─────────────────────────────────────────────────────────────

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def _ensure_bucket() -> None:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="PSD Cloud – Report Generator", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
async def startup():
    try:
        _ensure_bucket()
    except Exception as exc:
        log.warning("Could not initialise MinIO bucket: %s", exc)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    scan_id: str
    scan_type: str
    compliance_score: float
    findings_summary: dict[str, Any]
    enriched_findings: list[dict[str, Any]]
    project_name: str | None = None


# ─── Core logic ───────────────────────────────────────────────────────────────

_OWASP_NAMES = {
    "A01:2021": "Broken Access Control",
    "A02:2021": "Cryptographic Failures",
    "A03:2021": "Injection",
    "A04:2021": "Insecure Design",
    "A05:2021": "Security Misconfiguration",
    "A06:2021": "Vulnerable & Outdated Components",
    "A07:2021": "Auth Failures",
    "A08:2021": "Software & Data Integrity Failures",
    "A09:2021": "Logging & Monitoring Failures",
    "A10:2021": "Server-Side Request Forgery",
}


def _render_html(data: GenerateRequest) -> str:
    template = jinja_env.get_template("report.html.j2")
    severity_counts = data.findings_summary.get("by_severity", {})
    owasp_counts = data.findings_summary.get("by_owasp", {})

    return template.render(
        scan_id=data.scan_id,
        project_name=data.project_name or data.scan_id,
        scan_type=data.scan_type,
        compliance_score=data.compliance_score,
        total_findings=data.findings_summary.get("total", len(data.enriched_findings)),
        severity_counts=severity_counts,
        owasp_counts=owasp_counts,
        owasp_names=_OWASP_NAMES,
        findings=data.enriched_findings,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _upload_to_minio(scan_id: str, content: bytes, content_type: str, extension: str) -> str:
    object_name = f"{scan_id}/report.{extension}"
    try:
        minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
    except S3Error as exc:
        log.error("MinIO upload failed: %s", exc)
        raise
    return f"minio://{MINIO_BUCKET}/{object_name}"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "report-generator"}


@app.post("/reports/generate")
async def generate_report(payload: GenerateRequest):
    """Generate HTML + JSON reports and store in MinIO."""
    html = _render_html(payload)
    html_bytes = html.encode("utf-8")
    json_bytes = json.dumps({
        "scan_id": payload.scan_id,
        "scan_type": payload.scan_type,
        "compliance_score": payload.compliance_score,
        "findings_summary": payload.findings_summary,
        "findings": payload.enriched_findings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2).encode("utf-8")

    html_url = _upload_to_minio(payload.scan_id, html_bytes, "text/html", "html")
    json_url = _upload_to_minio(payload.scan_id, json_bytes, "application/json", "json")

    # Update orchestrator with report URL
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{ORCHESTRATOR_URL}/scans/{payload.scan_id}/result",
            json={
                "scan_id": payload.scan_id,
                "status": "completed",
                "report_url": html_url,
            },
        )
        # Notify
        await client.post(
            f"{NOTIFICATION_URL}/notify",
            json={
                "scan_id": payload.scan_id,
                "event": "scan.completed",
                "compliance_score": payload.compliance_score,
                "report_url": html_url,
            },
        )

    return {"html_url": html_url, "json_url": json_url}


@app.get("/reports/{scan_id}/html")
async def download_html(scan_id: str):
    """Stream the HTML report from MinIO."""
    object_name = f"{scan_id}/report.html"
    try:
        resp = minio_client.get_object(MINIO_BUCKET, object_name)
        content = resp.read()
        return Response(content=content, media_type="text/html")
    except S3Error:
        raise HTTPException(status_code=404, detail="Report not found")


@app.get("/reports/{scan_id}/json")
async def download_json(scan_id: str):
    """Stream the JSON report from MinIO."""
    object_name = f"{scan_id}/report.json"
    try:
        resp = minio_client.get_object(MINIO_BUCKET, object_name)
        content = resp.read()
        return Response(content=content, media_type="application/json")
    except S3Error:
        raise HTTPException(status_code=404, detail="Report not found")
