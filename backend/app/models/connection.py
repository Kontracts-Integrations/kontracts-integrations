import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConnectionType(str, enum.Enum):
    # Source systems (IWMS)
    tririga = "tririga"
    sap_re = "sap_re"
    planon = "planon"
    costar = "costar"
    servicenow_wsd = "servicenow_wsd"
    # Target system
    kontracts = "kontracts"


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_type: Mapped[ConnectionType] = mapped_column(
        Enum(ConnectionType, name="connectiontype"), nullable=False
    )
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_test_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_test_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    source_mappings: Mapped[list] = relationship(
        "MappingTemplate",
        foreign_keys="MappingTemplate.source_connection_id",
        back_populates="source_connection",
        lazy="select",
    )
    target_mappings: Mapped[list] = relationship(
        "MappingTemplate",
        foreign_keys="MappingTemplate.target_connection_id",
        back_populates="target_connection",
        lazy="select",
    )
