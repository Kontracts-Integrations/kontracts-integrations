import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update as sql_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.connection import Connection
from app.models.id_mapping import IdMapping
from app.models.lookup_table import LookupTable
from app.models.mapping import MappingTemplate, MappingVersion
from app.schemas.mapping import (
    FieldMapping,
    MappingImportPayload,
    MappingTemplateCreate,
    MappingTemplateResponse,
    MappingTemplateUpdate,
    MappingVersionResponse,
)

EXPORT_FORMAT_VERSION = "1.0"


class MappingPreviewRequest(BaseModel):
    records: List[Dict[str, Any]]
    field_mappings: Optional[List[FieldMapping]] = None


class LookupTableCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class LookupTableResponse(BaseModel):
    name: str
    description: Optional[str] = None
    entry_count: int = 0

logger = logging.getLogger(__name__)
router = APIRouter()


async def _ensure_lookup_table(
    db: AsyncSession, name: Optional[str], description: Optional[str] = None
) -> None:
    """Register a named lookup table (bucket) if it isn't already. Idempotent and
    race-safe (atomic upsert on the unique name)."""
    name = (name or "").strip()
    if not name:
        return
    stmt = (
        pg_insert(LookupTable)
        .values(name=name, description=description)
        .on_conflict_do_nothing(index_elements=["name"])
    )
    await db.execute(stmt)


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
        lookup_table_name=template.lookup_table_name,
        update_existing=template.update_existing,
        lookup_key_fields=template.lookup_key_fields or [],
        source_filters=template.source_filters or [],
        filter_match=template.filter_match or "all",
        fetch_associated=template.fetch_associated,
        assoc_module=template.assoc_module,
        assoc_object=template.assoc_object,
        assoc_string=template.assoc_string,
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


# NOTE: declared before "/{mapping_id}" so the literal path wins over the int param.
@router.get("/lookup-tables", response_model=List[LookupTableResponse])
async def list_lookup_tables(db: AsyncSession = Depends(get_db)):
    """List named lookup tables available for mappings to write to / read from.

    Unions the registry (names declared by mappings) with any bucket names that
    already have entries, so nothing is missed.
    """
    reg_result = await db.execute(select(LookupTable).order_by(LookupTable.name))
    registry = {r.name: r.description for r in reg_result.scalars().all()}

    count_result = await db.execute(
        select(IdMapping.table_name, func.count(IdMapping.id)).group_by(IdMapping.table_name)
    )
    counts: Dict[str, int] = {row[0]: row[1] for row in count_result.fetchall()}

    names = sorted(set(registry) | set(counts))
    return [
        LookupTableResponse(
            name=n, description=registry.get(n), entry_count=counts.get(n, 0)
        )
        for n in names
    ]


@router.post(
    "/lookup-tables", response_model=LookupTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_lookup_table(
    payload: LookupTableCreate, db: AsyncSession = Depends(get_db)
):
    """Register a named lookup table up front, so mappings can select it."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Lookup table name is required")
    await _ensure_lookup_table(db, name, payload.description)
    await db.commit()
    return LookupTableResponse(name=name, description=payload.description, entry_count=0)


# NOTE: declared before "/{mapping_id}" so the literal path wins over the int param.
@router.get("/export-all")
async def export_all_mappings(db: AsyncSession = Depends(get_db)):
    """Export every mapping template (config + current field mappings) as one JSON file."""
    result = await db.execute(
        select(MappingTemplate).order_by(MappingTemplate.name)
    )
    templates = result.scalars().all()

    current_by_template: Dict[int, Any] = {}
    if templates:
        cv_result = await db.execute(
            select(MappingVersion)
            .where(MappingVersion.template_id.in_([t.id for t in templates]))
            .where(MappingVersion.is_current.is_(True))
            .order_by(MappingVersion.id.desc())
        )
        for v in cv_result.scalars().all():
            current_by_template.setdefault(v.template_id, v)

    mappings = []
    for t in templates:
        cv = current_by_template.get(t.id)
        field_mappings = cv.field_mappings.get("mappings", []) if cv else []
        mappings.append(_build_export(t, field_mappings)["template"])

    export = {
        "kontracts_mappings_export": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "mappings": mappings,
    }
    return JSONResponse(
        content=export,
        headers={"Content-Disposition": 'attachment; filename="mapping-templates.json"'},
    )


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
        lookup_table_name=payload.lookup_table_name,
        update_existing=payload.update_existing,
        lookup_key_fields=payload.lookup_key_fields,
        source_filters=[f.model_dump() for f in payload.source_filters],
        filter_match=payload.filter_match,
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
    await _ensure_lookup_table(db, template.lookup_table_name)
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

    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        template.name = payload.name
    if "description" in fields:
        template.description = payload.description
    if "source_connection_id" in fields:
        template.source_connection_id = payload.source_connection_id
    if "target_connection_id" in fields:
        template.target_connection_id = payload.target_connection_id
    if "source_module" in fields:
        template.source_module = payload.source_module
    if "source_object" in fields:
        template.source_object = payload.source_object
    if "source_query" in fields:
        template.source_query = payload.source_query
    if "kontracts_endpoint" in fields:
        template.kontracts_endpoint = payload.kontracts_endpoint
    if "kontracts_method" in fields and payload.kontracts_method is not None:
        template.kontracts_method = payload.kontracts_method
    if "lookup_table_name" in fields:
        template.lookup_table_name = payload.lookup_table_name
        await _ensure_lookup_table(db, payload.lookup_table_name)
    if "update_existing" in fields and payload.update_existing is not None:
        template.update_existing = payload.update_existing
    if "lookup_key_fields" in fields and payload.lookup_key_fields is not None:
        template.lookup_key_fields = payload.lookup_key_fields
    if "source_filters" in fields and payload.source_filters is not None:
        template.source_filters = [f.model_dump() for f in payload.source_filters]
    if "filter_match" in fields and payload.filter_match is not None:
        template.filter_match = payload.filter_match
    if "is_active" in fields and payload.is_active is not None:
        template.is_active = payload.is_active
    if "fetch_associated" in fields and payload.fetch_associated is not None:
        template.fetch_associated = payload.fetch_associated
    if "assoc_module" in fields:
        template.assoc_module = payload.assoc_module
    if "assoc_object" in fields:
        template.assoc_object = payload.assoc_object
    if "assoc_string" in fields:
        template.assoc_string = payload.assoc_string

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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "mapping").strip()).strip("-").lower()
    return slug or "mapping"


def _build_export(template: MappingTemplate, field_mappings: list) -> Dict[str, Any]:
    return {
        "kontracts_mapping_export": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "template": {
            "name": template.name,
            "description": template.description,
            "source_connection_id": template.source_connection_id,
            "target_connection_id": template.target_connection_id,
            "source_module": template.source_module,
            "source_object": template.source_object,
            "source_query": template.source_query,
            "kontracts_endpoint": template.kontracts_endpoint,
            "kontracts_method": template.kontracts_method,
            "lookup_table_name": template.lookup_table_name,
            "update_existing": template.update_existing,
            "lookup_key_fields": template.lookup_key_fields or [],
            "source_filters": template.source_filters or [],
            "filter_match": template.filter_match or "all",
            "fetch_associated": template.fetch_associated,
            "assoc_module": template.assoc_module,
            "assoc_object": template.assoc_object,
            "assoc_string": template.assoc_string,
            "field_mappings": field_mappings,
        },
    }


@router.get("/{mapping_id}/export")
async def export_mapping(mapping_id: int, db: AsyncSession = Depends(get_db)):
    """Export a mapping template (config + current field mappings) as a portable JSON file."""
    result = await db.execute(
        select(MappingTemplate).where(MappingTemplate.id == mapping_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mapping template not found")

    current = await _get_current_version(db, mapping_id)
    field_mappings = current.field_mappings.get("mappings", []) if current else []

    export = _build_export(template, field_mappings)
    filename = f"mapping-{_slugify(template.name)}.json"
    return JSONResponse(
        content=export,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/import", response_model=MappingTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def import_mapping(
    payload: MappingImportPayload,
    name_override: Optional[str] = Query(
        default=None, description="Override the imported template's name"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Create a new mapping template from a previously exported JSON file.

    Connection references that no longer exist on this system are dropped so the
    import always succeeds; re-point them afterwards in the mapping editor.
    """
    tpl = payload.template

    name = (name_override or tpl.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Imported template is missing a name")

    async def _valid_conn(conn_id: Optional[int]) -> Optional[int]:
        if conn_id is None:
            return None
        exists = await db.execute(select(Connection.id).where(Connection.id == conn_id))
        return conn_id if exists.scalar_one_or_none() is not None else None

    source_connection_id = await _valid_conn(tpl.source_connection_id)
    target_connection_id = await _valid_conn(tpl.target_connection_id)

    template = MappingTemplate(
        name=name,
        description=tpl.description,
        source_connection_id=source_connection_id,
        target_connection_id=target_connection_id,
        source_module=tpl.source_module,
        source_object=tpl.source_object,
        source_query=tpl.source_query,
        kontracts_endpoint=tpl.kontracts_endpoint,
        kontracts_method=tpl.kontracts_method or "POST",
        lookup_table_name=tpl.lookup_table_name,
        update_existing=tpl.update_existing,
        lookup_key_fields=tpl.lookup_key_fields,
        source_filters=[f.model_dump() for f in tpl.source_filters],
        filter_match=tpl.filter_match,
        fetch_associated=tpl.fetch_associated,
        assoc_module=tpl.assoc_module,
        assoc_object=tpl.assoc_object,
        assoc_string=tpl.assoc_string,
    )
    db.add(template)
    await db.flush()

    field_mappings_data = [fm.model_dump() for fm in tpl.field_mappings]
    version = MappingVersion(
        template_id=template.id,
        version_number=1,
        field_mappings={"mappings": field_mappings_data},
        is_current=True,
    )
    db.add(version)
    await db.flush()
    await _ensure_lookup_table(db, template.lookup_table_name)
    await db.refresh(template)
    await db.refresh(version)
    return _build_response_with_version(template, version)


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
