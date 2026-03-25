"""Unit tests for idempotency service."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.models.idempotency_key import IdempotencyKey
from src.services.idempotency_service import IdempotencyService


class TestIdempotencyService:
    @pytest.mark.asyncio
    async def test_check_returns_none_for_new_key(self, session):
        service = IdempotencyService(session)
        workspace_id = uuid.uuid4()

        result = await service.check(
            workspace_id=workspace_id,
            key="new-key",
            action_type="test_action",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_acquire_creates_key(self, session):
        service = IdempotencyService(session)
        workspace_id = uuid.uuid4()

        key = await service.acquire(
            workspace_id=workspace_id,
            key="test-key",
            action_type="test_action",
            request_payload={"test": "data"},
        )

        assert key is not None
        assert key.key == "test-key"
        assert key.status == "processing"

    @pytest.mark.asyncio
    async def test_check_returns_processing_for_inflight(self, session):
        service = IdempotencyService(session)
        workspace_id = uuid.uuid4()

        await service.acquire(
            workspace_id=workspace_id,
            key="inflight-key",
            action_type="test_action",
            request_payload={},
        )

        result = await service.check(
            workspace_id=workspace_id,
            key="inflight-key",
            action_type="test_action",
        )

        assert result is not None
        assert result.get("status") == "processing"

    @pytest.mark.asyncio
    async def test_complete_updates_status(self, session):
        service = IdempotencyService(session)
        workspace_id = uuid.uuid4()

        await service.acquire(
            workspace_id=workspace_id,
            key="complete-key",
            action_type="test_action",
            request_payload={},
        )

        await service.complete(
            workspace_id=workspace_id,
            key="complete-key",
            response_payload={"result": "success"},
        )

        result = await service.check(
            workspace_id=workspace_id,
            key="complete-key",
            action_type="test_action",
        )

        assert result is not None
        assert result.get("result") == "success"

    @pytest.mark.asyncio
    async def test_check_returns_none_for_expired_key(self, session):
        service = IdempotencyService(session)
        workspace_id = uuid.uuid4()

        expired_key = IdempotencyKey(
            workspace_id=workspace_id,
            key="expired-key",
            action_type="test_action",
            status="completed",
            request_payload={},
            response_payload={"result": "old"},
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        session.add(expired_key)
        await session.commit()

        result = await service.check(
            workspace_id=workspace_id,
            key="expired-key",
            action_type="test_action",
        )

        assert result is None
