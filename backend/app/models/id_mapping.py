from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Default named lookup bucket. Existing (pre-naming) rows and syncs that don't
# declare a lookup table name live under this name. Kept for backward
# compatibility with previously written entries and transform configs.
DEFAULT_LOOKUP_TABLE = "default"


class IdMapping(Base):
    """A single source-record -> Kontracts-ID entry, tagged with the named lookup
    table (bucket) it belongs to.

    This is a generic ID store — it is not tied to any particular mapping or
    object type. A mapping writes the IDs it produces here so that subsequent
    mappings can resolve the Kontracts ID from a source key.
    """

    __tablename__ = "id_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Named lookup table (bucket) this ID mapping belongs to. Lets a mapping write
    # its produced IDs into a named bucket that subsequent mappings can look up.
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=DEFAULT_LOOKUP_TABLE,
        server_default=DEFAULT_LOOKUP_TABLE,
        index=True,
    )
    # Primary business key of the produced record (e.g. a lease/contract id).
    source_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kontracts_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Additional business-key values (from the writing mapping's configured
    # lookup_key_fields) that also resolve to this kontracts_id, so subsequent
    # mappings can look the ID up by those source field values, not just the
    # record/primary key. Stored as a JSON list of strings.
    lookup_keys: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
