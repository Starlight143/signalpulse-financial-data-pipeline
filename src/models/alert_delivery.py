"""Alert delivery model for tracking notifications."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID, JSONDict


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

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
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
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
    delivery_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONDict,
        nullable=True,
    )
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
            name="uq_alert_deliveries_workspace_key",
        ),
        Index(
            "ix_alert_deliveries_lookup",
            "workspace_id",
            "alert_type",
            "status",
            "created_at",
        ),
    )
