"""Ingestion worker for scheduled data collection."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import async_session_factory
from src.ingestion.base import IngestionResult
from src.ingestion.binance import BinanceIngestor
from src.ingestion.bybit import BybitIngestor
from src.ingestion.normalizer import DataNormalizer
from src.models.data_source import DataSource
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot
from src.models.raw_market_event import RawMarketEvent
from src.models.workspace import Workspace

settings = get_settings()
logger = structlog.get_logger()


class IngestionWorker:
    def __init__(
        self,
        symbols: list[str] | None = None,
        interval_seconds: int | None = None,
    ):
        self.symbols = symbols or settings.supported_symbols_list
        self.interval_seconds = interval_seconds or settings.ingestion_interval_seconds
        self.binance = BinanceIngestor()
        self.bybit = BybitIngestor()
        self.normalizer = DataNormalizer()
        self._running = False

    async def run_once(self, workspace_id: uuid.UUID) -> dict[str, IngestionResult]:
        results: dict[str, IngestionResult] = {}
        job_id = f"ingest_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        async with async_session_factory() as session:
            workspace = await session.get(Workspace, workspace_id)
            if not workspace or not workspace.is_active:
                logger.error("workspace_not_found_or_inactive", workspace_id=str(workspace_id))
                return results

            stmt = select(DataSource).where(
                DataSource.workspace_id == workspace_id,
                DataSource.is_active.is_(True),
            )
            db_result = await session.execute(stmt)
            data_sources = db_result.scalars().all()

            if not data_sources:
                data_source = await self._ensure_data_source(session, workspace_id)
                data_sources = [data_source]

            data_source_id = data_sources[0].id

            # Build the full task matrix.
            task_keys = [
                (symbol, exchange, data_type)
                for symbol in self.symbols
                for exchange in ["binance", "bybit"]
                for data_type in ["funding_rate", "ohlcv"]
            ]

            # Phase 1: Fetch all data in parallel (pure I/O, no DB writes).
            fetch_results: list[list[dict[str, Any]] | BaseException] = list(
                await asyncio.gather(
                    *[
                        self._fetch_single(symbol, exchange, data_type)
                        for symbol, exchange, data_type in task_keys
                    ],
                    return_exceptions=True,
                )
            )

            # Phase 2: Store results sequentially within a single session.
            for (symbol, exchange, data_type), fetch_result in zip(task_keys, fetch_results):
                key = f"{exchange}:{symbol}:{data_type}"
                if isinstance(fetch_result, BaseException):
                    logger.error(
                        "ingestion_fetch_failed",
                        exchange=exchange,
                        symbol=symbol,
                        data_type=data_type,
                        error=str(fetch_result),
                    )
                    results[key] = IngestionResult(
                        success=False,
                        exchange=exchange,
                        symbol=symbol,
                        data_type=data_type,
                        error_message=str(fetch_result),
                    )
                    continue

                try:
                    result = await self._store_records(
                        session=session,
                        workspace_id=workspace_id,
                        data_source_id=data_source_id,
                        symbol=symbol,
                        exchange=exchange,
                        data_type=data_type,
                        raw_records=fetch_result,
                        job_id=job_id,
                    )
                    results[key] = result
                except Exception as e:
                    logger.error(
                        "ingestion_store_failed",
                        exchange=exchange,
                        symbol=symbol,
                        data_type=data_type,
                        error=str(e),
                    )
                    results[key] = IngestionResult(
                        success=False,
                        exchange=exchange,
                        symbol=symbol,
                        data_type=data_type,
                        error_message=str(e),
                    )

            await session.commit()

        return results

    async def _fetch_single(
        self,
        symbol: str,
        exchange: str,
        data_type: str,
    ) -> list[dict[str, Any]]:
        """Fetch raw records from an exchange. No DB access — safe to run concurrently."""
        ingestor = self.binance if exchange == "binance" else self.bybit
        end_dt = datetime.now(UTC)
        start_dt = end_dt - timedelta(hours=24)

        if data_type == "ohlcv":
            return await ingestor.fetch_ohlcv(
                symbol=symbol,
                interval="1h",
                start_time=start_dt,
                end_time=end_dt,
            )
        else:
            return await ingestor.fetch_funding_rate(
                symbol=symbol,
                start_time=start_dt,
                end_time=end_dt,
            )

    async def _store_records(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data_source_id: uuid.UUID,
        symbol: str,
        exchange: str,
        data_type: str,
        raw_records: list[dict[str, Any]],
        job_id: str,
    ) -> IngestionResult:
        start_time = datetime.now(UTC)

        if not raw_records:
            return IngestionResult(
                success=True,
                exchange=exchange,
                symbol=symbol,
                data_type=data_type,
                records_fetched=0,
                records_stored=0,
                latency_seconds=0.0,
            )

        # Normalize all fetched records to determine their event_timestamps.
        normalized_records = [
            (self.normalizer.normalize(r, data_type, exchange), r) for r in raw_records
        ]

        # Pre-filter: query which event_timestamps already exist for this key.
        # This prevents duplicate raw_events and avoids unique-constraint violations
        # on normalized_market_snapshots on repeated ingestion runs.
        all_timestamps = [n["event_timestamp"] for n, _ in normalized_records]
        existing_stmt = select(NormalizedMarketSnapshot.event_timestamp).where(
            NormalizedMarketSnapshot.workspace_id == workspace_id,
            NormalizedMarketSnapshot.symbol == symbol.upper(),
            NormalizedMarketSnapshot.exchange == exchange,
            NormalizedMarketSnapshot.snapshot_type == data_type,
            NormalizedMarketSnapshot.event_timestamp.in_(all_timestamps),
        )
        existing_result = await session.execute(existing_stmt)
        existing_timestamps = {row[0] for row in existing_result.all()}

        new_records = [
            (normalized, raw)
            for normalized, raw in normalized_records
            if normalized["event_timestamp"] not in existing_timestamps
        ]

        if not new_records:
            latency = (datetime.now(UTC) - start_time).total_seconds()
            logger.debug(
                "ingestion_all_records_exist",
                exchange=exchange,
                symbol=symbol,
                data_type=data_type,
                records_fetched=len(raw_records),
                latency_seconds=latency,
            )
            return IngestionResult(
                success=True,
                exchange=exchange,
                symbol=symbol,
                data_type=data_type,
                records_fetched=len(raw_records),
                records_stored=0,
                latency_seconds=latency,
            )

        # Assign Python-side UUIDs upfront so snapshots can reference them
        # before any flush occurs — enables a single bulk flush for both tables.
        raw_events: list[RawMarketEvent] = []
        snapshots: list[NormalizedMarketSnapshot] = []

        for normalized, raw in new_records:
            raw_event_id = uuid.uuid4()
            raw_events.append(
                RawMarketEvent(
                    id=raw_event_id,
                    workspace_id=workspace_id,
                    data_source_id=data_source_id,
                    event_type=data_type,
                    symbol=symbol.upper(),
                    exchange=exchange,
                    event_timestamp=normalized["event_timestamp"],
                    raw_payload=raw,
                    ingestion_job_id=job_id,
                )
            )
            snapshots.append(
                NormalizedMarketSnapshot(
                    workspace_id=workspace_id,
                    raw_event_id=raw_event_id,
                    symbol=normalized["symbol"],
                    snapshot_type=normalized["snapshot_type"],
                    event_timestamp=normalized["event_timestamp"],
                    open_price=normalized.get("open_price"),
                    high_price=normalized.get("high_price"),
                    low_price=normalized.get("low_price"),
                    close_price=normalized.get("close_price"),
                    volume=normalized.get("volume"),
                    turnover=normalized.get("turnover"),
                    funding_rate=normalized.get("funding_rate"),
                    mark_price=normalized.get("mark_price"),
                    exchange=exchange,
                )
            )

        # Single bulk flush for all new raw events and snapshots together.
        session.add_all(raw_events)
        session.add_all(snapshots)
        await session.flush()

        latency = (datetime.now(UTC) - start_time).total_seconds()

        logger.info(
            "ingestion_complete",
            exchange=exchange,
            symbol=symbol,
            data_type=data_type,
            records_fetched=len(raw_records),
            records_stored=len(new_records),
            records_skipped=len(raw_records) - len(new_records),
            latency_seconds=latency,
        )

        return IngestionResult(
            success=True,
            exchange=exchange,
            symbol=symbol,
            data_type=data_type,
            records_fetched=len(raw_records),
            records_stored=len(new_records),
            latency_seconds=latency,
        )

    async def _ensure_data_source(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> DataSource:
        stmt = select(DataSource).where(
            DataSource.workspace_id == workspace_id,
            DataSource.exchange == "binance",
        )
        db_result = await session.execute(stmt)
        existing_source = db_result.scalar_one_or_none()

        if existing_source is not None:
            return existing_source

        new_source = DataSource(
            workspace_id=workspace_id,
            name="Default Binance Source",
            source_type="funding_rate",
            exchange="binance",
            is_active=True,
        )
        session.add(new_source)
        await session.flush()

        return new_source

    async def run_forever(self, workspace_id: uuid.UUID) -> None:
        self._running = True
        while self._running:
            try:
                await self.run_once(workspace_id)
            except Exception as e:
                logger.error("ingestion_error", error=str(e))

            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False


async def main() -> None:
    import os

    workspace_id = uuid.UUID(os.environ.get("WORKSPACE_ID", "00000000-0000-0000-0000-000000000001"))
    worker = IngestionWorker()
    await worker.run_once(workspace_id)


if __name__ == "__main__":
    asyncio.run(main())
