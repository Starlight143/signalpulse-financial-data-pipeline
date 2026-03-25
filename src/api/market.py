"""Market data API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_session
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot
from src.schemas.market import (
    MarketFeaturesResponse,
    MarketSignalsResponse,
    MarketSnapshotResponse,
    SignalItem,
)

router = APIRouter()
settings = get_settings()


def _get_default_workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/{symbol}/snapshot", response_model=list[MarketSnapshotResponse])
async def get_market_snapshot(
    symbol: str,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    snapshot_type: str | None = Query(
        None, description="Filter by snapshot type (ohlcv, funding_rate)"
    ),
    exchange: str | None = Query(None, description="Filter by exchange"),
    hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[MarketSnapshotResponse]:
    symbol = symbol.upper()

    if symbol not in settings.supported_symbols_list:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{symbol}' not in allowed list: {settings.supported_symbols_list}",
        )

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    conditions = [
        NormalizedMarketSnapshot.workspace_id == workspace_id,
        NormalizedMarketSnapshot.symbol == symbol,
        NormalizedMarketSnapshot.event_timestamp >= cutoff,
    ]

    if snapshot_type:
        conditions.append(NormalizedMarketSnapshot.snapshot_type == snapshot_type)
    if exchange:
        conditions.append(NormalizedMarketSnapshot.exchange == exchange.lower())

    stmt = (
        select(NormalizedMarketSnapshot)
        .where(and_(*conditions))
        .order_by(desc(NormalizedMarketSnapshot.event_timestamp))
        .limit(limit)
    )

    result = await session.execute(stmt)
    snapshots = result.scalars().all()

    return [MarketSnapshotResponse.model_validate(s) for s in snapshots]


@router.get("/{symbol}/features", response_model=MarketFeaturesResponse)
async def get_market_features(
    symbol: str,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    session: AsyncSession = Depends(get_session),
) -> MarketFeaturesResponse:
    symbol = symbol.upper()

    if symbol not in settings.supported_symbols_list:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{symbol}' not in allowed list",
        )

    cutoff = datetime.now(UTC) - timedelta(hours=24)

    stmt = (
        select(DerivedSignal)
        .where(
            and_(
                DerivedSignal.workspace_id == workspace_id,
                DerivedSignal.symbol == symbol,
                DerivedSignal.event_timestamp >= cutoff,
            )
        )
        .order_by(desc(DerivedSignal.event_timestamp))
        .limit(50)
    )

    result = await session.execute(stmt)
    signals = result.scalars().all()

    features: dict[str, float | None] = {
        "funding_diff": None,
        "mid_price": None,
        "spread_proxy": None,
        "rolling_zscore": None,
        "volatility_proxy": None,
        "data_freshness_seconds": None,
        "quality_score": None,
    }

    metadata: dict[str, Any] = {}

    for signal in signals:
        if signal.signal_type in features and features[signal.signal_type] is None:
            features[signal.signal_type] = signal.value
            if signal.signal_metadata:
                metadata[signal.signal_type] = signal.signal_metadata
        if signal.signal_type == "funding_zscore" and features["rolling_zscore"] is None:
            features["rolling_zscore"] = signal.value

    latest_signal = signals[0] if signals else None

    return MarketFeaturesResponse(
        symbol=symbol,
        timestamp=latest_signal.event_timestamp if latest_signal else datetime.now(UTC),
        funding_diff=features.get("funding_diff"),
        mid_price=features.get("mid_price"),
        spread_proxy=features.get("spread_proxy"),
        rolling_zscore=features.get("rolling_zscore"),
        volatility_proxy=features.get("volatility_proxy"),
        data_freshness_seconds=latest_signal.data_freshness_seconds if latest_signal else None,
        quality_score=latest_signal.quality_score if latest_signal else None,
        is_anomaly=latest_signal.is_anomaly if latest_signal else False,
        metadata=metadata,
    )


@router.get("/{symbol}/signals", response_model=MarketSignalsResponse)
async def get_market_signals(
    symbol: str,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    signal_type: str | None = Query(None, description="Filter by signal type"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> MarketSignalsResponse:
    symbol = symbol.upper()

    if symbol not in settings.supported_symbols_list:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{symbol}' not in allowed list",
        )

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    conditions = [
        DerivedSignal.workspace_id == workspace_id,
        DerivedSignal.symbol == symbol,
        DerivedSignal.event_timestamp >= cutoff,
    ]

    if signal_type:
        conditions.append(DerivedSignal.signal_type == signal_type)

    stmt = (
        select(DerivedSignal)
        .where(and_(*conditions))
        .order_by(desc(DerivedSignal.event_timestamp))
        .limit(limit)
    )

    result = await session.execute(stmt)
    signals = result.scalars().all()

    signal_items = [
        SignalItem(
            signal_type=s.signal_type,
            value=s.value,
            timestamp=s.event_timestamp,
            quality_score=s.quality_score,
            is_anomaly=s.is_anomaly,
        )
        for s in signals
    ]

    latest = signals[0] if signals else None

    return MarketSignalsResponse(
        symbol=symbol,
        signals=signal_items,
        latest_timestamp=latest.event_timestamp if latest else None,
        data_freshness_seconds=latest.data_freshness_seconds if latest else None,
    )
