"""Health check API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_session
from src.models.data_source import DataSource
from src.schemas.health import (
    DataSourceHealth,
    HealthCheckResponse,
    ReadinessResponse,
)
from src.stage0 import get_stage0_adapter

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.app_name,
        version="1.0.0",
        timestamp=datetime.now(UTC),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    session: AsyncSession = Depends(get_session),
) -> ReadinessResponse:
    database_connected = False
    try:
        await session.execute(select(1))
        database_connected = True
    except Exception:
        pass

    stage0_adapter = get_stage0_adapter()
    stage0_configured = not stage0_adapter.is_mock()

    data_sources = await _get_data_source_health(session)

    all_healthy = database_connected and len(data_sources) > 0

    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        app_name=settings.app_name,
        timestamp=datetime.now(UTC),
        database_connected=database_connected,
        stage0_configured=stage0_configured,
        stage0_mode="mock" if stage0_adapter.is_mock() else "live",
        data_sources=data_sources,
    )


@router.get("/sources/health", response_model=list[DataSourceHealth])
async def sources_health(
    session: AsyncSession = Depends(get_session),
) -> list[DataSourceHealth]:
    return await _get_data_source_health(session)


async def _get_data_source_health(session: AsyncSession) -> list[DataSourceHealth]:
    result = await session.execute(select(DataSource).where(DataSource.is_active.is_(True)))
    data_sources = result.scalars().all()

    health_list: list[DataSourceHealth] = []
    for ds in data_sources:
        if ds.last_error_at and (not ds.last_success_at or ds.last_error_at > ds.last_success_at):
            status = "unhealthy"
        elif ds.last_success_at:
            status = "healthy"
        else:
            status = "unknown"

        health_list.append(
            DataSourceHealth(
                name=ds.name,
                exchange=ds.exchange,
                status=status,
                last_success_at=ds.last_success_at,
                last_error_at=ds.last_error_at,
                last_error_message=ds.last_error_message,
                fetch_count=ds.fetch_count,
                error_count=ds.error_count,
                avg_latency_seconds=ds.avg_latency_seconds,
            )
        )

    return health_list
