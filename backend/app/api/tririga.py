import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.connection import Connection, ConnectionType
from app.utils.crypto import decrypt_credentials

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    connection_id: Optional[int] = None
    module_name: str
    query_name: str
    filters: Optional[Dict[str, Any]] = None
    max_records: int = 100


class PreviewRequest(BaseModel):
    connection_id: Optional[int] = None
    module_name: str
    query_name: str
    max_records: int = 5


async def _get_tririga_client(
    connection_id: Optional[int], db: AsyncSession
):
    from app.tririga_client.client import TririgaClient

    if settings.demo_mode:
        return TririgaClient(
            base_url=settings.tririga_url,
            username="demo",
            password="demo",
            demo_mode=True,
        )

    if connection_id:
        result = await db.execute(
            select(Connection).where(
                Connection.id == connection_id,
                Connection.connection_type == ConnectionType.tririga,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="TRIRIGA connection not found")
        creds = decrypt_credentials(conn.encrypted_credentials)
        return TririgaClient(
            base_url=conn.base_url or settings.tririga_url,
            username=creds.get("username", ""),
            password=creds.get("password", ""),
            wsdl_path=creds.get("wsdl_path", "/ws/TririgaWS?wsdl"),
        )

    # Fall back to env-based settings
    return TririgaClient(
        base_url=settings.tririga_url,
        username=settings.tririga_username or "",
        password=settings.tririga_password or "",
        wsdl_path=settings.tririga_wsdl_path,
    )


@router.get("/modules")
async def get_modules(
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_tririga_client(connection_id, db)
    try:
        modules = await client.get_modules()
        return {"modules": modules}
    except Exception as e:
        logger.error(f"Failed to get TRIRIGA modules: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")


@router.get("/operations")
async def get_operations(
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_tririga_client(connection_id, db)
    try:
        from app.tririga_client.wsdl_parser import parse_wsdl_operations
        ops = await parse_wsdl_operations(client)
        return {"operations": ops}
    except Exception as e:
        logger.error(f"Failed to get TRIRIGA operations: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")


@router.get("/fields")
async def get_fields(
    module_name: str = Query(...),
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_tririga_client(connection_id, db)
    try:
        fields = await client.get_module_fields(module_name)
        return {"module": module_name, "fields": fields}
    except Exception as e:
        logger.error(f"Failed to get fields for module {module_name}: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")


@router.post("/query")
async def run_query(
    payload: QueryRequest, db: AsyncSession = Depends(get_db)
):
    client = await _get_tririga_client(payload.connection_id, db)
    try:
        records = await client.run_named_query(
            module_name=payload.module_name,
            query_name=payload.query_name,
            filters=payload.filters or {},
            max_records=payload.max_records,
        )
        return {"records": records, "count": len(records)}
    except Exception as e:
        logger.error(f"Failed to run TRIRIGA query: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")


@router.post("/preview")
async def preview_data(
    payload: PreviewRequest, db: AsyncSession = Depends(get_db)
):
    client = await _get_tririga_client(payload.connection_id, db)
    try:
        records = await client.run_named_query(
            module_name=payload.module_name,
            query_name=payload.query_name,
            filters={},
            max_records=payload.max_records,
        )
        fields = await client.get_module_fields(payload.module_name)
        return {
            "records": records,
            "count": len(records),
            "fields": fields,
            "module": payload.module_name,
            "query": payload.query_name,
        }
    except Exception as e:
        logger.error(f"Failed to preview TRIRIGA data: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")


@router.get("/record/{spec_id}/{record_id}")
async def get_record(
    spec_id: int,
    record_id: int,
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_tririga_client(connection_id, db)
    try:
        record = await client.get_record(spec_id=spec_id, record_id=record_id)
        return {"record": record}
    except Exception as e:
        logger.error(f"Failed to get TRIRIGA record {spec_id}/{record_id}: {e}")
        raise HTTPException(status_code=502, detail=f"TRIRIGA error: {str(e)}")
