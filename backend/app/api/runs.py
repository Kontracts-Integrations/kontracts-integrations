import logging
from datetime import datetime, timezone
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
            selectinload(SyncRun.log_entries),
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    from app.models.sync_run import SyncRecord
    from sqlalchemy import func, desc, cast, String
    from app.schemas.sync_run import LogEntryResponse, GroupedRecordResponse

    # Deduplicate by tririga_record_id first using DISTINCT ON (keeps latest entry via id DESC)
    # If tririga_record_id is null, fall back to record id to prevent grouping nulls together
    distinct_expr = func.coalesce(SyncRecord.tririga_record_id, cast(SyncRecord.id, String))
    subquery = (
        select(
            SyncRecord.status,
            SyncRecord.error_message,
            SyncRecord.tririga_record_id
        )
        .distinct(distinct_expr)
        .where(SyncRecord.run_id == run_id)
        .order_by(distinct_expr, desc(SyncRecord.id))
        .subquery()
    )

    # Query grouped sync records from deduplicated subquery
    records_query = (
        select(
            subquery.c.status,
            subquery.c.error_message,
            func.count(subquery.c.tririga_record_id).label("count"),
            func.array_agg(subquery.c.tririga_record_id).label("examples")
        )
        .group_by(subquery.c.status, subquery.c.error_message)
    )
    records_result = await db.execute(records_query)

    grouped_records = []
    for row in records_result:
        # Deduplicate and limit example tririga record IDs
        seen_examples = set()
        examples = []
        if row.examples:
            for ex in row.examples:
                if ex and ex not in seen_examples:
                    seen_examples.add(ex)
                    examples.append(ex)
                    if len(examples) >= 10:
                        break
        grouped_records.append(
            GroupedRecordResponse(
                status=row.status.value,
                error_message=row.error_message,
                count=row.count,
                examples=examples
            )
        )

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
        grouped_records=grouped_records,
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


@router.post("/{run_id}/cancel", response_model=SyncRunResponse)
async def cancel_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SyncRun).where(SyncRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in (RunStatus.pending, RunStatus.running):
        raise HTTPException(status_code=400, detail="Only pending or running runs can be cancelled")

    run.status = RunStatus.stopped
    run.error_message = "Manually stopped by user"
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{run_id}/export")
async def export_run_records(
    run_id: int,
    status: Optional[str] = None,
    error_message: Optional[List[str]] = Query(None),
    category: Optional[str] = Query(None)
):
    from fastapi.responses import StreamingResponse
    import io
    import csv
    from app.database import AsyncSessionLocal

    async def csv_generator():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Mapping Template", "TRIRIGA Record ID", "Status", "Error / Reason", "Created At"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Open its own separate database session to prevent FastAPI from cleaning it up prematurely
        async with AsyncSessionLocal() as local_db:
            from sqlalchemy.orm import selectinload
            run_result = await local_db.execute(
                select(SyncRun)
                .options(selectinload(SyncRun.mapping_template))
                .where(SyncRun.id == run_id)
            )
            run = run_result.scalar_one_or_none()
            if not run:
                return

            mapping_template_name = run.mapping_template.name if run.mapping_template else "Unknown"

            from app.models.sync_run import SyncRecord
            from sqlalchemy import func, desc, cast, String

            # Deduplicate by tririga_record_id first using DISTINCT ON (keeps latest entry via id DESC)
            distinct_expr = func.coalesce(SyncRecord.tririga_record_id, cast(SyncRecord.id, String))
            subquery = (
                select(
                    SyncRecord.tririga_record_id,
                    SyncRecord.status,
                    SyncRecord.error_message,
                    SyncRecord.created_at,
                    SyncRecord.id
                )
                .distinct(distinct_expr)
                .where(SyncRecord.run_id == run_id)
                .order_by(distinct_expr, desc(SyncRecord.id))
                .subquery()
            )

            query = select(
                subquery.c.tririga_record_id,
                subquery.c.status,
                subquery.c.error_message,
                subquery.c.created_at
            )

            if status:
                query = query.where(subquery.c.status == status)
            if error_message:
                query = query.where(subquery.c.error_message.in_(error_message))

            query = query.order_by(subquery.c.id.asc())

            result = await local_db.stream(query)
            async for row in result:
                writer.writerow([
                    mapping_template_name,
                    row.tririga_record_id or "",
                    row.status.value,
                    row.error_message or "",
                    row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else ""
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    filename = f"run {run_id} - export.csv"
    if category:
        filename = f"run {run_id} - {category}.csv"

    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _execute_sync_run(run_id: int) -> None:
    from app.sync_service.service import SyncService

    async with AsyncSessionLocal() as db:
        try:
            service = SyncService(db)
            await service.execute_run(run_id)
        except Exception as e:
            logger.error(f"Background sync run {run_id} failed: {e}", exc_info=True)
        finally:
            await db.commit()
