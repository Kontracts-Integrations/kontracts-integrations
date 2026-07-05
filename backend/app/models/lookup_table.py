from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LookupTable(Base):
    """Registry of named lookup tables (buckets).

    A named lookup table is registered as soon as a mapping declares it, so it is
    discoverable by other mappings before any run has populated it. The actual
    (source_key -> kontracts_id) entries live in ``id_mappings`` tagged with this
    name via ``id_mappings.table_name``.
    """

    __tablename__ = "lookup_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
