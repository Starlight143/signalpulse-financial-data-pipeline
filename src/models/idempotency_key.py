"""Idempotency key model for deduplication."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID, JSONDict


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

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
    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
        index=True,
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONDict,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Include action_type so the same key string can be used independently
        # for different action types within the same workspace.
        Index(
            "uq_idempotency_keys_workspace_key_action",
            "workspace_id",
            "key",
            "action_type",
            unique=True,
        ),
    )
