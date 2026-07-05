import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.connection import Connection, ConnectionType
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResult,
    ConnectionUpdate,
)
from app.utils.crypto import decrypt_credentials, encrypt_credentials

logger = logging.getLogger(__name__)
router = APIRouter()

EXPORT_FORMAT_VERSION = "1.0"

# Credential keys treated as secrets and stripped from any export. Matching is
# case-insensitive and substring-based so variants (e.g. "client_secret",
# "api_key", "auth_token") are all caught.
_SECRET_KEY_PATTERNS = ("password", "secret", "token", "api_key", "apikey", "private_key", "passphrase")


def _redact_credentials(creds: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Split credentials into the non-secret fields to export and the names of
    the secret fields that were stripped."""
    kept: Dict[str, Any] = {}
    redacted: List[str] = []
    for key, value in (creds or {}).items():
        low = key.lower()
        if any(p in low for p in _SECRET_KEY_PATTERNS):
            redacted.append(key)
        else:
            kept[key] = value
    return kept, redacted


@router.get("/", response_model=List[ConnectionResponse])
async def list_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connection).order_by(Connection.created_at.desc()))
    connections = result.scalars().all()
    return connections


# NOTE: declared before "/{connection_id}" so the literal path wins over the int param.
@router.get("/export")
async def export_connections(db: AsyncSession = Depends(get_db)):
    """Export all connections as a portable JSON file, WITHOUT any secret
    credentials (passwords, client secrets, tokens are stripped)."""
    result = await db.execute(select(Connection).order_by(Connection.name))
    connections = result.scalars().all()

    items = []
    for conn in connections:
        creds: Dict[str, Any] = {}
        try:
            creds = decrypt_credentials(conn.encrypted_credentials) if conn.encrypted_credentials else {}
        except Exception:
            creds = {}
        kept, redacted = _redact_credentials(creds)
        items.append({
            "name": conn.name,
            "connection_type": conn.connection_type.value,
            "base_url": conn.base_url,
            "is_active": conn.is_active,
            "credentials": kept,
            "redacted_credentials": redacted,
        })

    export = {
        "kontracts_connections_export": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "note": "Secrets (passwords/client secrets/tokens) are intentionally omitted; re-enter them on import.",
        "connections": items,
    }
    return JSONResponse(
        content=export,
        headers={"Content-Disposition": 'attachment; filename="connections.json"'},
    )


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Connection).where(Connection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
        )
    return conn


@router.post("/", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    payload: ConnectionCreate, db: AsyncSession = Depends(get_db)
):
    encrypted = encrypt_credentials(payload.credentials)
    conn = Connection(
        name=payload.name,
        connection_type=payload.connection_type,
        base_url=payload.base_url,
        encrypted_credentials=encrypted,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return conn


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int,
    payload: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connection).where(Connection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    if payload.name is not None:
        conn.name = payload.name
    if payload.base_url is not None:
        conn.base_url = payload.base_url
    if payload.is_active is not None:
        conn.is_active = payload.is_active
    if payload.credentials is not None:
        existing_creds = {}
        if conn.encrypted_credentials:
            try:
                existing_creds = decrypt_credentials(conn.encrypted_credentials)
            except Exception:
                pass
        merged = {**existing_creds, **payload.credentials}
        conn.encrypted_credentials = encrypt_credentials(merged)
    conn.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(conn)
    return conn


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Connection).where(Connection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.flush()


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Connection).where(Connection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        credentials = decrypt_credentials(conn.encrypted_credentials)
        test_result = await _test_connection_by_type(conn, credentials)
    except Exception as e:
        test_result = ConnectionTestResult(success=False, message=str(e))

    conn.last_tested_at = datetime.now(timezone.utc)
    conn.last_test_success = test_result.success
    conn.last_test_error = None if test_result.success else test_result.message
    await db.flush()

    return test_result


async def _test_connection_by_type(
    conn: Connection, credentials: dict
) -> ConnectionTestResult:
    if conn.connection_type == ConnectionType.tririga:
        from app.tririga_client.client import TririgaClient

        client = TririgaClient(
            base_url=conn.base_url or "",
            username=credentials.get("username", ""),
            password=credentials.get("password", ""),
            wsdl_path=credentials.get("wsdl_path", "/ws/TririgaWS?wsdl"),
        )
        ok, msg, details = await client.test_connection()
        return ConnectionTestResult(success=ok, message=msg, details=details)

    elif conn.connection_type == ConnectionType.kontracts:
        from app.kontracts_client.client import KontractsClient

        client = KontractsClient(
            base_url=conn.base_url or "",
            auth0_domain=credentials.get("auth0_domain", ""),
            client_id=credentials.get("client_id", ""),
            client_secret=credentials.get("client_secret", ""),
            audience=credentials.get("audience", ""),
        )
        ok, msg, details = await client.test_connection()
        return ConnectionTestResult(success=ok, message=msg, details=details)

    elif conn.connection_type in {
        ConnectionType.sap_re,
        ConnectionType.planon,
        ConnectionType.costar,
        ConnectionType.servicenow_wsd,
    }:
        from app.source_connectors.factory import build_source_connector

        connector = build_source_connector(
            connection_type=conn.connection_type,
            base_url=conn.base_url or "",
            credentials=credentials,
        )
        ok, msg, details = await connector.test_connection()
        return ConnectionTestResult(success=ok, message=msg, details=details)

    return ConnectionTestResult(success=False, message="Unknown connection type")
