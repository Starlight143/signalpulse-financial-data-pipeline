"""Feature calculator base class and orchestrator."""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import structlog

from src.config import get_settings
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot

logger = structlog.get_logger()

settings = get_settings()


class FeatureCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        snapshots: list[NormalizedMarketSnapshot],
        workspace_id: uuid.UUID,
    ) -> list[DerivedSignal]:
        pass

    @abstractmethod
    def get_signal_types(self) -> list[str]:
        pass

    def _get_timestamp(self) -> datetime:
        return datetime.now(UTC)

    def _calculate_data_freshness(
        self,
        event_timestamp: datetime,
    ) -> float:
        # Normalise naive timestamps to UTC to avoid TypeError on subtraction.
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=UTC)
        return (datetime.now(UTC) - event_timestamp).total_seconds()


class FeatureEngine:
    def __init__(self) -> None:
        from src.features.funding import FundingFeatureCalculator
        from src.features.quality import QualityFeatureCalculator
        from src.features.volatility import VolatilityFeatureCalculator

        self.calculators: list[FeatureCalculator] = [
            FundingFeatureCalculator(),
            VolatilityFeatureCalculator(),
            QualityFeatureCalculator(),
        ]

    def calculate_all(
        self,
        snapshots: list[NormalizedMarketSnapshot],
        workspace_id: uuid.UUID,
    ) -> list[DerivedSignal]:
        all_signals: list[DerivedSignal] = []

        for calculator in self.calculators:
            try:
                signals = calculator.calculate(snapshots, workspace_id)
                all_signals.extend(signals)
            except Exception as exc:
                logger.warning(
                    "feature_calculator_failed",
                    calculator=type(calculator).__name__,
                    error=str(exc),
                    exc_info=True,
                )

        return all_signals

    def get_all_signal_types(self) -> list[str]:
        types: list[str] = []
        for calculator in self.calculators:
            types.extend(calculator.get_signal_types())
        return types
