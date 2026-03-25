"""Unit tests for Stage0 adapter."""

import pytest

from src.schemas.stage0 import Stage0Context, Stage0Request
from src.stage0.mock_adapter import MockStage0Adapter


class TestMockStage0Adapter:
    def test_adapter_initialization(self):
        adapter = MockStage0Adapter(default_verdict="DENY", risk_threshold=75.0)
        assert adapter.default_verdict == "DENY"
        assert adapter.risk_threshold == 75.0
        assert adapter.is_mock() is True

    @pytest.mark.asyncio
    async def test_check_returns_allow_with_approval(self):
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Test goal",
            tools=["test_tool"],
            side_effects=["notification"],
            context=Stage0Context(
                actor_role="admin",
                approval_status="approved",
                approved_by="user@example.com",
                approved_at="2024-01-01T00:00:00Z",
            ),
        )

        response = await adapter.check(request)

        assert response.verdict == "ALLOW"
        assert response.decision == "GO"

    @pytest.mark.asyncio
    async def test_check_returns_defer_without_approval(self):
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Test goal",
            tools=["test_tool"],
            side_effects=["notification"],
        )

        response = await adapter.check(request)

        assert response.verdict == "DEFER"
        assert response.decision == "DEFER"
        assert any(i.code == "CONTEXT_REQUIRED" for i in response.issues)

    @pytest.mark.asyncio
    async def test_check_returns_deny_with_invalid_approval_status(self):
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Test goal",
            tools=["test_tool"],
            side_effects=["notification"],
            context=Stage0Context(
                approval_status="pending",
            ),
        )

        response = await adapter.check(request)

        assert response.verdict == "DENY"
        assert response.decision == "NO_GO"

    @pytest.mark.asyncio
    async def test_check_calculates_risk_score(self):
        adapter = MockStage0Adapter(risk_threshold=50.0)
        request = Stage0Request(
            goal="Deploy to production",
            tools=["deployment"],
            side_effects=["deployment", "payment"],
            context=Stage0Context(
                approval_status="approved",
                approved_by="admin@example.com",
                environment="production",
            ),
        )

        response = await adapter.check(request)

        assert response.risk_score is not None
        assert response.risk_score > 10.0

    @pytest.mark.asyncio
    async def test_check_generates_request_id(self):
        adapter = MockStage0Adapter()
        request = Stage0Request(
            goal="Test goal",
            context=Stage0Context(
                approval_status="approved",
                approved_by="admin@example.com",
            ),
        )

        response = await adapter.check(request)

        assert response.request_id is not None
        assert response.request_id.startswith("req_mock_")

    @pytest.mark.asyncio
    async def test_check_deterministic_request_id(self):
        adapter = MockStage0Adapter()
        request1 = Stage0Request(
            goal="Same goal",
            tools=["tool1"],
            side_effects=["effect1"],
            context=Stage0Context(
                approval_status="approved",
                approved_by="admin@example.com",
            ),
        )
        request2 = Stage0Request(
            goal="Same goal",
            tools=["tool1"],
            side_effects=["effect1"],
            context=Stage0Context(
                approval_status="approved",
                approved_by="admin@example.com",
            ),
        )

        response1 = await adapter.check(request1)
        response2 = await adapter.check(request2)

        assert response1.request_id == response2.request_id
