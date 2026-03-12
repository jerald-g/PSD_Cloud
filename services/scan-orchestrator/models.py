import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanType(str, Enum):
    SAST = "sast"
    DAST = "dast"
    FULL = "full"    # SAST + DAST


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ScanType.FULL)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ScanStatus.PENDING, index=True)

    # Source for SAST – git repository URL or upload path
    repository_url: Mapped[str] = mapped_column(Text, nullable=True)
    # Target for DAST – application URL
    target_url: Mapped[str] = mapped_column(Text, nullable=True)

    # Aggregated results written back by the compliance engine
    findings_summary: Mapped[dict] = mapped_column(JSON, nullable=True)
    compliance_score: Mapped[float] = mapped_column(nullable=True)
    report_url: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
