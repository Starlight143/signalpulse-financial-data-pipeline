"""Stage0 context builder."""

import uuid
from datetime import UTC, datetime

from src.schemas.stage0 import Stage0Context


def build_context(
    run_id: str | None = None,
    current_iteration: int | None = None,
    elapsed_seconds: float | None = None,
    current_tool: str | None = None,
    recent_tools: list[str] | None = None,
    cumulative_cost_usd: float | None = None,
    approval_status: str | None = None,
    approved_by: str | None = None,
    approved_at: datetime | str | None = None,
    approval_reason: str | None = None,
    actor_role: str | None = None,
    user_role: str | None = None,
    requester_role: str | None = None,
    environment: str | None = None,
    target_environment: str | None = None,
) -> Stage0Context:
    return Stage0Context(
        run_id=run_id,
        current_iteration=current_iteration,
        elapsed_seconds=elapsed_seconds,
        current_tool=current_tool,
        recent_tools=recent_tools,
        cumulative_cost_usd=cumulative_cost_usd,
        approval_status=approval_status,
        approved_by=approved_by,
        approved_at=approved_at,
        approval_reason=approval_reason,
        actor_role=actor_role,
        user_role=user_role,
        requester_role=requester_role,
        environment=environment,
        target_environment=target_environment,
    )


def context_from_request(
    workspace_id: str,
    action_type: str,
    symbol: str | None = None,
    actor_role: str | None = None,
    approval_status: str | None = None,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    approval_reason: str | None = None,
    environment: str | None = None,
) -> Stage0Context:
    return build_context(
        run_id=f"run_{uuid.uuid4().hex[:16]}",
        current_iteration=1,
        elapsed_seconds=0.0,
        current_tool=action_type,
        recent_tools=[],
        cumulative_cost_usd=0.0,
        actor_role=actor_role,
        approval_status=approval_status,
        approved_by=approved_by,
        approved_at=approved_at or datetime.now(UTC),
        approval_reason=approval_reason,
        environment=environment,
    )
