import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.connection import Connection, ConnectionType
from app.source_connectors.factory import build_source_connector
from app.utils.crypto import decrypt_credentials

logger = logging.getLogger(__name__)
router = APIRouter()

SOURCE_TYPES = {
    ConnectionType.tririga,
    ConnectionType.sap_re,
    ConnectionType.planon,
    ConnectionType.costar,
    ConnectionType.servicenow_wsd,
}


async def _get_connector(connection_id: Optional[int], db: AsyncSession):
    """Resolve the source connector from a connection_id (or fall back to env TRIRIGA)."""
    if connection_id:
        result = await db.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="Source connection not found")
        if conn.connection_type not in SOURCE_TYPES:
            raise HTTPException(status_code=400, detail=f"Connection {conn.id} is not a source system connection")
        creds = decrypt_credentials(conn.encrypted_credentials)
        return build_source_connector(
            connection_type=conn.connection_type,
            base_url=conn.base_url or "",
            credentials=creds,
            demo_mode=settings.demo_mode,
        )

    # No connection_id — fall back to env-based TRIRIGA
    from app.tririga_client.client import TririgaClient
    from app.source_connectors.tririga import TririgaSourceConnector
    client = TririgaClient(
        base_url=settings.tririga_url,
        username=settings.tririga_username or "",
        password=settings.tririga_password or "",
        wsdl_path=settings.tririga_wsdl_path,
        demo_mode=settings.demo_mode,
    )
    return TririgaSourceConnector(client)


@router.get("/objects")
async def get_objects(
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    connector = await _get_connector(connection_id, db)
    try:
        objects = await connector.get_objects()
        return {"objects": objects}
    except Exception as e:
        logger.error(f"get_objects failed: {e}")
        raise HTTPException(status_code=502, detail=f"Source system error: {str(e)}")


@router.get("/business-objects")
async def get_business_objects(
    module_name: str = Query(...),
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    connector = await _get_connector(connection_id, db)
    try:
        if hasattr(connector, "get_business_objects"):
            bos = await connector.get_business_objects(module_name)
        else:
            # Non-TRIRIGA connectors: fall back to objects list filtered by module
            bos = await connector.get_objects()
        return {"module": module_name, "business_objects": bos}
    except Exception as e:
        logger.error(f"get_business_objects failed for {module_name}: {e}")
        raise HTTPException(status_code=502, detail=f"Source system error: {str(e)}")


@router.get("/fields")
async def get_fields(
    object_name: str = Query(...),
    module_name: Optional[str] = Query(None),
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    connector = await _get_connector(connection_id, db)
    try:
        try:
            fields = await connector.get_object_fields(
                object_name, **({"module_name": module_name} if module_name else {})
            )
        except TypeError:
            fields = await connector.get_object_fields(object_name)
        return {"object": object_name, "fields": fields}
    except Exception as e:
        logger.error(f"get_fields failed for {object_name}: {e}")
        raise HTTPException(status_code=502, detail=f"Source system error: {str(e)}")


@router.get("/associated-objects")
async def get_associated_objects(
    object_type_id: int = Query(...),
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    connector = await _get_connector(connection_id, db)
    try:
        if hasattr(connector, "get_associated_objects"):
            associations = await connector.get_associated_objects(object_type_id)
        else:
            associations = []
        return {"object_type_id": object_type_id, "associations": associations}
    except Exception as e:
        logger.error(f"get_associated_objects failed for objectTypeId={object_type_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Source system error: {str(e)}")


class PreviewRequest(BaseModel):
    connection_id: Optional[int] = None
    object_name: str
    module_name: Optional[str] = None
    field_names: Optional[List[str]] = None
    query_name: str = ""
    max_records: int = 5
    source_filters: Optional[List[Dict[str, Any]]] = None
    filter_match: str = "all"


@router.post("/preview")
async def preview_data(
    payload: PreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    connector = await _get_connector(payload.connection_id, db)
    try:
        # Associated-BO filters can't be evaluated in preview (association data
        # isn't fetched here), so they're ignored for the sample.
        preview_filters = [f for f in (payload.source_filters or []) if not f.get("use_associated")]

        # Fields referenced only by filters must also be fetched, else the filter
        # has no value to compare against and drops every record.
        field_names = list(payload.field_names or [])
        for flt in preview_filters:
            fld = flt.get("field")
            if fld and fld not in field_names:
                field_names.append(fld)

        # When filters are active, fetch a larger sample so matching records
        # aren't missed, then filter and cap to the requested preview size.
        fetch_count = 200 if preview_filters else payload.max_records
        records = await connector.preview_records(
            object_name=payload.object_name,
            module_name=payload.module_name,
            field_names=field_names or None,
            query_name=payload.query_name,
            max_records=fetch_count,
        )
        if preview_filters:
            from app.mapping_engine.filters import filter_records
            records = filter_records(
                records, preview_filters, payload.filter_match
            )[: payload.max_records]
        try:
            fields = await connector.get_object_fields(
                payload.object_name,
                **({"module_name": payload.module_name} if payload.module_name else {}),
            )
        except TypeError:
            fields = await connector.get_object_fields(payload.object_name)
        return {
            "records": records,
            "count": len(records),
            "fields": fields,
            "object": payload.object_name,
            "query": payload.query_name,
        }
    except Exception as e:
        logger.error(f"preview_data failed: {e}")
        raise HTTPException(status_code=502, detail=f"Source system error: {str(e)}")
