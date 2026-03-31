from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MappingTemplate(Base):
    __tablename__ = "mapping_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source_connection_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_connection_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_module: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_object: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_query: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kontracts_endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kontracts_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    fetch_associated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assoc_module: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assoc_object: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assoc_string: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    source_connection: Mapped[Optional[Any]] = relationship(
        "Connection",
        foreign_keys=[source_connection_id],
        back_populates="source_mappings",
        lazy="select",
    )
    target_connection: Mapped[Optional[Any]] = relationship(
        "Connection",
        foreign_keys=[target_connection_id],
        back_populates="target_mappings",
        lazy="select",
    )
    versions: Mapped[list] = relationship(
        "MappingVersion",
        back_populates="template",
        lazy="select",
        uselist=True,
        cascade="all, delete-orphan",
    )
    sync_runs: Mapped[list] = relationship(
        "SyncRun",
        back_populates="mapping_template",
        lazy="select",
    )


class MappingVersion(Base):
    __tablename__ = "mapping_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mapping_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_mappings: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    template: Mapped[MappingTemplate] = relationship(
        "MappingTemplate", back_populates="versions", lazy="select"
    )
