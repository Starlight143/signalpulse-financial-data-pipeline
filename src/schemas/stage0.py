"""Stage0 API schemas matching the official contract."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.common import BaseSchema

VerdictType = Literal["ALLOW", "DENY", "DEFER"]
DecisionType = Literal["GO", "NO_GO", "DEFER", "ERROR"]


class Stage0Context(BaseModel):
    run_id: str | None = None
    current_iteration: int | None = None
    elapsed_seconds: float | None = None
    current_tool: str | None = None
    recent_tools: list[str] | None = None
    cumulative_cost_usd: float | None = None
    approval_status: str | None = None
    approved_by: str | None = None
    approved_at: datetime | str | None = None
    approval_reason: str | None = None
    actor_role: str | None = None
    user_role: str | None = None
    requester_role: str | None = None
    environment: str | None = None
    target_environment: str | None = None


class Stage0Request(BaseModel):
    goal: str = Field(..., min_length=1)
    tools: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    context: Stage0Context | None = None
    pro: bool = False


class Stage0Issue(BaseModel):
    code: str
    message: str | None = None


class Stage0CostEstimate(BaseModel):
    currency: str
    min: float
    max: float
    assumptions: list[str] = Field(default_factory=list)


class Stage0Meta(BaseModel):
    source: str
    test_mode: bool = False


class Stage0Response(BaseSchema):
    decision: DecisionType
    verdict: VerdictType
    risk_score: float | None = None
    high_risk: bool = False
    value_risk: float | None = None
    waste_risk: float | None = None
    issues: list[Stage0Issue] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    defer_questions: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    guardrail_checks: dict[str, Any] = Field(default_factory=dict)
    value_findings: list[str] | None = None
    request_id: str
    policy_version: str | None = None
    policy_pack_version: str | None = None
    timestamp: int | None = None
    evaluated_at: int | None = None
    decision_trace_summary: str | None = None
    cached: bool = False
    cost_estimate: Stage0CostEstimate | None = None
    meta: Stage0Meta | None = None
    raw_response: dict[str, Any] | None = None


class Stage0DecisionLogResponse(BaseSchema):
    id: str
    request_id: str
    decision: str
    verdict: str
    risk_score: float | None
    high_risk: bool
    issues: list[dict[str, Any]]
    goal: str
    tools: list[str]
    side_effects: list[str]
    constraints: list[str]
    context: dict[str, Any]
    policy_version: str | None
    was_executed: bool
    created_at: datetime
