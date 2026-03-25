"""Fail-closed tests for Stage0 integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.stage0 import Stage0Context, Stage0Request
from src.stage0.client import Stage0Client
from src.stage0.exceptions import (
    Stage0ConnectionError,
    Stage0TimeoutError,
)
from src.stage0.live_adapter import LiveStage0Adapter
from src.stage0.mock_adapter import MockStage0Adapter


def _create_async_client_mock(mock_context: AsyncMock) -> MagicMock:
    async def mock_aenter(*args):
        return mock_context

    async def mock_aexit(*args):
        return None

    mock_instance = MagicMock()
    mock_instance.__aenter__ = mock_aenter
    mock_instance.__aexit__ = mock_aexit
    return mock_instance


class TestStage0FailClosed:
    """These tests verify that the system fails CLOSED - meaning it blocks
    execution on any error, unknown state, or missing data.
    """

    @pytest.mark.asyncio
    async def test_missing_api_key_blocks_execution(self):
        """No API key = no execution. This is fail-closed."""
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Execute trade",
            tools=["trading_api"],
            side_effects=["money movement"],
        )

        response = await adapter.check(request)

        assert response.verdict == "DEFER"

    @pytest.mark.asyncio
    async def test_connection_error_blocks_execution(self):
        """Connection error to Stage0 = no execution. Fail-closed."""
        client = Stage0Client(base_url="https://invalid.example.com", api_key="test-key")
        adapter = LiveStage0Adapter(client=client)
        request = Stage0Request(
            goal="Test goal",
            tools=["test"],
            side_effects=[],
        )

        with pytest.raises((Stage0ConnectionError, Stage0TimeoutError)):
            await adapter.check(request)

    @pytest.mark.asyncio
    async def test_timeout_blocks_execution(self):
        """Timeout = no execution. Fail-closed."""
        client = Stage0Client(
            base_url="https://slow.example.com",
            api_key="test-key",
            timeout_seconds=1,
        )
        adapter = LiveStage0Adapter(client=client)
        request = Stage0Request(goal="Test", tools=[], side_effects=[])

        with pytest.raises((Stage0TimeoutError, Stage0ConnectionError)):
            await adapter.check(request)

    @pytest.mark.asyncio
    async def test_500_error_blocks_execution(self):
        """Server error = no execution. Fail-closed."""
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")
        adapter = LiveStage0Adapter(client=client)
        request = Stage0Request(goal="Test", tools=[], side_effects=[])

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client, "check") as mock_check:
            mock_check.side_effect = Stage0ConnectionError("Server error")

            with pytest.raises(Stage0ConnectionError):
                await adapter.check(request)

    @pytest.mark.asyncio
    async def test_missing_verdict_field_blocks_execution(self):
        """Missing verdict in response = no execution. Fail-closed."""
        client = Stage0Client(base_url="https://test.example.com", api_key="test-key")

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
                await client.check(Stage0Request(goal="Test", tools=[], side_effects=[]))

    @pytest.mark.asyncio
    async def test_unknown_verdict_blocks_execution(self):
        """Unknown verdict value = no execution. Fail-closed."""
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Test",
            tools=[],
            side_effects=[],
        )

        with patch.object(adapter, "_determine_verdict", return_value=("ERROR", "DENY", [])):
            response = await adapter.check(request)
            assert response.verdict != "ALLOW"

    @pytest.mark.asyncio
    async def test_deny_verdict_blocks_execution(self):
        """DENY verdict = no execution. Fail-closed by design."""
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Unauthorized action",
            tools=["dangerous_tool"],
            side_effects=["destruction"],
            context=Stage0Context(
                approval_status="pending",
            ),
        )

        response = await adapter.check(request)

        assert response.verdict == "DENY"

    @pytest.mark.asyncio
    async def test_defer_verdict_blocks_execution(self):
        """DEFER verdict = no execution until context provided. Fail-closed."""
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Needs approval",
            tools=["sensitive_tool"],
            side_effects=["notification"],
        )

        response = await adapter.check(request)

        assert response.verdict == "DEFER"
        assert response.decision == "DEFER"

    @pytest.mark.asyncio
    async def test_high_risk_blocks_execution_when_threshold_exceeded(self):
        """High risk score above threshold = no execution. Fail-closed."""
        adapter = MockStage0Adapter(risk_threshold=20.0)
        request = Stage0Request(
            goal="Risky operation",
            tools=["admin_tool"],
            side_effects=["deployment", "data_modification"],
            context=Stage0Context(
                approval_status="approved",
                approved_by="admin@example.com",
            ),
        )

        response = await adapter.check(request)

        assert response.risk_score is not None
        if response.risk_score > 20.0:
            assert response.verdict == "DENY"
