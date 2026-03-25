"""Derived signal schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from src.schemas.common import BaseSchema


class DerivedSignalResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    symbol: str
    signal_type: str
    event_timestamp: datetime
    value: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: float | None
    is_anomaly: bool
    data_freshness_seconds: float | None
    computation_window: int | None
    created_at: datetime
