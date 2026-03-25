"""Test factories for creating test data."""

import uuid
from datetime import UTC, datetime
from typing import Any

from src.models.data_source import DataSource
from src.models.derived_signal import DerivedSignal
from src.models.execution_intent import ExecutionIntent
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot
from src.models.raw_market_event import RawMarketEvent
from src.models.stage0_decision_log import Stage0DecisionLog
from src.models.workspace import Workspace


class WorkspaceFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        name: str = "Test Workspace",
        slug: str = "test-workspace",
        is_active: bool = True,
    ) -> Workspace:
        return Workspace(
            id=id or uuid.uuid4(),
            name=name,
            slug=slug,
            is_active=is_active,
        )


class DataSourceFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        name: str = "Test Data Source",
        source_type: str = "funding_rate",
        exchange: str = "binance",
        is_active: bool = True,
    ) -> DataSource:
        return DataSource(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            name=name,
            source_type=source_type,
            exchange=exchange,
            is_active=is_active,
        )


class RawMarketEventFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        data_source_id: uuid.UUID | None = None,
        event_type: str = "funding_rate",
        symbol: str = "BTCUSDT",
        exchange: str = "binance",
        event_timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> RawMarketEvent:
        return RawMarketEvent(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            data_source_id=data_source_id or uuid.uuid4(),
            event_type=event_type,
            symbol=symbol,
            exchange=exchange,
            event_timestamp=event_timestamp or datetime.now(UTC),
            raw_payload=raw_payload or {},
        )


class NormalizedMarketSnapshotFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        raw_event_id: uuid.UUID | None = None,
        symbol: str = "BTCUSDT",
        snapshot_type: str = "ohlcv",
        event_timestamp: datetime | None = None,
        close_price: float = 50000.0,
        volume: float = 1000.0,
        funding_rate: float | None = None,
        exchange: str = "binance",
    ) -> NormalizedMarketSnapshot:
        return NormalizedMarketSnapshot(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            raw_event_id=raw_event_id or uuid.uuid4(),
            symbol=symbol,
            snapshot_type=snapshot_type,
            event_timestamp=event_timestamp or datetime.now(UTC),
            close_price=close_price,
            volume=volume,
            funding_rate=funding_rate,
            exchange=exchange,
        )


class DerivedSignalFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        symbol: str = "BTCUSDT",
        signal_type: str = "funding_diff",
        event_timestamp: datetime | None = None,
        value: float = 0.0001,
        is_anomaly: bool = False,
    ) -> DerivedSignal:
        return DerivedSignal(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            symbol=symbol,
            signal_type=signal_type,
            event_timestamp=event_timestamp or datetime.now(UTC),
            value=value,
            is_anomaly=is_anomaly,
        )


class Stage0DecisionLogFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        request_id: str | None = None,
        decision: str = "GO",
        verdict: str = "ALLOW",
        goal: str = "Test goal",
        raw_response: dict[str, Any] | None = None,
    ) -> Stage0DecisionLog:
        return Stage0DecisionLog(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            request_id=request_id or f"req_{uuid.uuid4().hex[:16]}",
            decision=decision,
            verdict=verdict,
            goal=goal,
            raw_response=raw_response or {},
        )


class ExecutionIntentFactory:
    @staticmethod
    def create(
        id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        intent_type: str = "test_intent",
        status: str = "pending",
        payload: dict[str, Any] | None = None,
    ) -> ExecutionIntent:
        return ExecutionIntent(
            id=id or uuid.uuid4(),
            workspace_id=workspace_id or uuid.uuid4(),
            idempotency_key=idempotency_key or f"key_{uuid.uuid4().hex[:16]}",
            intent_type=intent_type,
            status=status,
            payload=payload or {},
        )
