"""Binance data ingestor."""

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


class BinanceIngestor(BaseIngestor):
    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_per_minute: int | None = None,
    ):
        super().__init__(
            exchange="binance",
            base_url=base_url or settings.binance_base_url,
        )
        self.rate_limit_per_minute = rate_limit_per_minute or settings.binance_rate_limit_per_minute
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
                    f"Binance request timeout: {e}",
                    exchange=self.exchange,
                ) from e
            except httpx.RequestError as e:
                raise IngestionConnectionError(
                    f"Binance connection error: {e}",
                    exchange=self.exchange,
                ) from e

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise IngestionRateLimitError(retry_after, exchange=self.exchange)

            if response.status_code >= 500:
                raise IngestionConnectionError(
                    f"Binance server error: HTTP {response.status_code}",
                    exchange=self.exchange,
                )

            if response.status_code >= 400:
                raise IngestionDataError(
                    f"Binance API error: HTTP {response.status_code}",
                    raw_data={"status_code": response.status_code, "body": response.text},
                    exchange=self.exchange,
                )

            try:
                return response.json()
            except Exception as e:
                raise IngestionDataError(
                    f"Binance invalid JSON response: {e}",
                    raw_data={"body": response.text[:500]},
                    exchange=self.exchange,
                ) from e

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1500),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        data = await self._request("/fapi/v1/klines", params)

        if not isinstance(data, list):
            raise IngestionDataError(
                "Binance OHLCV response is not a list",
                raw_data=data,
                exchange=self.exchange,
            )

        return [
            {
                "exchange": self.exchange,
                "symbol": symbol.upper(),
                "interval": interval,
                "open_time": item[0],
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "volume": item[5],
                "close_time": item[6],
                "quote_volume": item[7],
                "trades": item[8],
                "taker_buy_base": item[9],
                "taker_buy_quote": item[10],
            }
            for item in data
        ]

    async def fetch_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "limit": min(limit, 1000),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        data = await self._request("/fapi/v1/fundingRate", params)

        if not isinstance(data, list):
            raise IngestionDataError(
                "Binance funding rate response is not a list",
                raw_data=data,
                exchange=self.exchange,
            )

        return [
            {
                "exchange": self.exchange,
                "symbol": item["symbol"],
                "funding_rate": item["fundingRate"],
                "funding_time": item["fundingTime"],
                "mark_price": item.get("markPrice"),
            }
            for item in data
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
            "turnover": float(raw_data["quote_volume"]) if raw_data.get("quote_volume") else None,
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
            "mark_price": float(raw_data["mark_price"]) if raw_data.get("mark_price") else None,
            "next_funding_time": None,
            "raw_payload": raw_data,
        }
