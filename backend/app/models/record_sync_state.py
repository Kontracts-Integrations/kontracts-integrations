from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecordSyncState(Base):
    """Persistent per-record sync state, used to upsert on subsequent runs.

    Tracks, for each (mapping template, source record), the Kontracts ID that was
    created and a hash of the last mapped payload that was pushed. On a re-run the
    sync compares the freshly mapped payload's hash against payload_hash to decide
    whether to skip (unchanged), update via PUT (changed), or create (new).
    """

    __tablename__ = "record_sync_state"
    __table_args__ = (
        UniqueConstraint(
            "mapping_template_id", "source_record_id", name="uq_record_sync_template_record"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mapping_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mapping_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kontracts_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
