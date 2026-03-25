"""Unit tests for Stage0 client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.schemas.stage0 import Stage0Request
from src.stage0.client import Stage0Client
from src.stage0.exceptions import (
    Stage0ConnectionError,
    Stage0TimeoutError,
)


def _create_async_client_mock(mock_context: AsyncMock) -> MagicMock:
    """Create a mock for httpx.AsyncClient that works as async context manager."""

    async def mock_aenter(*args):
        return mock_context

    async def mock_aexit(*args):
        return None

    mock_instance = MagicMock()
    mock_instance.__aenter__ = mock_aenter
    mock_instance.__aexit__ = mock_aexit
    return mock_instance


class TestStage0Client:
    def test_client_initialization(self):
        client = Stage0Client(
            base_url="https://test.example.com",
            api_key="test-key",
            timeout_seconds=10,
        )
        assert client.base_url == "https://test.example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 10

    def test_is_configured_true(self):
        client = Stage0Client(api_key="test-key")
        assert client.is_configured() is True

    def test_is_configured_false(self):
        client = Stage0Client(api_key="")
        assert client.is_configured() is False

    @pytest.mark.asyncio
    async def test_check_success(self):
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")
        request = Stage0Request(
            goal="Test goal",
            tools=["test_tool"],
            side_effects=["test_effect"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "decision": "GO",
            "verdict": "ALLOW",
            "request_id": "req_test123",
            "issues": [],
            "risk_score": 10.0,
        }

        mock_context = AsyncMock()
        mock_context.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.stage0.client.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            response = await client.check(request)

            assert response.verdict == "ALLOW"
            assert response.decision == "GO"
            assert response.request_id == "req_test123"

    @pytest.mark.asyncio
    async def test_check_timeout_raises_timeout_error(self):
        client = Stage0Client(
            base_url="https://test.example.com", api_key="test-key", timeout_seconds=1
        )
        request = Stage0Request(goal="Test goal")

        mock_context = AsyncMock()
        mock_context.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch(
            "src.stage0.client.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(Stage0TimeoutError):
                await client.check(request)

    @pytest.mark.asyncio
    async def test_check_connection_error(self):
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")
        request = Stage0Request(goal="Test goal")

        mock_context = AsyncMock()
        mock_context.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

        with patch(
            "src.stage0.client.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(Stage0ConnectionError):
                await client.check(request)

    @pytest.mark.asyncio
    async def test_check_500_error_raises_connection_error(self):
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")
        request = Stage0Request(goal="Test goal")

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_context = AsyncMock()
        mock_context.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.stage0.client.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(Stage0ConnectionError):
                await client.check(request)

    @pytest.mark.asyncio
    async def test_check_missing_verdict_raises_connection_error(self):
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")
        request = Stage0Request(goal="Test goal")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"decision": "GO"}

        mock_context = AsyncMock()
        mock_context.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.stage0.client.httpx.AsyncClient",
            return_value=_create_async_client_mock(mock_context),
        ):
            with pytest.raises(Stage0ConnectionError, match="missing required 'verdict'"):
                await client.check(request)
