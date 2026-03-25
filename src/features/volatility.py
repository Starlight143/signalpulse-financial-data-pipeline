"""Volatility feature calculations."""

import statistics
import uuid

from src.config import get_settings
from src.features.calculator import FeatureCalculator
from src.models.derived_signal import DerivedSignal
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot

settings = get_settings()


class VolatilityFeatureCalculator(FeatureCalculator):
    def __init__(
        self,
        window_size: int | None = None,
    ):
        self.window_size = window_size or settings.feature_rolling_window_medium

    def get_signal_types(self) -> list[str]:
        return ["volatility_proxy", "price_range_zscore", "volume_zscore"]

    def calculate(
        self,
        snapshots: list[NormalizedMarketSnapshot],
        workspace_id: uuid.UUID,
    ) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []

        ohlcv_snapshots = [
            s
            for s in snapshots
            if s.snapshot_type == "ohlcv"
            and s.high_price is not None
            and s.low_price is not None
            and s.close_price is not None
        ]

        if len(ohlcv_snapshots) < settings.feature_min_data_points:
            return signals

        ohlcv_snapshots.sort(key=lambda x: x.event_timestamp, reverse=True)
        symbol = ohlcv_snapshots[0].symbol

        vol_signal = self._calculate_volatility_proxy(
            workspace_id=workspace_id,
            symbol=symbol,
            snapshots=ohlcv_snapshots[: self.window_size],
        )
        if vol_signal:
            signals.append(vol_signal)

        range_signal = self._calculate_price_range_zscore(
            workspace_id=workspace_id,
            symbol=symbol,
            snapshots=ohlcv_snapshots[: self.window_size],
        )
        if range_signal:
            signals.append(range_signal)

        volume_snapshots = [s for s in ohlcv_snapshots if s.volume is not None]
        if len(volume_snapshots) >= settings.feature_min_data_points:
            vol_zscore_signal = self._calculate_volume_zscore(
                workspace_id=workspace_id,
                symbol=symbol,
                snapshots=volume_snapshots[: self.window_size],
            )
            if vol_zscore_signal:
                signals.append(vol_zscore_signal)

        return signals

    def _calculate_volatility_proxy(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
    ) -> DerivedSignal | None:
        if len(snapshots) < settings.feature_min_data_points:
            return None

        returns: list[float] = []
        for i in range(len(snapshots) - 1):
            curr_close = snapshots[i].close_price
            prev_close = snapshots[i + 1].close_price
            if curr_close is not None and prev_close is not None and prev_close != 0.0:
                ret = (curr_close - prev_close) / prev_close
                returns.append(ret)

        if not returns:
            return None

        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="volatility_proxy",
            event_timestamp=snapshots[0].event_timestamp,
            value=volatility,
            signal_metadata={
                "return_count": len(returns),
                "window_size": len(snapshots),
                "mean_return": statistics.mean(returns) if returns else 0.0,
            },
            quality_score=min(1.0, len(returns) / self.window_size),
            data_freshness_seconds=self._calculate_data_freshness(snapshots[0].event_timestamp),
            computation_window=len(snapshots),
        )

    def _calculate_price_range_zscore(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
    ) -> DerivedSignal | None:
        if len(snapshots) < settings.feature_min_data_points:
            return None

        ranges: list[float] = []
        for s in snapshots:
            if s.high_price and s.low_price:
                ranges.append(s.high_price - s.low_price)

        if len(ranges) < settings.feature_min_data_points:
            return None

        mean_range = statistics.mean(ranges)
        stdev_range = statistics.stdev(ranges) if len(ranges) > 1 else 0.0

        if stdev_range == 0:
            return None

        zscore = (ranges[0] - mean_range) / stdev_range
        is_anomaly = abs(zscore) > settings.feature_zscore_threshold

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="price_range_zscore",
            event_timestamp=snapshots[0].event_timestamp,
            value=zscore,
            signal_metadata={
                "current_range": ranges[0],
                "mean_range": mean_range,
                "stdev_range": stdev_range,
            },
            is_anomaly=is_anomaly,
            data_freshness_seconds=self._calculate_data_freshness(snapshots[0].event_timestamp),
            computation_window=len(ranges),
        )

    def _calculate_volume_zscore(
        self,
        workspace_id: uuid.UUID,
        symbol: str,
        snapshots: list[NormalizedMarketSnapshot],
    ) -> DerivedSignal | None:
        volumes = [s.volume for s in snapshots if s.volume is not None]

        if len(volumes) < settings.feature_min_data_points:
            return None

        mean_vol = statistics.mean(volumes)
        stdev_vol = statistics.stdev(volumes) if len(volumes) > 1 else 0.0

        if stdev_vol == 0:
            return None

        zscore = (volumes[0] - mean_vol) / stdev_vol
        is_anomaly = abs(zscore) > settings.feature_zscore_threshold

        return DerivedSignal(
            workspace_id=workspace_id,
            symbol=symbol,
            signal_type="volume_zscore",
            event_timestamp=snapshots[0].event_timestamp,
            value=zscore,
            signal_metadata={
                "current_volume": volumes[0],
                "mean_volume": mean_vol,
                "stdev_volume": stdev_vol,
            },
            is_anomaly=is_anomaly,
            data_freshness_seconds=self._calculate_data_freshness(snapshots[0].event_timestamp),
            computation_window=len(volumes),
        )
