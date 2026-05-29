import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TRIRIGA-Kontracts Integration API",
    description=(
        "Integration platform bridging IBM TRIRIGA (SOAP) "
        "with the Kontracts lease accounting REST API"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    return JSONResponse(
        {"status": "ok", "demo_mode": settings.demo_mode, "version": "1.0.0"}
    )


def _build_openapi_schema() -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "GitHubToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "GitHub OAuth Token",
            "description": (
                "GitHub OAuth access token issued after signing in with GitHub via NextAuth. "
                "Paste the value of `session.accessToken` from your browser session, "
                "or use a GitHub personal access token with the `read:user` scope."
            ),
        }
    }

    # Apply the security requirement to every operation under /api/v1.
    # /health is intentionally left public.
    for path, path_item in schema.get("paths", {}).items():
        if path.startswith("/api/v1"):
            for operation in path_item.values():
                if isinstance(operation, dict):
                    operation["security"] = [{"GitHubToken": []}]

    return schema


@app.on_event("startup")
async def startup_event():
    logger.info("TRIRIGA-Kontracts Integration API starting up")
    if settings.demo_mode:
        logger.info("DEMO MODE enabled — using fixture data")
    if not settings.fernet_key:
        logger.warning(
            "FERNET_KEY not set — credentials will not be encrypted properly"
        )
    # Cache the OpenAPI schema once at startup so it is consistent.
    app.openapi_schema = _build_openapi_schema()
    await _mark_orphaned_runs_failed()


async def _mark_orphaned_runs_failed():
    """Mark any pending/running runs as failed — they were killed by a restart."""
    from datetime import datetime, timezone
    from sqlalchemy import update as sql_update
    from app.database import AsyncSessionLocal
    from app.models.sync_run import RunStatus, SyncRun

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            sql_update(SyncRun)
            .where(SyncRun.status.in_([RunStatus.pending, RunStatus.running]))
            .values(
                status=RunStatus.failed,
                error_message="Run was interrupted by a server restart.",
                completed_at=datetime.now(timezone.utc),
            )
            .returning(SyncRun.id)
        )
        orphaned_ids = [row[0] for row in result.fetchall()]
        await db.commit()

    if orphaned_ids:
        logger.warning(
            "Marked %d orphaned run(s) as failed on startup: %s",
            len(orphaned_ids),
            orphaned_ids,
        )
