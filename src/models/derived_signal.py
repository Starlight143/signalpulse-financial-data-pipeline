"""Derived signal model for feature engineering results."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID, JSONDict, JSONList


class DerivedSignal(Base):
    __tablename__ = "derived_signals"

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
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    signal_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
        default=dict,
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(default=False, nullable=False)
    data_freshness_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    computation_window: Mapped[int | None] = mapped_column(nullable=True)
    source_snapshot_ids: Mapped[list[str] | None] = mapped_column(
        JSONList,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_derived_signals_lookup",
            "workspace_id",
            "symbol",
            "signal_type",
            "event_timestamp",
        ),
    )
