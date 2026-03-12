"""
PSD Cloud – Notification Service
Sends scan completion notifications via registered webhooks.
Supports webhook (HTTP POST) and future extensibility for email/Slack.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from prometheus_fastapi_instrumentator import Instrumentator

log = logging.getLogger("notification-service")

# In-memory webhook registry (replace with DB persistence in production)
_webhooks: dict[str, list[str]] = {}

app = FastAPI(title="PSD Cloud – Notification Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class WebhookRegistration(BaseModel):
    scan_id: str | None = None   # None = global (all scans)
    url: str


class NotifyRequest(BaseModel):
    scan_id: str
    event: str                   # e.g. "scan.completed", "scan.failed"
    compliance_score: float | None = None
    report_url: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification-service"}


@app.post("/webhooks/register", status_code=201)
async def register_webhook(payload: WebhookRegistration):
    """Register a webhook URL to be called when a scan (or any scan) completes."""
    key = payload.scan_id or "__global__"
    _webhooks.setdefault(key, [])
    if payload.url not in _webhooks[key]:
        _webhooks[key].append(payload.url)
    return {"registered": True, "key": key, "url": payload.url}


@app.post("/notify")
async def notify(payload: NotifyRequest):
    """Dispatch notification to all registered webhooks for this scan."""
    targets = (
        _webhooks.get(payload.scan_id, []) +
        _webhooks.get("__global__", [])
    )

    body = {
        "event": payload.event,
        "scan_id": payload.scan_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compliance_score": payload.compliance_score,
        "report_url": payload.report_url,
        "error_message": payload.error_message,
        **(payload.metadata or {}),
    }

    results = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in targets:
            try:
                resp = await client.post(url, json=body)
                results.append({"url": url, "status": resp.status_code})
                log.info("Notified %s for scan %s → %d", url, payload.scan_id, resp.status_code)
            except Exception as exc:
                results.append({"url": url, "error": str(exc)})
                log.warning("Failed to notify %s for scan %s: %s", url, payload.scan_id, exc)

    return {"dispatched": len(targets), "results": results}
