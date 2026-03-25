"""Market data service."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot


class MarketService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_snapshots(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshot_type: str | None = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[NormalizedMarketSnapshot]:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        conditions = [
            NormalizedMarketSnapshot.workspace_id == workspace_id,
            NormalizedMarketSnapshot.symbol == symbol.upper(),
            NormalizedMarketSnapshot.event_timestamp >= cutoff,
        ]

        if snapshot_type:
            conditions.append(NormalizedMarketSnapshot.snapshot_type == snapshot_type)

        stmt = (
            select(NormalizedMarketSnapshot)
            .where(and_(*conditions))
            .order_by(desc(NormalizedMarketSnapshot.event_timestamp))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_signals(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        signal_type: str | None = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[DerivedSignal]:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        conditions = [
            DerivedSignal.workspace_id == workspace_id,
            DerivedSignal.symbol == symbol.upper(),
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

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_aggregated_features(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
    ) -> dict[str, Any]:
        signals = await self.get_latest_signals(
            workspace_id=workspace_id,
            symbol=symbol,
            hours=24,
            limit=50,
        )

        features: dict[str, float | None] = {}
        metadata: dict[str, Any] = {}

        for signal in signals:
            if signal.signal_type not in features:
                features[signal.signal_type] = signal.value
                metadata[signal.signal_type] = signal.signal_metadata

        latest = signals[0] if signals else None

        return {
            "symbol": symbol.upper(),
            "timestamp": latest.event_timestamp if latest else None,
            "features": features,
            "metadata": metadata,
            "is_anomaly": latest.is_anomaly if latest else False,
            "quality_score": latest.quality_score if latest else None,
            "data_freshness_seconds": latest.data_freshness_seconds if latest else None,
        }
