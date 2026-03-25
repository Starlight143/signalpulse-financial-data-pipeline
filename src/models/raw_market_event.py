"""Raw market event model for storing original exchange data."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database_types import GUID, JSONDict

if TYPE_CHECKING:
    from src.models.data_source import DataSource


class RawMarketEvent(Base):
    __tablename__ = "raw_market_events"

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
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONDict,
        nullable=False,
    )
    ingestion_job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    data_source: Mapped["DataSource"] = relationship(
        "DataSource",
        back_populates="raw_events",
    )

    __table_args__ = (
        Index(
            "ix_raw_market_events_lookup",
            "workspace_id",
            "symbol",
            "event_type",
            "event_timestamp",
        ),
    )
