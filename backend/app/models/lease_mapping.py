from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeaseMapping(Base):
    __tablename__ = "lease_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tririga_lease_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tririga_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kontracts_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
