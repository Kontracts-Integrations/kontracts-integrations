import enum
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LogLevel(str, enum.Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        Index("ix_log_entries_created_at", "created_at"),
        Index("ix_log_entries_level", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sync_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="loglevel"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    component: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[Optional[Any]] = relationship(
        "SyncRun", back_populates="log_entries", lazy="select"
    )
