import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.connection import Connection, ConnectionType
from app.utils.crypto import decrypt_credentials

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_kontracts_client(
    connection_id: Optional[int], db: AsyncSession
):
    from app.kontracts_client.client import KontractsClient

    if settings.demo_mode:
        return KontractsClient(
            base_url=settings.kontracts_base_url,
            auth0_domain="demo.auth0.com",
            client_id="demo",
            client_secret="demo",
            audience="demo",
            demo_mode=True,
        )

    if connection_id:
        result = await db.execute(
            select(Connection).where(
                Connection.id == connection_id,
                Connection.connection_type == ConnectionType.kontracts,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(
                status_code=404, detail="Kontracts connection not found"
            )
        creds = decrypt_credentials(conn.encrypted_credentials)
        return KontractsClient(
            base_url=conn.base_url or settings.kontracts_base_url,
            auth0_domain=creds.get("auth0_domain", ""),
            client_id=creds.get("client_id", ""),
            client_secret=creds.get("client_secret", ""),
            audience=creds.get("audience", ""),
        )

    return KontractsClient(
        base_url=settings.kontracts_base_url,
        auth0_domain=settings.kontracts_auth0_domain or "",
        client_id=settings.kontracts_client_id or "",
        client_secret=settings.kontracts_client_secret or "",
        audience=settings.kontracts_audience or "",
    )


@router.get("/endpoints")
async def list_endpoints(
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_kontracts_client(connection_id, db)
    try:
        from app.kontracts_client.schema_parser import parse_openapi_endpoints
        schema = await client.get_openapi_schema()
        endpoints = parse_openapi_endpoints(schema)
        return {"endpoints": endpoints}
    except Exception as e:
        logger.error(f"Failed to list Kontracts endpoints: {e}")
        raise HTTPException(status_code=502, detail=f"Kontracts error: {str(e)}")


@router.get("/schema")
async def get_endpoint_schema(
    endpoint: str = Query(..., description="Endpoint path e.g. /api/v1/leases/"),
    method: str = Query(default="post"),
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_kontracts_client(connection_id, db)
    try:
        from app.kontracts_client.schema_parser import parse_endpoint_schema
        schema = await client.get_openapi_schema()
        fields = parse_endpoint_schema(schema, endpoint, method.lower())
        return {"endpoint": endpoint, "method": method, "fields": fields}
    except Exception as e:
        logger.error(f"Failed to get schema for {endpoint}: {e}")
        raise HTTPException(status_code=502, detail=f"Kontracts error: {str(e)}")


@router.get("/leases")
async def list_leases(
    connection_id: Optional[int] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_kontracts_client(connection_id, db)
    try:
        result = await client.list_leases(page=page, page_size=page_size)
        return result
    except Exception as e:
        logger.error(f"Failed to list Kontracts leases: {e}")
        raise HTTPException(status_code=502, detail=f"Kontracts error: {str(e)}")


@router.get("/health")
async def kontracts_health(
    connection_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_kontracts_client(connection_id, db)
    try:
        health = await client.health_check()
        return health
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Kontracts error: {str(e)}")
