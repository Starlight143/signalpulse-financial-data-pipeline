"""Action schemas for dispatch-alert and execution-intent."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.common import BaseSchema
from src.schemas.stage0 import Stage0Context

AlertStatus = Literal["pending", "sent", "failed", "denied"]
IntentStatus = Literal[
    "pending", "authorized", "executed", "completed", "failed", "denied", "deferred"
]


class AlertDispatchRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    alert_type: str = Field(..., min_length=1, max_length=100)
    symbol: str | None = Field(None, max_length=20)
    destination: str = Field(..., min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    context: Stage0Context | None = None


class ExecutionIntentCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    intent_type: str = Field(..., min_length=1, max_length=100)
    symbol: str | None = Field(None, max_length=20)
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_role: str | None = None
    approval_status: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_reason: str | None = None
    environment: str | None = None
    context: Stage0Context | None = None


class ExecutionIntentResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    idempotency_key: str
    intent_type: str
    symbol: str | None
    status: IntentStatus
    payload: dict[str, Any]
    stage0_request_id: str | None
    stage0_verdict: str | None
    risk_score: float | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class AlertDeliveryResponse(BaseSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    idempotency_key: str
    alert_type: str
    symbol: str | None
    status: AlertStatus
    destination: str
    stage0_request_id: str | None
    stage0_verdict: str | None
    delivered_at: datetime | None
    error_message: str | None
    created_at: datetime


class ActionResponse(BaseSchema):
    success: bool
    action_id: uuid.UUID | None = None
    status: str
    stage0_request_id: str | None = None
    stage0_verdict: str | None = None
    message: str | None = None
    errors: list[dict[str, Any]] | None = None
