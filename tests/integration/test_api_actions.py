"""Integration tests for actions API endpoints."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestActionsAPI:
    @pytest.mark.asyncio
    async def test_dispatch_alert_without_auth_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/actions/dispatch-alert",
            json={
                "idempotency_key": "test-key-1",
                "alert_type": "test_alert",
                "destination": "https://example.com/webhook",
                "payload": {"message": "test"},
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_alert_with_auth_and_mock_stage0(
        self,
        client: AsyncClient,
        session: AsyncSession,  # noqa: ARG002
        workspace_id: uuid.UUID,  # noqa: ARG002
        internal_api_key: str,
    ):
        response = await client.post(
            "/actions/dispatch-alert",
            headers={"X-Internal-Key": internal_api_key},
            json={
                "idempotency_key": "test-key-with-approval",
                "alert_type": "test_alert",
                "destination": "https://example.com/webhook",
                "payload": {"message": "test"},
                "context": {
                    "actor_role": "admin",
                    "approval_status": "approved",
                    "approved_by": "admin@example.com",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stage0_verdict"] == "ALLOW"

    @pytest.mark.asyncio
    async def test_dispatch_alert_idempotency(
        self,
        client: AsyncClient,
        session: AsyncSession,  # noqa: ARG002
        workspace_id: uuid.UUID,  # noqa: ARG002
        internal_api_key: str,
    ):
        payload = {
            "idempotency_key": "idempotent-test-key",
            "alert_type": "test_alert",
            "destination": "https://example.com/webhook",
            "payload": {"message": "test"},
            "context": {
                "actor_role": "admin",
                "approval_status": "approved",
                "approved_by": "admin@example.com",
            },
        }

        response1 = await client.post(
            "/actions/dispatch-alert",
            headers={"X-Internal-Key": internal_api_key},
            json=payload,
        )

        response2 = await client.post(
            "/actions/dispatch-alert",
            headers={"X-Internal-Key": internal_api_key},
            json=payload,
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response2.json()["status"] == "already_processed"

    @pytest.mark.asyncio
    async def test_create_execution_intent_without_auth_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/actions/create-execution-intent",
            json={
                "idempotency_key": "test-intent-1",
                "intent_type": "test_intent",
                "payload": {},
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_execution_intent_denied_without_approval(
        self,
        client: AsyncClient,
        session: AsyncSession,  # noqa: ARG002
        workspace_id: uuid.UUID,  # noqa: ARG002
        internal_api_key: str,
    ):
        response = await client.post(
            "/actions/create-execution-intent",
            headers={"X-Internal-Key": internal_api_key},
            json={
                "idempotency_key": "test-intent-no-approval",
                "intent_type": "trade_execution",
                "symbol": "BTCUSDT",
                "payload": {"action": "buy", "amount": 1.0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["deferred", "denied"]

    @pytest.mark.asyncio
    async def test_create_execution_intent_with_approval(
        self,
        client: AsyncClient,
        session: AsyncSession,  # noqa: ARG002
        workspace_id: uuid.UUID,  # noqa: ARG002
        internal_api_key: str,
    ):
        response = await client.post(
            "/actions/create-execution-intent",
            headers={"X-Internal-Key": internal_api_key},
            json={
                "idempotency_key": "test-intent-with-approval",
                "intent_type": "trade_execution",
                "symbol": "BTCUSDT",
                "payload": {"action": "buy", "amount": 1.0},
                "actor_role": "trader",
                "approval_status": "approved",
                "approved_by": "manager@example.com",
                "environment": "staging",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "authorized"
        assert data["stage0_verdict"] == "ALLOW"
