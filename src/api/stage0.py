"""Stage0 decision log API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models.stage0_decision_log import Stage0DecisionLog
from src.schemas.stage0 import Stage0DecisionLogResponse

router = APIRouter()


def _get_default_workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/decisions/{request_id}", response_model=Stage0DecisionLogResponse)
async def get_stage0_decision(
    request_id: str,
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    session: AsyncSession = Depends(get_session),
) -> Stage0DecisionLogResponse:
    stmt = select(Stage0DecisionLog).where(
        and_(
            Stage0DecisionLog.workspace_id == workspace_id,
            Stage0DecisionLog.request_id == request_id,
        )
    )

    result = await session.execute(stmt)
    decision_log = result.scalar_one_or_none()

    if not decision_log:
        raise HTTPException(
            status_code=404,
            detail=f"Decision log not found: {request_id}",
        )

    return Stage0DecisionLogResponse(
        id=str(decision_log.id),
        request_id=decision_log.request_id,
        decision=decision_log.decision,
        verdict=decision_log.verdict,
        risk_score=decision_log.risk_score,
        high_risk=decision_log.high_risk,
        issues=decision_log.issues,
        goal=decision_log.goal,
        tools=decision_log.tools,
        side_effects=decision_log.side_effects,
        constraints=decision_log.constraints,
        context=decision_log.context,
        policy_version=decision_log.policy_version,
        was_executed=decision_log.was_executed,
        created_at=decision_log.created_at,
    )


@router.get("/decisions", response_model=list[Stage0DecisionLogResponse])
async def list_stage0_decisions(
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    verdict: str | None = None,
    hours: int = 24,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[Stage0DecisionLogResponse]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    conditions = [
        Stage0DecisionLog.workspace_id == workspace_id,
        Stage0DecisionLog.created_at >= cutoff,
    ]

    if verdict:
        conditions.append(Stage0DecisionLog.verdict == verdict.upper())

    stmt = (
        select(Stage0DecisionLog)
        .where(and_(*conditions))
        .order_by(desc(Stage0DecisionLog.created_at))
        .limit(limit)
    )

    result = await session.execute(stmt)
    decision_logs = result.scalars().all()

    return [
        Stage0DecisionLogResponse(
            id=str(dl.id),
            request_id=dl.request_id,
            decision=dl.decision,
            verdict=dl.verdict,
            risk_score=dl.risk_score,
            high_risk=dl.high_risk,
            issues=dl.issues,
            goal=dl.goal,
            tools=dl.tools,
            side_effects=dl.side_effects,
            constraints=dl.constraints,
            context=dl.context,
            policy_version=dl.policy_version,
            was_executed=dl.was_executed,
            created_at=dl.created_at,
        )
        for dl in decision_logs
    ]
