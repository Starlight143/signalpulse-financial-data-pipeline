"""Funding rate feature calculations."""

import statistics
import uuid
from datetime import datetime

from src.config import get_settings
from src.features.calculator import FeatureCalculator
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot

settings = get_settings()


class FundingFeatureCalculator(FeatureCalculator):
    def __init__(
        self,
        window_size: int | None = None,
        zscore_threshold: float | None = None,
    ):
        self.window_size = window_size or settings.feature_rolling_window_medium
        self.zscore_threshold = zscore_threshold or settings.feature_zscore_threshold

    def get_signal_types(self) -> list[str]:
        return ["funding_diff", "funding_zscore", "funding_mid_spread"]

    def calculate(
        self,
        snapshots: list[NormalizedMarketSnapshot],
        workspace_id: uuid.UUID,
    ) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []

        funding_snapshots = [
            s for s in snapshots if s.snapshot_type == "funding_rate" and s.funding_rate is not None
        ]

        if len(funding_snapshots) < 2:
            return signals

        funding_snapshots.sort(key=lambda x: x.event_timestamp, reverse=True)
        symbol = funding_snapshots[0].symbol

        funding_rates = [
            s.funding_rate
            for s in funding_snapshots[: self.window_size]
            if s.funding_rate is not None
        ]
        if len(funding_rates) >= 2:
            diff_signal = self._calculate_funding_diff(
                workspace_id=workspace_id,
                symbol=symbol,
                funding_rates=funding_rates,
                timestamps=[s.event_timestamp for s in funding_snapshots[: len(funding_rates)]],
            )
            if diff_signal:
                signals.append(diff_signal)

        if len(funding_rates) >= settings.feature_min_data_points:
            zscore_signal = self._calculate_funding_zscore(
                workspace_id=workspace_id,
                symbol=symbol,
                funding_rates=funding_rates,
                timestamp=funding_snapshots[0].event_timestamp,
            )
            if zscore_signal:
                signals.append(zscore_signal)

        ohlcv_snapshots = [
            s for s in snapshots if s.snapshot_type == "ohlcv" and s.close_price is not None
        ]
        if ohlcv_snapshots and funding_snapshots:
            spread_signal = self._calculate_funding_mid_spread(
                workspace_id=workspace_id,
                symbol=symbol,
                funding_snapshot=funding_snapshots[0],
                ohlcv_snapshot=ohlcv_snapshots[0],
            )
            if spread_signal:
                signals.append(spread_signal)

        return signals

    def _calculate_funding_diff(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        funding_rates: list[float],
        timestamps: list[datetime],
    ) -> DerivedSignal | None:
        if len(funding_rates) < 2:
            return None

        diff = funding_rates[0] - funding_rates[1]

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="funding_diff",
            event_timestamp=timestamps[0],
            value=diff,
            signal_metadata={
                "current_rate": funding_rates[0],
                "previous_rate": funding_rates[1],
                "window_size": len(funding_rates),
            },
            data_freshness_seconds=self._calculate_data_freshness(timestamps[0]),
            computation_window=len(funding_rates),
        )

    def _calculate_funding_zscore(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        funding_rates: list[float],
        timestamp: datetime,
    ) -> DerivedSignal | None:
        if len(funding_rates) < settings.feature_min_data_points:
            return None

        mean_val = statistics.mean(funding_rates)
        stdev_val = statistics.stdev(funding_rates) if len(funding_rates) > 1 else 0.0

        if stdev_val == 0:
            return None

        zscore = (funding_rates[0] - mean_val) / stdev_val
        is_anomaly = abs(zscore) > self.zscore_threshold

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="funding_zscore",
            event_timestamp=timestamp,
            value=zscore,
            signal_metadata={
                "mean": mean_val,
                "stdev": stdev_val,
                "current_rate": funding_rates[0],
            },
            is_anomaly=is_anomaly,
            data_freshness_seconds=self._calculate_data_freshness(timestamp),
            computation_window=len(funding_rates),
        )

    def _calculate_funding_mid_spread(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        funding_snapshot: NormalizedMarketSnapshot,
        ohlcv_snapshot: NormalizedMarketSnapshot,
    ) -> DerivedSignal | None:
        if funding_snapshot.funding_rate is None or ohlcv_snapshot.close_price is None:
            return None

        mark_price = funding_snapshot.mark_price or ohlcv_snapshot.close_price
        mid_spread = funding_snapshot.funding_rate * mark_price

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="funding_mid_spread",
            event_timestamp=funding_snapshot.event_timestamp,
            value=mid_spread,
            signal_metadata={
                "funding_rate": funding_snapshot.funding_rate,
                "mark_price": mark_price,
                "close_price": ohlcv_snapshot.close_price,
            },
            data_freshness_seconds=self._calculate_data_freshness(funding_snapshot.event_timestamp),
        )
