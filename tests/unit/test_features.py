"""Unit tests for feature calculators."""

import uuid
from datetime import UTC, datetime

import pytest

from src.features.funding import FundingFeatureCalculator
from src.features.quality import QualityFeatureCalculator
from src.features.volatility import VolatilityFeatureCalculator
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot


def create_funding_snapshot(
    funding_rate: float,
    mark_price: float | None = None,
    timestamp: datetime | None = None,
) -> NormalizedMarketSnapshot:
    return NormalizedMarketSnapshot(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        raw_event_id=uuid.uuid4(),
        symbol="BTCUSDT",
        snapshot_type="funding_rate",
        event_timestamp=timestamp or datetime.now(UTC),
        funding_rate=funding_rate,
        mark_price=mark_price,
        exchange="binance",
    )


def create_ohlcv_snapshot(
    close_price: float,
    high_price: float | None = None,
    low_price: float | None = None,
    volume: float | None = None,
    timestamp: datetime | None = None,
) -> NormalizedMarketSnapshot:
    return NormalizedMarketSnapshot(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        raw_event_id=uuid.uuid4(),
        symbol="BTCUSDT",
        snapshot_type="ohlcv",
        event_timestamp=timestamp or datetime.now(UTC),
        close_price=close_price,
        high_price=high_price or close_price * 1.01,
        low_price=low_price or close_price * 0.99,
        volume=volume or 1000.0,
        exchange="binance",
    )


class TestFundingFeatureCalculator:
    def setup_method(self):
        self.calculator = FundingFeatureCalculator(window_size=10, zscore_threshold=2.0)

    def test_get_signal_types(self):
        types = self.calculator.get_signal_types()
        assert "funding_diff" in types
        assert "funding_zscore" in types
        assert "funding_mid_spread" in types

    def test_calculate_funding_diff(self):
        workspace_id = uuid.uuid4()
        now = datetime.now(UTC)

        snapshots = [
            create_funding_snapshot(0.0001, 42000.0, now),
            create_funding_snapshot(0.0002, 42000.0, now),
        ]

        signals = self.calculator.calculate(snapshots, workspace_id)

        diff_signals = [s for s in signals if s.signal_type == "funding_diff"]
        assert len(diff_signals) == 1
        assert diff_signals[0].value == pytest.approx(-0.0001, rel=1e-6)

    def test_calculate_funding_zscore(self):
        workspace_id = uuid.uuid4()
        now = datetime.now(UTC)

        snapshots = [
            create_funding_snapshot(0.0010, 42000.0, now),
            create_funding_snapshot(0.0001, 42000.0, now),
            create_funding_snapshot(0.0001, 42000.0, now),
            create_funding_snapshot(0.0001, 42000.0, now),
            create_funding_snapshot(0.0001, 42000.0, now),
            create_funding_snapshot(0.0001, 42000.0, now),
        ]

        signals = self.calculator.calculate(snapshots, workspace_id)

        zscore_signals = [s for s in signals if s.signal_type == "funding_zscore"]
        assert len(zscore_signals) == 1
        assert zscore_signals[0].is_anomaly is True

    def test_insufficient_data_returns_empty(self):
        workspace_id = uuid.uuid4()

        snapshots = [create_funding_snapshot(0.0001, 42000.0)]

        signals = self.calculator.calculate(snapshots, workspace_id)

        assert len(signals) == 0


class TestVolatilityFeatureCalculator:
    def setup_method(self):
        self.calculator = VolatilityFeatureCalculator(window_size=10)

    def test_get_signal_types(self):
        types = self.calculator.get_signal_types()
        assert "volatility_proxy" in types
        assert "price_range_zscore" in types
        assert "volume_zscore" in types

    def test_calculate_volatility_proxy(self):
        workspace_id = uuid.uuid4()
        now = datetime.now(UTC)

        snapshots = [
            create_ohlcv_snapshot(42000.0, timestamp=now),
            create_ohlcv_snapshot(41500.0, timestamp=now),
            create_ohlcv_snapshot(41000.0, timestamp=now),
            create_ohlcv_snapshot(40500.0, timestamp=now),
            create_ohlcv_snapshot(40000.0, timestamp=now),
            create_ohlcv_snapshot(39500.0, timestamp=now),
        ]

        signals = self.calculator.calculate(snapshots, workspace_id)

        vol_signals = [s for s in signals if s.signal_type == "volatility_proxy"]
        assert len(vol_signals) == 1
        assert vol_signals[0].value > 0


class TestQualityFeatureCalculator:
    def setup_method(self):
        self.calculator = QualityFeatureCalculator(max_age_seconds=3600, min_data_points=5)

    def test_get_signal_types(self):
        types = self.calculator.get_signal_types()
        assert "data_freshness" in types
        assert "data_quality_score" in types
        assert "data_completeness" in types

    def test_calculate_data_freshness(self):
        workspace_id = uuid.uuid4()
        now = datetime.now(UTC)

        snapshots = [
            create_ohlcv_snapshot(42000.0, timestamp=now),
        ]

        signals = self.calculator.calculate(snapshots, workspace_id)

        freshness_signals = [s for s in signals if s.signal_type == "data_freshness"]
        assert len(freshness_signals) == 1
        assert freshness_signals[0].value < 60

    def test_calculate_quality_score(self):
        workspace_id = uuid.uuid4()
        now = datetime.now(UTC)

        snapshots = [
            create_ohlcv_snapshot(42000.0, timestamp=now),
            create_ohlcv_snapshot(41500.0, timestamp=now),
            create_ohlcv_snapshot(41000.0, timestamp=now),
            create_ohlcv_snapshot(40500.0, timestamp=now),
            create_ohlcv_snapshot(40000.0, timestamp=now),
        ]

        signals = self.calculator.calculate(snapshots, workspace_id)

        quality_signals = [s for s in signals if s.signal_type == "data_quality_score"]
        assert len(quality_signals) == 1
        assert 0.0 <= quality_signals[0].value <= 1.0
