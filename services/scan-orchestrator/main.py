"""
PSD Cloud – Scan Orchestrator
Manages scan lifecycle: accepts scan requests, publishes jobs to NATS,
tracks status in PostgreSQL, and receives result callbacks.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from prometheus_fastapi_instrumentator import Instrumentator

from models import Base, Scan, ScanStatus, ScanType
from nats_queue import publish_scan_job, close as close_nats

# ─── Config ───────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://psd:psd_secret@localhost:5432/psd_cloud")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="PSD Cloud – Scan Orchestrator", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown():
    await close_nats()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateScanRequest(BaseModel):
    project_name: str
    scan_type: ScanType = ScanType.FULL
    repository_url: str | None = None   # Required for SAST
    target_url: str | None = None       # Required for DAST
    # user_id is injected by the gateway from JWT payload via X-User-ID header


class ScanResponse(BaseModel):
    id: str
    user_id: str
    project_name: str
    scan_type: str
    status: str
    repository_url: str | None
    target_url: str | None
    compliance_score: float | None
    findings_summary: dict | None
    report_url: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class ScanResultCallback(BaseModel):
    scan_id: str
    status: ScanStatus
    findings_summary: dict | None = None
    compliance_score: float | None = None
    report_url: str | None = None
    error_message: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


def _to_response(scan: Scan) -> ScanResponse:
    return ScanResponse(
        id=scan.id, user_id=scan.user_id, project_name=scan.project_name,
        scan_type=scan.scan_type, status=scan.status,
        repository_url=scan.repository_url, target_url=scan.target_url,
        compliance_score=scan.compliance_score, findings_summary=scan.findings_summary,
        report_url=scan.report_url,
        created_at=scan.created_at, started_at=scan.started_at,
        completed_at=scan.completed_at, error_message=scan.error_message,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "scan-orchestrator"}


@app.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: CreateScanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    # User ID is forwarded by the API Gateway as a header
    # In a real deployment this would come from the verified JWT via gateway middleware
):
    # Validate inputs per scan type
    if payload.scan_type in (ScanType.SAST, ScanType.FULL) and not payload.repository_url:
        raise HTTPException(status_code=400, detail="repository_url is required for SAST scans")
    if payload.scan_type in (ScanType.DAST, ScanType.FULL) and not payload.target_url:
        raise HTTPException(status_code=400, detail="target_url is required for DAST scans")

    scan = Scan(
        user_id="system",   # Replaced by gateway-injected user ID in production
        project_name=payload.project_name,
        scan_type=payload.scan_type.value,
        repository_url=payload.repository_url,
        target_url=payload.target_url,
        status=ScanStatus.PENDING.value,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Publish jobs to NATS
    job_payload = {
        "scan_id": scan.id,
        "project_name": scan.project_name,
        "repository_url": scan.repository_url,
        "target_url": scan.target_url,
    }

    if payload.scan_type in (ScanType.SAST, ScanType.FULL):
        await publish_scan_job("scan.sast.requested", job_payload)
    if payload.scan_type in (ScanType.DAST, ScanType.FULL):
        await publish_scan_job("scan.dast.requested", job_payload)

    # Mark as running
    scan.status = ScanStatus.RUNNING.value
    scan.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(scan)

    return _to_response(scan)


@app.get("/scans", response_model=list[ScanResponse])
async def list_scans(db: Annotated[AsyncSession, Depends(get_db)], limit: int = 50, offset: int = 0):
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(limit).offset(offset))
    return [_to_response(s) for s in result.scalars()]


@app.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _to_response(scan)


@app.post("/scans/{scan_id}/result")
async def update_scan_result(scan_id: str, payload: ScanResultCallback, db: Annotated[AsyncSession, Depends(get_db)]):
    """Internal callback endpoint – called by compliance-engine after results are processed."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan.status = payload.status.value
    if payload.findings_summary:
        scan.findings_summary = payload.findings_summary
    if payload.compliance_score is not None:
        scan.compliance_score = payload.compliance_score
    if payload.report_url:
        scan.report_url = payload.report_url
    if payload.error_message:
        scan.error_message = payload.error_message
    if payload.status in (ScanStatus.COMPLETED, ScanStatus.FAILED):
        scan.completed_at = datetime.utcnow()

    await db.commit()
    return {"status": "updated"}
