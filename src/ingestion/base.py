"""Base ingestor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class IngestionResult:
    success: bool
    exchange: str
    symbol: str
    data_type: str
    records_fetched: int = 0
    records_stored: int = 0
    raw_records: list[dict[str, Any]] = field(default_factory=list)
    normalized_records: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None
    latency_seconds: float | None = None
    event_timestamp_range: tuple[datetime, datetime] | None = None


class BaseIngestor(ABC):
    def __init__(self, exchange: str, base_url: str):
        self.exchange = exchange
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def normalize_ohlcv(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    def normalize_funding_rate(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        pass

    def validate_symbol(self, symbol: str, allowed_symbols: list[str]) -> bool:
        return symbol.upper() in [s.upper() for s in allowed_symbols]

    def calculate_freshness(self, event_timestamp: datetime) -> float:
        # Normalize naive timestamps to UTC before comparison to avoid TypeError.
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=UTC)
        return (datetime.now(UTC) - event_timestamp).total_seconds()
