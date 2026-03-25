"""Fail-closed tests for network failures."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ingestion.binance import BinanceIngestor
from src.ingestion.bybit import BybitIngestor
from src.ingestion.exceptions import (
    IngestionConnectionError,
    IngestionDataError,
    IngestionRateLimitError,
)


def _create_async_client_mock(mock_context: AsyncMock) -> MagicMock:
    async def mock_aenter(*args):
        return mock_context

    async def mock_aexit(*args):
        return None

    mock_instance = MagicMock()
    mock_instance.__aenter__ = mock_aenter
    mock_instance.__aexit__ = mock_aexit
    return mock_instance


class TestNetworkFailClosed:
    """Tests for network failure handling in ingestion."""

    @pytest.mark.asyncio
    async def test_binance_connection_error_is_isolated(self):
        """Connection errors are isolated and don't crash the system."""
        ingestor = BinanceIngestor()

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch(
            "src.ingestion.binance.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionConnectionError):
                await ingestor.fetch_ohlcv("BTCUSDT")

    @pytest.mark.asyncio
    async def test_binance_rate_limit_is_handled(self):
        """Rate limit errors are properly raised for backoff handling."""
        ingestor = BinanceIngestor()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(return_value=mock_response)

        with patch(
            "src.ingestion.binance.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionRateLimitError) as exc_info:
                await ingestor.fetch_ohlcv("BTCUSDT")

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_binance_invalid_json_is_handled(self):
        """Invalid JSON responses don't crash, they raise structured errors."""
        ingestor = BinanceIngestor()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "not valid json {{{"
        mock_response.json.side_effect = Exception("Invalid JSON")

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(return_value=mock_response)

        with patch(
            "src.ingestion.binance.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionDataError):
                await ingestor.fetch_ohlcv("BTCUSDT")

    @pytest.mark.asyncio
    async def test_bybit_error_response_is_handled(self):
        """Bybit API error responses are properly raised."""
        ingestor = BybitIngestor()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "retCode": 10001,
            "retMsg": "Invalid symbol",
            "result": {},
        }

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(return_value=mock_response)

        with patch(
            "src.ingestion.bybit.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionDataError, match="Invalid symbol"):
                await ingestor.fetch_ohlcv("INVALID")

    @pytest.mark.asyncio
    async def test_timeout_is_handled_gracefully(self):
        """Timeouts don't crash, they raise structured errors."""
        ingestor = BinanceIngestor()

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch(
            "src.ingestion.binance.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionConnectionError):
                await ingestor.fetch_ohlcv("BTCUSDT")

    @pytest.mark.asyncio
    async def test_server_error_is_handled(self):
        """Server errors (5xx) are properly raised."""
        ingestor = BinanceIngestor()

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        mock_context = AsyncMock()
        mock_context.get = AsyncMock(return_value=mock_response)

        with patch(
            "src.ingestion.binance.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(IngestionConnectionError, match="server error"):
                await ingestor.fetch_ohlcv("BTCUSDT")
