"""Execution intent model for tracking action requests."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID, JSONDict


class ExecutionIntent(Base):
    __tablename__ = "execution_intents"

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
    idempotency_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    intent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
    )
    stage0_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID,
        nullable=True,
        index=True,
    )
    stage0_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage0_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    execution_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONDict,
        nullable=True,
    )
    execution_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Idempotency keys must be unique per workspace, not globally.
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_execution_intents_workspace_key",
        ),
        Index(
            "ix_execution_intents_lookup",
            "workspace_id",
            "intent_type",
            "status",
            "created_at",
        ),
    )
