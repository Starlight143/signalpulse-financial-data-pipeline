"""Health check schemas."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from src.schemas.common import BaseSchema

DataSourceStatus = Literal["healthy", "degraded", "unhealthy", "unknown"]


class DataSourceHealth(BaseSchema):
    name: str
    exchange: str
    status: DataSourceStatus
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None
    fetch_count: int = 0
    error_count: int = 0
    avg_latency_seconds: float | None = None


class HealthCheckResponse(BaseSchema):
    status: Literal["healthy", "unhealthy"]
    app_name: str
    version: str
    timestamp: datetime


class ReadinessResponse(BaseSchema):
    status: Literal["ready", "not_ready"]
    app_name: str
    timestamp: datetime
    database_connected: bool
    stage0_configured: bool
    stage0_mode: str
    data_sources: list[DataSourceHealth] = Field(default_factory=list)
