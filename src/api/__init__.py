"""API router configuration."""

from fastapi import APIRouter

from src.api.actions import router as actions_router
from src.api.health import router as health_router
from src.api.ingest import router as ingest_router
from src.api.market import router as market_router
from src.api.stage0 import router as stage0_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(actions_router, prefix="/actions", tags=["actions"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(stage0_router, prefix="/stage0", tags=["stage0"])
