"""Stage0 decision log model for audit trail."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID, JSONDict, JSONList


class Stage0DecisionLog(Base):
    __tablename__ = "stage0_decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        nullable=False,
        index=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_risk: Mapped[bool] = mapped_column(default=False, nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    clarifying_questions: Mapped[list[str]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    guardrails: Mapped[list[str]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    policy_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[list[str]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    side_effects: Mapped[list[str]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    constraints: Mapped[list[str]] = mapped_column(
        JSONList,
        nullable=False,
        default=list,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
        default=dict,
    )
    raw_response: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
    )
    action_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID,
        nullable=True,
    )
    was_executed: Mapped[bool] = mapped_column(default=False, nullable=False)
    execution_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_stage0_decision_logs_lookup",
            "workspace_id",
            "verdict",
            "created_at",
        ),
    )
