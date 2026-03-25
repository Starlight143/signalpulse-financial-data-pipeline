"""Ingestion service."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.features.calculator import FeatureEngine
from src.ingestion.worker import IngestionWorker
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot

settings = get_settings()
logger = structlog.get_logger()


class IngestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.feature_engine = FeatureEngine()

    async def run_ingestion(
        self,
        workspace_id: uuid.UUID,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        effective_symbols = [s.upper() for s in symbols] if symbols else settings.supported_symbols_list
        worker = IngestionWorker(symbols=effective_symbols)
        results = await worker.run_once(workspace_id)

        successful = sum(1 for r in results.values() if r.success)
        total = len(results)

        logger.info(
            "ingestion_complete",
            workspace_id=str(workspace_id),
            successful=successful,
            total=total,
        )

        return {
            "successful": successful,
            "total": total,
            "results": {
                k: {
                    "success": v.success,
                    "records_stored": v.records_stored,
                }
                for k, v in results.items()
            },
        }

    async def calculate_features(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
    ) -> list[DerivedSignal]:
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        stmt = (
            select(NormalizedMarketSnapshot)
            .where(
                and_(
                    NormalizedMarketSnapshot.workspace_id == workspace_id,
                    NormalizedMarketSnapshot.symbol == symbol.upper(),
                    NormalizedMarketSnapshot.event_timestamp >= cutoff,
                )
            )
            .order_by(desc(NormalizedMarketSnapshot.event_timestamp))
            .limit(200)
        )

        result = await self.session.execute(stmt)
        snapshots = list(result.scalars().all())

        signals = self.feature_engine.calculate_all(
            snapshots=snapshots,
            workspace_id=workspace_id,
        )

        for signal in signals:
            self.session.add(signal)

        await self.session.flush()

        logger.info(
            "features_calculated",
            symbol=symbol,
            signal_count=len(signals),
        )

        return signals
