import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    stopped = "stopped"


class RecordStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mapping_template_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("mapping_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="runstatus"),
        default=RunStatus.pending,
        nullable=False,
    )
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mapping_template: Mapped[Optional[Any]] = relationship(
        "MappingTemplate", back_populates="sync_runs", lazy="select"
    )
    records: Mapped[List["SyncRecord"]] = relationship(
        "SyncRecord",
        back_populates="run",
        order_by="SyncRecord.id",
        lazy="select",
    )
    log_entries: Mapped[List["LogEntry"]] = relationship(
        "LogEntry",
        back_populates="run",
        order_by="LogEntry.created_at",
        lazy="select",
    )


class SyncRecord(Base):
    __tablename__ = "sync_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sync_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tririga_record_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    kontracts_record_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="recordstatus"), nullable=False
    )
    source_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mapped_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[SyncRun] = relationship(
        "SyncRun", back_populates="records", lazy="select"
    )
