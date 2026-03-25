"""Action API endpoints for side effects requiring Stage0 authorization."""

import hmac
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_session
from src.dependencies import get_http_client
from src.models.execution_intent import ExecutionIntent
from src.models.stage0_decision_log import Stage0DecisionLog
from src.schemas.action import (
    ActionResponse,
    AlertDispatchRequest,
    ExecutionIntentCreate,
    ExecutionIntentResponse,
)
from src.schemas.stage0 import Stage0Context, Stage0Request, Stage0Response
from src.services.action_service import ActionService
from src.services.idempotency_service import IdempotencyService
from src.stage0 import build_context, get_stage0_adapter
from src.stage0.exceptions import Stage0AuthorizationError, Stage0DeferredError

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


def _get_default_workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


async def verify_internal_api_key(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> bool:
    if not x_internal_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key",
        )
    # Constant-time comparison prevents timing-based key enumeration.
    if not hmac.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key",
        )
    return True


async def _save_stage0_decision(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    stage0_request: Stage0Request,
    stage0_response: Stage0Response,
    action_type: str,
    context: Stage0Context,
) -> Stage0DecisionLog:
    """Persist a Stage0 decision to the audit log and return the saved record."""
    decision_log = Stage0DecisionLog(
        workspace_id=workspace_id,
        request_id=stage0_response.request_id,
        decision=stage0_response.decision,
        verdict=stage0_response.verdict,
        risk_score=stage0_response.risk_score,
        high_risk=stage0_response.high_risk,
        issues=[i.model_dump() for i in stage0_response.issues],
        clarifying_questions=stage0_response.clarifying_questions,
        guardrails=stage0_response.guardrails,
        policy_version=stage0_response.policy_version,
        goal=stage0_request.goal,
        tools=stage0_request.tools,
        side_effects=stage0_request.side_effects,
        constraints=stage0_request.constraints,
        context=context.model_dump(),
        raw_response=stage0_response.raw_response or stage0_response.model_dump(),
        action_type=action_type,
    )
    session.add(decision_log)
    await session.flush()
    return decision_log


@router.post("/dispatch-alert", response_model=ActionResponse)
async def dispatch_alert(
    request: AlertDispatchRequest,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    _: bool = Depends(verify_internal_api_key),
) -> ActionResponse:
    idempotency_service = IdempotencyService(session)
    action_service = ActionService(session, http_client)

    existing = await idempotency_service.check(
        workspace_id=workspace_id,
        key=request.idempotency_key,
        action_type="alert_dispatch",
    )

    if existing is not None:
        if existing.get("status") == "processing":
            raise HTTPException(
                status_code=409,
                detail="A request with this idempotency key is already being processed",
            )
        raw_id = existing.get("action_id")
        return ActionResponse(
            success=True,
            action_id=uuid.UUID(raw_id) if raw_id else None,
            status="already_processed",
            message="Alert already processed (idempotent)",
        )

    await idempotency_service.acquire(
        workspace_id=workspace_id,
        key=request.idempotency_key,
        action_type="alert_dispatch",
        request_payload=request.model_dump(),
    )

    try:
        context = request.context or build_context(
            actor_role="system",
            environment="production",
        )

        stage0_request = Stage0Request(
            goal=f"Dispatch {request.alert_type} alert to {request.destination}",
            tools=["webhook", "notification"],
            side_effects=["external notification"],
            constraints=[
                "destination must be valid",
                "payload must be complete",
            ],
            context=context,
        )

        stage0_adapter = get_stage0_adapter(http_client=http_client)

        # LiveStage0Adapter raises Stage0AuthorizationError on DENY and
        # Stage0DeferredError on DEFER instead of returning them as a response.
        # MockStage0Adapter always returns a Stage0Response without raising.
        # Both paths are handled below.
        try:
            stage0_response = await stage0_adapter.check(stage0_request)
        except Stage0AuthorizationError as exc:
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="alert_dispatch",
                response_payload={"status": "denied", "verdict": exc.verdict},
            )
            logger.warning(
                "alert_dispatch_denied",
                verdict=exc.verdict,
                issues=exc.issues,
                request_id=exc.request_id,
            )
            return ActionResponse(
                success=False,
                status="denied",
                stage0_request_id=exc.request_id,
                stage0_verdict=exc.verdict,
                message=f"Stage0 denied alert dispatch",
                errors=[{"code": "STAGE0_DENIED", "verdict": exc.verdict}],
            )
        except Stage0DeferredError as exc:
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="alert_dispatch",
                response_payload={"status": "deferred"},
            )
            logger.info(
                "alert_dispatch_deferred",
                request_id=exc.request_id,
                questions=exc.clarifying_questions,
            )
            return ActionResponse(
                success=False,
                status="deferred",
                stage0_request_id=exc.request_id,
                stage0_verdict="DEFER",
                message="Stage0 deferred: additional context required",
                errors=[{"code": "STAGE0_DEFERRED"}],
            )

        decision_log = await _save_stage0_decision(
            session=session,
            workspace_id=workspace_id,
            stage0_request=stage0_request,
            stage0_response=stage0_response,
            action_type="alert_dispatch",
            context=context,
        )

        # Mock adapter returns non-ALLOW verdicts as a response instead of raising.
        if stage0_response.verdict != "ALLOW":
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="alert_dispatch",
                response_payload={"status": "denied", "verdict": stage0_response.verdict},
            )
            return ActionResponse(
                success=False,
                status="denied",
                stage0_request_id=stage0_response.request_id,
                stage0_verdict=stage0_response.verdict,
                message=f"Stage0 denied alert dispatch",
                errors=[{"code": "STAGE0_DENIED", "verdict": stage0_response.verdict}],
            )

        alert = await action_service.dispatch_alert(
            workspace_id=workspace_id,
            request=request,
            stage0_decision_id=decision_log.id,
            stage0_request_id=stage0_response.request_id,
            stage0_verdict=stage0_response.verdict,
        )

        if alert.status == "failed":
            decision_log.action_id = alert.id
            decision_log.execution_result = "Alert delivery failed"
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="alert_dispatch",
                response_payload={"status": "failed", "action_id": str(alert.id)},
            )
            logger.warning(
                "alert_delivery_failed",
                alert_id=str(alert.id),
                stage0_request_id=stage0_response.request_id,
                workspace_id=str(workspace_id),
            )
            return ActionResponse(
                success=False,
                action_id=alert.id,
                status="failed",
                stage0_request_id=stage0_response.request_id,
                stage0_verdict=stage0_response.verdict,
                message="Alert delivery failed",
                errors=[{"code": "DELIVERY_FAILED", "message": "Webhook delivery failed after all retry attempts"}],
            )

        decision_log.was_executed = True
        decision_log.action_id = alert.id
        decision_log.execution_result = "Alert dispatched successfully"

        await idempotency_service.complete(
            workspace_id=workspace_id,
            key=request.idempotency_key,
            action_type="alert_dispatch",
            response_payload={
                "status": "success",
                "action_id": str(alert.id),
                "stage0_request_id": stage0_response.request_id,
            },
        )

        logger.info(
            "alert_dispatched",
            alert_id=str(alert.id),
            stage0_request_id=stage0_response.request_id,
            workspace_id=str(workspace_id),
        )

        return ActionResponse(
            success=True,
            action_id=alert.id,
            status="sent",
            stage0_request_id=stage0_response.request_id,
            stage0_verdict=stage0_response.verdict,
            message="Alert dispatched successfully",
        )

    except Exception as e:
        logger.error("alert_dispatch_failed", error=str(e), exc_info=True)
        # Release the processing lock so the caller can retry with the same key.
        try:
            await idempotency_service.fail(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="alert_dispatch",
            )
        except Exception:
            logger.warning(
                "idempotency_fail_cleanup_error",
                key=request.idempotency_key,
                action_type="alert_dispatch",
            )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/create-execution-intent", response_model=ExecutionIntentResponse)
async def create_execution_intent(
    request: ExecutionIntentCreate,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    _: bool = Depends(verify_internal_api_key),
) -> ExecutionIntentResponse:
    idempotency_service = IdempotencyService(session)

    existing = await idempotency_service.check(
        workspace_id=workspace_id,
        key=request.idempotency_key,
        action_type="execution_intent",
    )

    if existing is not None:
        if existing.get("status") == "processing":
            raise HTTPException(
                status_code=409,
                detail="A request with this idempotency key is already being processed",
            )
        intent_id = existing.get("intent_id")
        if intent_id:
            existing_intent = await session.get(ExecutionIntent, uuid.UUID(intent_id))
            if existing_intent:
                return ExecutionIntentResponse.model_validate(existing_intent)
        # Idempotency key is completed but the record is gone — caller must retry
        # with a new key; re-using this key would violate the unique constraint.
        raise HTTPException(
            status_code=404,
            detail="Execution intent for this idempotency key no longer exists",
        )

    if request.symbol and request.symbol.upper() not in settings.supported_symbols_list:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{request.symbol}' not in allowed list",
        )

    await idempotency_service.acquire(
        workspace_id=workspace_id,
        key=request.idempotency_key,
        action_type="execution_intent",
        request_payload=request.model_dump(),
    )

    try:
        context = request.context or build_context(
            actor_role=request.actor_role,
            approval_status=request.approval_status,
            approved_by=request.approved_by,
            approved_at=request.approved_at,
            approval_reason=request.approval_reason,
            environment=request.environment,
        )

        stage0_request = Stage0Request(
            goal=f"Create execution intent: {request.intent_type}",
            tools=["execution_intent_store"],
            side_effects=["execution intent creation"],
            constraints=[
                "human approval required for trading intents",
                "symbol must be in allowlist",
                "payload must be validated",
            ],
            context=context,
        )

        stage0_adapter = get_stage0_adapter(http_client=http_client)

        try:
            stage0_response = await stage0_adapter.check(stage0_request)
        except Stage0AuthorizationError as exc:
            intent = ExecutionIntent(
                workspace_id=workspace_id,
                idempotency_key=request.idempotency_key,
                intent_type=request.intent_type,
                symbol=request.symbol.upper() if request.symbol else None,
                status="denied",
                payload=request.payload,
                stage0_request_id=exc.request_id,
                stage0_verdict=exc.verdict,
                actor_role=request.actor_role,
                approval_status=request.approval_status,
                approved_by=request.approved_by,
                approved_at=request.approved_at,
                rejection_reason=str(exc.issues),
            )
            session.add(intent)
            await session.flush()
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="execution_intent",
                response_payload={"status": "denied", "intent_id": str(intent.id)},
            )
            logger.warning(
                "execution_intent_denied",
                verdict=exc.verdict,
                issues=exc.issues,
                request_id=exc.request_id,
            )
            return ExecutionIntentResponse.model_validate(intent)
        except Stage0DeferredError as exc:
            intent = ExecutionIntent(
                workspace_id=workspace_id,
                idempotency_key=request.idempotency_key,
                intent_type=request.intent_type,
                symbol=request.symbol.upper() if request.symbol else None,
                status="deferred",
                payload=request.payload,
                stage0_request_id=exc.request_id,
                stage0_verdict="DEFER",
                actor_role=request.actor_role,
                approval_status=request.approval_status,
                approved_by=request.approved_by,
                approved_at=request.approved_at,
                rejection_reason=f"Deferred: {exc.clarifying_questions}",
            )
            session.add(intent)
            await session.flush()
            await idempotency_service.complete(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="execution_intent",
                response_payload={"status": "deferred", "intent_id": str(intent.id)},
            )
            return ExecutionIntentResponse.model_validate(intent)

        decision_log = await _save_stage0_decision(
            session=session,
            workspace_id=workspace_id,
            stage0_request=stage0_request,
            stage0_response=stage0_response,
            action_type="execution_intent",
            context=context,
        )

        status = "pending"
        if stage0_response.verdict == "DENY":
            status = "denied"
        elif stage0_response.verdict == "DEFER":
            status = "deferred"
        elif stage0_response.verdict == "ALLOW":
            status = "authorized"

        intent = ExecutionIntent(
            workspace_id=workspace_id,
            idempotency_key=request.idempotency_key,
            intent_type=request.intent_type,
            symbol=request.symbol.upper() if request.symbol else None,
            status=status,
            payload=request.payload,
            stage0_decision_id=decision_log.id,
            stage0_request_id=stage0_response.request_id,
            stage0_verdict=stage0_response.verdict,
            risk_score=stage0_response.risk_score,
            actor_role=request.actor_role,
            approval_status=request.approval_status,
            approved_by=request.approved_by,
            approved_at=request.approved_at,
            rejection_reason=None
            if stage0_response.verdict == "ALLOW"
            else str(stage0_response.issues),
        )
        session.add(intent)
        await session.flush()

        decision_log.action_id = intent.id
        decision_log.was_executed = stage0_response.verdict == "ALLOW"

        await idempotency_service.complete(
            workspace_id=workspace_id,
            key=request.idempotency_key,
            action_type="execution_intent",
            response_payload={
                "status": status,
                "intent_id": str(intent.id),
                "stage0_request_id": stage0_response.request_id,
            },
        )

        logger.info(
            "execution_intent_created",
            intent_id=str(intent.id),
            stage0_request_id=stage0_response.request_id,
            verdict=stage0_response.verdict,
            workspace_id=str(workspace_id),
        )

        return ExecutionIntentResponse.model_validate(intent)

    except Exception as e:
        logger.error("execution_intent_failed", error=str(e), exc_info=True)
        # Release the processing lock so the caller can retry with the same key.
        try:
            await idempotency_service.fail(
                workspace_id=workspace_id,
                key=request.idempotency_key,
                action_type="execution_intent",
            )
        except Exception:
            logger.warning(
                "idempotency_fail_cleanup_error",
                key=request.idempotency_key,
                action_type="execution_intent",
            )
        raise HTTPException(status_code=500, detail="Internal server error")
