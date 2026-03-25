"""Normalized market snapshot model for unified data schema."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.database_types import GUID


class NormalizedMarketSnapshot(Base):
    __tablename__ = "normalized_market_snapshots"

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
    raw_event_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    funding_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    mark_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_funding_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "symbol",
            "snapshot_type",
            "event_timestamp",
            "exchange",
            name="uq_normalized_snapshot",
        ),
        Index(
            "ix_normalized_market_snapshots_lookup",
            "workspace_id",
            "symbol",
            "snapshot_type",
            "event_timestamp",
        ),
    )
