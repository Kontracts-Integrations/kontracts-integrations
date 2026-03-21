import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, get_db
from app.models.mapping import MappingTemplate
from app.models.sync_run import RunStatus, SyncRun
from app.schemas.sync_run import SyncRunCreate, SyncRunDetailResponse, SyncRunResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[SyncRunResponse])
async def list_runs(
    mapping_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(SyncRun).order_by(SyncRun.created_at.desc()).limit(limit).offset(offset)
    if mapping_id:
        q = q.where(SyncRun.mapping_template_id == mapping_id)
    if status_filter:
        try:
            q = q.where(SyncRun.status == RunStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status_filter}")
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{run_id}", response_model=SyncRunDetailResponse)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SyncRun)
        .where(SyncRun.id == run_id)
        .options(
            selectinload(SyncRun.records),
            selectinload(SyncRun.log_entries),
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    from app.schemas.sync_run import LogEntryResponse, SyncRecordResponse

    return SyncRunDetailResponse(
        id=run.id,
        mapping_template_id=run.mapping_template_id,
        status=run.status,
        triggered_by=run.triggered_by,
        total_records=run.total_records,
        success_count=run.success_count,
        failed_count=run.failed_count,
        skipped_count=run.skipped_count,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        records=[SyncRecordResponse.model_validate(r) for r in run.records],
        logs=[LogEntryResponse.model_validate(l) for l in run.log_entries],
    )


@router.post("/", response_model=SyncRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_run(
    payload: SyncRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Verify mapping exists
    result = await db.execute(
        select(MappingTemplate).where(
            MappingTemplate.id == payload.mapping_template_id,
            MappingTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Active mapping template not found",
        )

    run = SyncRun(
        mapping_template_id=payload.mapping_template_id,
        status=RunStatus.pending,
        triggered_by=payload.triggered_by,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    run_id = run.id
    background_tasks.add_task(_execute_sync_run, run_id)

    return run


@router.post("/{run_id}/retry", response_model=SyncRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_run(
    run_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SyncRun).where(SyncRun.id == run_id))
    original_run = result.scalar_one_or_none()
    if not original_run:
        raise HTTPException(status_code=404, detail="Run not found")

    if original_run.status not in (RunStatus.failed, RunStatus.completed):
        raise HTTPException(
            status_code=400,
            detail="Can only retry failed or completed runs",
        )

    new_run = SyncRun(
        mapping_template_id=original_run.mapping_template_id,
        status=RunStatus.pending,
        triggered_by=f"retry_of_{run_id}",
    )
    db.add(new_run)
    await db.flush()
    await db.refresh(new_run)

    new_run_id = new_run.id
    background_tasks.add_task(_execute_sync_run, new_run_id)

    return new_run


async def _execute_sync_run(run_id: int) -> None:
    from app.sync_service.service import SyncService

    async with AsyncSessionLocal() as db:
        try:
            service = SyncService(db)
            await service.execute_run(run_id)
            await db.commit()
        except Exception as e:
            logger.error(f"Background sync run {run_id} failed: {e}", exc_info=True)
            await db.rollback()
