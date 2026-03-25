"""Data source model for tracking exchange connections."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database_types import GUID

if TYPE_CHECKING:
    from src.models.raw_market_event import RawMarketEvent
    from src.models.workspace import Workspace


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_fetch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetch_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    avg_latency_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
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

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="data_sources",
    )
    raw_events: Mapped[list["RawMarketEvent"]] = relationship(
        "RawMarketEvent",
        back_populates="data_source",
        cascade="all, delete-orphan",
    )


ExchangeType = Literal["binance", "bybit"]
SourceType = Literal["funding_rate", "ohlcv"]
