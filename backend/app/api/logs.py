import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.log_entry import LogEntry, LogLevel
from app.schemas.sync_run import LogEntryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[LogEntryResponse])
async def list_logs(
    run_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(LogEntry)
        .order_by(LogEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if run_id is not None:
        q = q.where(LogEntry.run_id == run_id)

    if level:
        try:
            q = q.where(LogEntry.level == LogLevel(level))
        except ValueError:
            pass

    if component:
        q = q.where(LogEntry.component == component)

    if search:
        q = q.where(LogEntry.message.ilike(f"%{search}%"))

    result = await db.execute(q)
    entries = result.scalars().all()
    return entries


@router.get("/stats")
async def log_stats(
    run_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    q = select(LogEntry.level, func.count(LogEntry.id).label("count")).group_by(
        LogEntry.level
    )
    if run_id is not None:
        q = q.where(LogEntry.run_id == run_id)

    result = await db.execute(q)
    rows = result.all()

    stats = {level.value: 0 for level in LogLevel}
    for row in rows:
        stats[row.level.value] = row.count

    return {"stats": stats}
