"""Market data schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.schemas.common import BaseSchema


class MarketSnapshotBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    snapshot_type: str
    event_timestamp: datetime


class MarketSnapshotResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    symbol: str
    snapshot_type: str
    event_timestamp: datetime
    open_price: float | None
    high_price: float | None
    low_price: float | None
    close_price: float | None
    volume: float | None
    turnover: float | None
    funding_rate: float | None
    mark_price: float | None
    next_funding_time: datetime | None
    exchange: str
    created_at: datetime


class MarketFeaturesResponse(BaseSchema):
    symbol: str
    timestamp: datetime
    funding_diff: float | None
    mid_price: float | None
    spread_proxy: float | None
    rolling_zscore: float | None
    volatility_proxy: float | None
    data_freshness_seconds: float | None
    quality_score: float | None
    is_anomaly: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketSignalsResponse(BaseSchema):
    symbol: str
    signals: list["SignalItem"]
    latest_timestamp: datetime | None
    data_freshness_seconds: float | None


class SignalItem(BaseSchema):
    signal_type: str
    value: float
    timestamp: datetime
    quality_score: float | None
    is_anomaly: bool
