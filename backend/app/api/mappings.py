import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.mapping import MappingTemplate, MappingVersion
from app.schemas.mapping import (
    FieldMapping,
    MappingTemplateCreate,
    MappingTemplateResponse,
    MappingTemplateUpdate,
    MappingVersionResponse,
)


class MappingPreviewRequest(BaseModel):
    records: List[Dict[str, Any]]
    field_mappings: Optional[List[FieldMapping]] = None

logger = logging.getLogger(__name__)
router = APIRouter()


def _versions_list(template: MappingTemplate) -> list:
    """Safely coerce template.versions to a plain list regardless of SA collection state."""
    raw = template.versions
    return raw if isinstance(raw, list) else ([raw] if raw is not None else [])


def _build_response(template: MappingTemplate) -> MappingTemplateResponse:
    current_version = None
    versions_sorted = sorted(
        _versions_list(template), key=lambda v: (v.version_number, v.id), reverse=True
    )
    if versions_sorted:
        for v in versions_sorted:
            if v.is_current:
                current_version = MappingVersionResponse.model_validate(v)
                break
        if not current_version:
            current_version = MappingVersionResponse.model_validate(versions_sorted[0])

    return _build_response_with_version(template, current_version)


def _build_response_with_version(
    template: MappingTemplate,
    version: Optional[MappingVersion],
) -> MappingTemplateResponse:
    """Build a response from in-memory objects — no re-query needed."""
    cv = MappingVersionResponse.model_validate(version) if version else None
    return MappingTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        source_connection_id=template.source_connection_id,
        target_connection_id=template.target_connection_id,
        source_module=template.source_module,
        source_object=template.source_object,
        source_query=template.source_query,
        kontracts_endpoint=template.kontracts_endpoint,
        kontracts_method=template.kontracts_method,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        current_version=cv,
    )


async def _get_current_version(db: AsyncSession, template_id: int) -> Optional[MappingVersion]:
    """Query the current version for a template directly from DB."""
    result = await db.execute(
        select(MappingVersion)
        .where(MappingVersion.template_id == template_id)
        .where(MappingVersion.is_current.is_(True))
        .order_by(MappingVersion.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=List[MappingTemplateResponse])
async def list_mappings(
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    q = select(MappingTemplate).order_by(MappingTemplate.created_at.desc())
    if active_only:
        q = q.where(MappingTemplate.is_active.is_(True))
    result = await db.execute(q)
    templates = result.scalars().all()

    # Load current versions for all templates in one query
    if templates:
        template_ids = [t.id for t in templates]
        cv_result = await db.execute(
            select(MappingVersion)
            .where(MappingVersion.template_id.in_(template_ids))
            .where(MappingVersion.is_current.is_(True))
            .order_by(MappingVersion.id.desc())
        )
        current_versions: dict = {}
        for v in cv_result.scalars().all():
            if v.template_id not in current_versions:
                current_versions[v.template_id] = v
    else:
        current_versions = {}

    return [_build_response_with_version(t, current_versions.get(t.id)) for t in templates]


@router.get("/{mapping_id}", response_model=MappingTemplateResponse)
async def get_mapping(mapping_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MappingTemplate).where(MappingTemplate.id == mapping_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mapping template not found")
    current_version = await _get_current_version(db, mapping_id)
    return _build_response_with_version(template, current_version)


@router.post(
    "/", response_model=MappingTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_mapping(
    payload: MappingTemplateCreate, db: AsyncSession = Depends(get_db)
):
    template = MappingTemplate(
        name=payload.name,
        description=payload.description,
        source_connection_id=payload.source_connection_id,
        target_connection_id=payload.target_connection_id,
        source_module=payload.source_module,
        source_object=payload.source_object,
        source_query=payload.source_query,
        kontracts_endpoint=payload.kontracts_endpoint,
        kontracts_method=payload.kontracts_method or "POST",
    )
    db.add(template)
    await db.flush()

    field_mappings_data = [fm.model_dump() for fm in payload.field_mappings]
    version = MappingVersion(
        template_id=template.id,
        version_number=1,
        field_mappings={"mappings": field_mappings_data},
        is_current=True,
    )
    db.add(version)
    await db.flush()
    await db.refresh(template)  # populate server-generated timestamps
    await db.refresh(version)   # populate server-generated id / created_at
    return _build_response_with_version(template, version)


@router.put("/{mapping_id}", response_model=MappingTemplateResponse)
async def update_mapping(
    mapping_id: int,
    payload: MappingTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MappingTemplate)
        .where(MappingTemplate.id == mapping_id)
        .options(selectinload(MappingTemplate.versions))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mapping template not found")

    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    if payload.source_connection_id is not None:
        template.source_connection_id = payload.source_connection_id
    if payload.target_connection_id is not None:
        template.target_connection_id = payload.target_connection_id
    if payload.source_module is not None:
        template.source_module = payload.source_module
    if payload.source_object is not None:
        template.source_object = payload.source_object
    if payload.source_query is not None:
        template.source_query = payload.source_query
    if payload.kontracts_endpoint is not None:
        template.kontracts_endpoint = payload.kontracts_endpoint
    if payload.kontracts_method is not None:
        template.kontracts_method = payload.kontracts_method
    if payload.is_active is not None:
        template.is_active = payload.is_active

    if payload.field_mappings is not None:
        await db.execute(
            sql_update(MappingVersion)
            .where(MappingVersion.template_id == mapping_id)
            .values(is_current=False)
        )
        max_result = await db.execute(
            select(func.max(MappingVersion.version_number)).where(
                MappingVersion.template_id == mapping_id
            )
        )
        max_version = max_result.scalar() or 0
        field_mappings_data = [fm.model_dump() for fm in payload.field_mappings]
        new_version = MappingVersion(
            template_id=template.id,
            version_number=max_version + 1,
            field_mappings={"mappings": field_mappings_data},
            is_current=True,
        )
        db.add(new_version)

    await db.flush()
    await db.refresh(template)  # populate updated_at
    if payload.field_mappings is not None:
        await db.refresh(new_version)  # populate id / created_at
        return _build_response_with_version(template, new_version)
    current_version = await _get_current_version(db, mapping_id)
    return _build_response_with_version(template, current_version)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MappingTemplate).where(MappingTemplate.id == mapping_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mapping template not found")
    await db.delete(template)
    await db.commit()


@router.get("/{mapping_id}/versions", response_model=List[MappingVersionResponse])
async def get_mapping_versions(
    mapping_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MappingVersion)
        .where(MappingVersion.template_id == mapping_id)
        .order_by(MappingVersion.version_number.desc())
    )
    versions = result.scalars().all()
    return versions


@router.post("/{mapping_id}/preview")
async def preview_mapping(
    mapping_id: int,
    payload: MappingPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Apply the current (or provided) field mappings to sample records and return the results."""
    result = await db.execute(
        select(MappingTemplate)
        .where(MappingTemplate.id == mapping_id)
        .options(selectinload(MappingTemplate.versions))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mapping template not found")

    if payload.field_mappings is not None:
        field_mappings_list = [fm.model_dump() for fm in payload.field_mappings]
    else:
        raw = template.versions
        versions: list = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
        current = next((v for v in versions if v.is_current), versions[0] if versions else None)
        if not current:
            return {"records": [], "count": 0}
        field_mappings_list = current.field_mappings.get("mappings", [])

    from app.mapping_engine.engine import MappingEngine

    engine = MappingEngine(field_mappings_list)
    records = payload.records[:10]  # Cap preview at 10 records
    results = []
    for record in records:
        try:
            mapped, warnings = engine.apply(record)
            results.append({"mapped": mapped, "warnings": warnings, "error": None})
        except Exception as e:
            results.append({"mapped": {}, "warnings": [], "error": str(e)})

    return {"records": results, "count": len(results)}
