from datetime import datetime
from typing import Any, Dict, List, Optional

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

    # Named lookup table this mapping writes its produced (source_id -> kontracts_id)
    # pairs into on success, so subsequent mappings can look those IDs up.
    lookup_table_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Source field names whose values are also indexed as lookup keys (pointing to
    # the produced kontracts_id) when this mapping writes to its lookup table, so
    # subsequent mappings can resolve the target id by these business keys.
    lookup_key_fields: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True, default=list
    )

    # When True, subsequent runs update already-synced records whose mapped payload
    # changed (PUT to {endpoint}/{kontracts_id}) instead of skipping them.
    update_existing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Source-record filters: list of {field, operator, value}. Only records that
    # match are mapped/pushed. filter_match is "all" (AND) or "any" (OR).
    source_filters: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    filter_match: Mapped[str] = mapped_column(String(10), default="all", nullable=False)

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
    versions: Mapped[List["MappingVersion"]] = relationship(
        "MappingVersion",
        back_populates="template",
        lazy="select",
        uselist=True,
        cascade="all, delete-orphan",
    )
    sync_runs: Mapped[List["SyncRun"]] = relationship(
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
