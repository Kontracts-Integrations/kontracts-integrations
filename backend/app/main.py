import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.on_event("startup")
async def startup_event():
    logger.info("TRIRIGA-Kontracts Integration API starting up")
    if settings.demo_mode:
        logger.info("DEMO MODE enabled — using fixture data")
    if not settings.fernet_key:
        logger.warning(
            "FERNET_KEY not set — credentials will not be encrypted properly"
        )
