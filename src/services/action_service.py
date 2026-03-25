"""Action service for handling side effects."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.alert_delivery import AlertDelivery
from src.schemas.action import AlertDispatchRequest

settings = get_settings()
logger = structlog.get_logger()


class ActionService:
    def __init__(
        self,
        session: AsyncSession,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.session = session
        # Shared client enables TCP connection reuse; falls back to per-request client when None.
        self._http_client = http_client

    async def dispatch_alert(
        self,
        workspace_id: uuid.UUID,
        request: AlertDispatchRequest,
        stage0_decision_id: uuid.UUID,
        stage0_request_id: str,
        stage0_verdict: str,
    ) -> AlertDelivery:
        alert = AlertDelivery(
            workspace_id=workspace_id,
            idempotency_key=request.idempotency_key,
            alert_type=request.alert_type,
            symbol=request.symbol.upper() if request.symbol else None,
            status="pending",
            destination=request.destination,
            payload=request.payload,
            stage0_decision_id=stage0_decision_id,
            stage0_request_id=stage0_request_id,
            stage0_verdict=stage0_verdict,
        )
        self.session.add(alert)
        await self.session.flush()

        delivery_success = await self._deliver_webhook(
            destination=request.destination,
            payload=request.payload,
        )

        if delivery_success:
            alert.status = "sent"
            alert.delivered_at = datetime.now(UTC)
        else:
            alert.status = "failed"
            alert.error_message = "Webhook delivery failed after all retry attempts"

        await self.session.flush()

        logger.info(
            "alert_dispatched",
            alert_id=str(alert.id),
            status=alert.status,
            destination=request.destination,
        )

        return alert

    async def _attempt_delivery(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: dict[str, Any],
    ) -> bool:
        """Execute a single webhook delivery attempt. Returns True on success, False on 4xx."""
        response = await client.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        if 400 <= response.status_code < 500:
            # 4xx errors are caller faults — retrying will not help.
            logger.warning(
                "webhook_delivery_client_error",
                status_code=response.status_code,
                url=url,
            )
            return False
        return response.status_code < 400

    async def _deliver_webhook(
        self,
        destination: str,
        payload: dict[str, Any],
    ) -> bool:
        if settings.alert_webhook_url:
            # Relay mode: route through a configured relay/proxy endpoint.
            # The relay is responsible for forwarding to the final destination.
            url = settings.alert_webhook_url
            body: dict[str, Any] = {
                "destination": destination,
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            # Direct mode: POST the payload straight to the destination URL.
            url = destination
            body = payload

        last_error: Exception | None = None

        for attempt in range(1, settings.alert_retry_max_attempts + 1):
            try:
                if self._http_client is not None:
                    result = await self._attempt_delivery(self._http_client, url, body)
                else:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        result = await self._attempt_delivery(client, url, body)

                if result:
                    if attempt > 1:
                        logger.info(
                            "webhook_delivery_succeeded_on_retry",
                            attempt=attempt,
                            destination=destination,
                        )
                    return True

                # Non-retryable 4xx response — do not retry.
                return False

            except Exception as e:
                last_error = e
                logger.warning(
                    "webhook_delivery_attempt_failed",
                    attempt=attempt,
                    max_attempts=settings.alert_retry_max_attempts,
                    error=str(e),
                    destination=destination,
                )
                if attempt < settings.alert_retry_max_attempts:
                    await asyncio.sleep(settings.alert_retry_backoff_seconds)

        logger.error(
            "webhook_delivery_exhausted",
            max_attempts=settings.alert_retry_max_attempts,
            error=str(last_error),
            destination=destination,
        )
        return False
