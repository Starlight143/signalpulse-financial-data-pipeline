"""Bybit data ingestor."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config import get_settings
from src.ingestion.base import BaseIngestor
from src.ingestion.exceptions import (
    IngestionConnectionError,
    IngestionDataError,
    IngestionRateLimitError,
)

settings = get_settings()


class BybitIngestor(BaseIngestor):
    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_per_minute: int | None = None,
    ):
        super().__init__(
            exchange="bybit",
            base_url=base_url or settings.bybit_base_url,
        )
        self.rate_limit_per_minute = rate_limit_per_minute or settings.bybit_rate_limit_per_minute
        self._last_request_time: float = 0.0
        self._min_interval = 60.0 / self.rate_limit_per_minute
        self._rate_limit_lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
        async with self._rate_limit_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> Any:
        await self._rate_limit()
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
            except httpx.TimeoutException as e:
                raise IngestionConnectionError(
                    f"Bybit request timeout: {e}",
                    exchange=self.exchange,
                ) from e
            except httpx.RequestError as e:
                raise IngestionConnectionError(
                    f"Bybit connection error: {e}",
                    exchange=self.exchange,
                ) from e

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise IngestionRateLimitError(retry_after, exchange=self.exchange)

            if response.status_code >= 500:
                raise IngestionConnectionError(
                    f"Bybit server error: HTTP {response.status_code}",
                    exchange=self.exchange,
                )

            if response.status_code >= 400:
                raise IngestionDataError(
                    f"Bybit API error: HTTP {response.status_code}",
                    raw_data={"status_code": response.status_code, "body": response.text},
                    exchange=self.exchange,
                )

            try:
                data = response.json()
            except Exception as e:
                raise IngestionDataError(
                    f"Bybit invalid JSON response: {e}",
                    raw_data={"body": response.text[:500]},
                    exchange=self.exchange,
                ) from e

            if data.get("retCode", 0) != 0:
                raise IngestionDataError(
                    f"Bybit API error: {data.get('retMsg', 'Unknown error')}",
                    raw_data=data,
                    exchange=self.exchange,
                )

            return data.get("result", {})

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "60",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        interval_map = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "6h": "360",
            "12h": "720",
            "1d": "D",
            "1w": "W",
            "1M": "M",
        }
        bybit_interval = interval_map.get(interval, interval)

        params: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol.upper(),
            "interval": bybit_interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["start"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["end"] = int(end_time.timestamp() * 1000)

        result = await self._request("/v5/market/kline", params)
        raw_list = result.get("list", [])

        return [
            {
                "exchange": self.exchange,
                "symbol": symbol.upper(),
                "interval": interval,
                "open_time": int(item[0]),
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "volume": item[5],
                "turnover": item[6],
            }
            for item in raw_list
        ]

    async def fetch_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol.upper(),
            "limit": min(limit, 200),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        result = await self._request("/v5/market/funding/history", params)
        raw_list = result.get("list", [])

        return [
            {
                "exchange": self.exchange,
                "symbol": item["symbol"],
                "funding_rate": item["fundingRate"],
                "funding_time": int(item["fundingRateTimestamp"]),
            }
            for item in raw_list
        ]

    def normalize_ohlcv(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        open_time = raw_data["open_time"]
        event_timestamp = datetime.fromtimestamp(open_time / 1000, tz=UTC)

        return {
            "snapshot_type": "ohlcv",
            "symbol": raw_data["symbol"],
            "exchange": raw_data["exchange"],
            "event_timestamp": event_timestamp,
            "open_price": float(raw_data["open"]),
            "high_price": float(raw_data["high"]),
            "low_price": float(raw_data["low"]),
            "close_price": float(raw_data["close"]),
            "volume": float(raw_data["volume"]),
            "turnover": float(raw_data["turnover"]) if raw_data.get("turnover") else None,
            "funding_rate": None,
            "mark_price": None,
            "next_funding_time": None,
            "raw_payload": raw_data,
        }

    def normalize_funding_rate(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        funding_time = raw_data["funding_time"]
        event_timestamp = datetime.fromtimestamp(funding_time / 1000, tz=UTC)

        return {
            "snapshot_type": "funding_rate",
            "symbol": raw_data["symbol"],
            "exchange": raw_data["exchange"],
            "event_timestamp": event_timestamp,
            "open_price": None,
            "high_price": None,
            "low_price": None,
            "close_price": None,
            "volume": None,
            "turnover": None,
            "funding_rate": float(raw_data["funding_rate"]),
            "mark_price": None,
            "next_funding_time": None,
            "raw_payload": raw_data,
        }
