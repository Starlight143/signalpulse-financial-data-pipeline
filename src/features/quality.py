"""Data quality feature calculations."""

import uuid
from datetime import UTC, datetime

from src.config import get_settings
from src.features.calculator import FeatureCalculator
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot

settings = get_settings()


class QualityFeatureCalculator(FeatureCalculator):
    def __init__(
        self,
        max_age_seconds: int | None = None,
        min_data_points: int | None = None,
    ):
        self.max_age_seconds = max_age_seconds or settings.feature_max_age_seconds
        self.min_data_points = min_data_points or settings.feature_min_data_points

    def get_signal_types(self) -> list[str]:
        return ["data_freshness", "data_quality_score", "data_completeness"]

    def calculate(
        self,
        snapshots: list[NormalizedMarketSnapshot],
        workspace_id: uuid.UUID,
    ) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []

        if not snapshots:
            return signals

        symbol = snapshots[0].symbol
        now = datetime.now(UTC)

        freshness_signal = self._calculate_freshness(
            workspace_id=workspace_id,
            symbol=symbol,
            snapshots=snapshots,
            now=now,
        )
        if freshness_signal:
            signals.append(freshness_signal)

        quality_signal = self._calculate_quality_score(
            workspace_id=workspace_id,
            symbol=symbol,
            snapshots=snapshots,
            now=now,
        )
        if quality_signal:
            signals.append(quality_signal)

        completeness_signal = self._calculate_completeness(
            workspace_id=workspace_id,
            symbol=symbol,
            snapshots=snapshots,
        )
        if completeness_signal:
            signals.append(completeness_signal)

        return signals

    def _calculate_freshness(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
        now: datetime,
    ) -> DerivedSignal | None:
        if not snapshots:
            return None

        latest_timestamp = max(s.event_timestamp for s in snapshots)
        # Normalise naive timestamps (e.g. from SQLite) to UTC.
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=UTC)
        age_seconds = (now - latest_timestamp).total_seconds()

        is_fresh = age_seconds <= self.max_age_seconds

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="data_freshness",
            event_timestamp=now,
            value=age_seconds,
            signal_metadata={
                "latest_event_timestamp": latest_timestamp.isoformat(),
                "max_age_seconds": self.max_age_seconds,
                "is_fresh": is_fresh,
            },
            is_anomaly=not is_fresh,
            data_freshness_seconds=age_seconds,
        )

    def _calculate_quality_score(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
        now: datetime,
    ) -> DerivedSignal | None:
        if not snapshots:
            return None

        total_fields = 0
        filled_fields = 0

        for snapshot in snapshots:
            fields = [
                snapshot.open_price,
                snapshot.high_price,
                snapshot.low_price,
                snapshot.close_price,
                snapshot.volume,
                snapshot.funding_rate,
                snapshot.mark_price,
            ]
            total_fields += len(fields)
            filled_fields += sum(1 for f in fields if f is not None)

        completeness_ratio = filled_fields / total_fields if total_fields > 0 else 0.0

        latest_timestamp = max(s.event_timestamp for s in snapshots)
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=UTC)
        age_seconds = (now - latest_timestamp).total_seconds()
        freshness_score = max(0.0, 1.0 - (age_seconds / self.max_age_seconds))

        coverage_score = min(1.0, len(snapshots) / self.min_data_points)

        quality_score = completeness_ratio * 0.4 + freshness_score * 0.3 + coverage_score * 0.3

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="data_quality_score",
            event_timestamp=now,
            value=quality_score,
            signal_metadata={
                "completeness_ratio": completeness_ratio,
                "freshness_score": freshness_score,
                "coverage_score": coverage_score,
                "snapshot_count": len(snapshots),
            },
            quality_score=quality_score,
        )

    def _calculate_completeness(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
    ) -> DerivedSignal | None:
        if not snapshots:
            return None

        ohlcv_count = sum(1 for s in snapshots if s.snapshot_type == "ohlcv")
        funding_count = sum(1 for s in snapshots if s.snapshot_type == "funding_rate")

        expected_types = 2
        actual_types = sum(1 for count in [ohlcv_count, funding_count] if count > 0)
        type_completeness = actual_types / expected_types

        total_fields = 0
        filled_fields = 0
        for snapshot in snapshots:
            fields = [
                snapshot.open_price,
                snapshot.high_price,
                snapshot.low_price,
                snapshot.close_price,
                snapshot.volume,
                snapshot.funding_rate,
            ]
            total_fields += len(fields)
            filled_fields += sum(1 for f in fields if f is not None)

        field_completeness = filled_fields / total_fields if total_fields > 0 else 0.0

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="data_completeness",
            event_timestamp=datetime.now(UTC),
            value=field_completeness,
            signal_metadata={
                "type_completeness": type_completeness,
                "field_completeness": field_completeness,
                "ohlcv_count": ohlcv_count,
                "funding_count": funding_count,
                "total_snapshots": len(snapshots),
            },
            quality_score=field_completeness,
        )
