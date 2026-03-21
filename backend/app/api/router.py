from fastapi import APIRouter

from app.api import connections, kontracts, logs, mappings, runs, tririga

api_router = APIRouter()

api_router.include_router(
    connections.router, prefix="/connections", tags=["connections"]
)
api_router.include_router(
    tririga.router, prefix="/tririga", tags=["tririga"]
)
api_router.include_router(
    kontracts.router, prefix="/kontracts", tags=["kontracts"]
)
api_router.include_router(
    mappings.router, prefix="/mappings", tags=["mappings"]
)
api_router.include_router(
    runs.router, prefix="/runs", tags=["runs"]
)
api_router.include_router(
    logs.router, prefix="/logs", tags=["logs"]
)
