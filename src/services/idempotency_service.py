"""Idempotency service for deduplication."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.idempotency_key import IdempotencyKey

settings = get_settings()
logger = structlog.get_logger()


class IdempotencyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ttl_seconds = settings.idempotency_key_ttl_seconds

    async def check(
        self,
        workspace_id: uuid.UUID,
        key: str,
        action_type: str,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC)

        stmt = select(IdempotencyKey).where(
            IdempotencyKey.workspace_id == workspace_id,
            IdempotencyKey.key == key,
            IdempotencyKey.action_type == action_type,
            IdempotencyKey.expires_at > now,
        )

        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status == "completed":
                logger.info(
                    "idempotency_key_found",
                    key=key,
                    action_type=action_type,
                    status="completed",
                )
                return existing.response_payload

            if existing.status == "processing":
                logger.warning(
                    "idempotency_key_processing",
                    key=key,
                    action_type=action_type,
                )
                return {"status": "processing", "message": "Request is being processed"}

        return None

    async def acquire(
        self,
        workspace_id: uuid.UUID,
        key: str,
        action_type: str,
        request_payload: dict[str, Any],
    ) -> IdempotencyKey:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.ttl_seconds)

        idempotency_key = IdempotencyKey(
            workspace_id=workspace_id,
            key=key,
            action_type=action_type,
            status="processing",
            request_payload=request_payload,
            expires_at=expires_at,
        )

        self.session.add(idempotency_key)
        await self.session.flush()

        logger.info(
            "idempotency_key_acquired",
            key=key,
            action_type=action_type,
            expires_at=expires_at.isoformat(),
        )

        return idempotency_key

    async def complete(
        self,
        workspace_id: uuid.UUID,
        key: str,
        action_type: str,
        response_payload: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC)

        stmt = select(IdempotencyKey).where(
            IdempotencyKey.workspace_id == workspace_id,
            IdempotencyKey.key == key,
            IdempotencyKey.action_type == action_type,
        )

        result = await self.session.execute(stmt)
        idempotency_key = result.scalar_one_or_none()

        if idempotency_key:
            idempotency_key.status = "completed"
            idempotency_key.response_payload = response_payload
            idempotency_key.completed_at = now

            logger.info(
                "idempotency_key_completed",
                key=key,
                action_type=action_type,
                status="completed",
            )

    async def fail(
        self,
        workspace_id: uuid.UUID,
        key: str,
        action_type: str,
    ) -> None:
        """Delete a stuck-in-processing idempotency key so the caller can retry with the same key.

        Called from outer exception handlers when an unexpected error prevents normal completion.
        Deleting (rather than marking failed) is intentional: it allows the client to retry
        the exact same idempotency key without waiting for TTL expiry.
        """
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.workspace_id == workspace_id,
            IdempotencyKey.key == key,
            IdempotencyKey.action_type == action_type,
        )

        result = await self.session.execute(stmt)
        idempotency_key = result.scalar_one_or_none()

        if idempotency_key:
            await self.session.delete(idempotency_key)
            await self.session.flush()
            logger.info(
                "idempotency_key_released_on_failure",
                key=key,
                action_type=action_type,
            )

    async def cleanup_expired(self) -> int:
        now = datetime.now(UTC)

        stmt = select(IdempotencyKey).where(
            IdempotencyKey.expires_at < now,
        )

        result = await self.session.execute(stmt)
        expired_keys = result.scalars().all()

        for key in expired_keys:
            self.session.delete(key)

        await self.session.flush()

        if expired_keys:
            logger.info("idempotency_cleanup", count=len(expired_keys))

        return len(expired_keys)
