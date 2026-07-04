from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Default named lookup table. Existing (pre-naming) rows and lease syncs
# that don't declare a table name live under this name.
DEFAULT_LOOKUP_TABLE = "lease_mappings"


class LeaseMapping(Base):
    __tablename__ = "lease_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Named lookup table this ID mapping belongs to. Lets a mapping write its
    # produced IDs into a named bucket that subsequent mappings can look up.
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=DEFAULT_LOOKUP_TABLE,
        server_default=DEFAULT_LOOKUP_TABLE,
        index=True,
    )
    tririga_lease_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tririga_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kontracts_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
