"""Data normalizer for converting raw data to unified schema."""

import uuid
from datetime import UTC, datetime
from typing import Any

from src.ingestion.base import BaseIngestor
from src.ingestion.binance import BinanceIngestor
from src.ingestion.bybit import BybitIngestor


class DataNormalizer:
    def __init__(self) -> None:
        self._ingestors: dict[str, BaseIngestor] = {}

    def get_ingestor(self, exchange: str) -> BaseIngestor:
        exchange_lower = exchange.lower()
        if exchange_lower not in self._ingestors:
            if exchange_lower == "binance":
                self._ingestors[exchange_lower] = BinanceIngestor()
            elif exchange_lower == "bybit":
                self._ingestors[exchange_lower] = BybitIngestor()
            else:
                raise ValueError(f"Unsupported exchange: {exchange}")
        return self._ingestors[exchange_lower]

    def normalize(
        self,
        raw_data: dict[str, Any],
        data_type: str,
        exchange: str,
    ) -> dict[str, Any]:
        ingestor = self.get_ingestor(exchange)

        if data_type == "ohlcv":
            return ingestor.normalize_ohlcv(raw_data)
        elif data_type == "funding_rate":
            return ingestor.normalize_funding_rate(raw_data)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def create_raw_event(
        self,
        workspace_id: uuid.UUID,
        data_source_id: uuid.UUID,
        raw_data: dict[str, Any],
        data_type: str,
        symbol: str,
        exchange: str,
        ingestion_job_id: str | None = None,
    ) -> dict[str, Any]:
        raw_payload = raw_data.get("raw_payload", raw_data)

        event_timestamp: datetime
        if "event_timestamp" in raw_data:
            event_timestamp = raw_data["event_timestamp"]
        elif "open_time" in raw_data:
            event_timestamp = datetime.fromtimestamp(raw_data["open_time"] / 1000, tz=UTC)
        elif "funding_time" in raw_data:
            event_timestamp = datetime.fromtimestamp(raw_data["funding_time"] / 1000, tz=UTC)
        else:
            event_timestamp = datetime.now(UTC)

        return {
            "workspace_id": workspace_id,
            "data_source_id": data_source_id,
            "event_type": data_type,
            "symbol": symbol.upper(),
            "exchange": exchange.lower(),
            "event_timestamp": event_timestamp,
            "raw_payload": raw_payload,
            "ingestion_job_id": ingestion_job_id,
        }

    def create_normalized_snapshot(
        self,
        workspace_id: uuid.UUID,
        raw_event_id: uuid.UUID,
        normalized_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "workspace_id": workspace_id,
            "raw_event_id": raw_event_id,
            **{k: v for k, v in normalized_data.items() if k != "raw_payload"},
        }
