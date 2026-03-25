"""Unit tests for data normalizer."""

import uuid

import pytest

from src.ingestion.binance import BinanceIngestor
from src.ingestion.bybit import BybitIngestor
from src.ingestion.normalizer import DataNormalizer


class TestDataNormalizer:
    def setup_method(self):
        self.normalizer = DataNormalizer()

    def test_get_ingestor_binance(self):
        ingestor = self.normalizer.get_ingestor("binance")
        assert isinstance(ingestor, BinanceIngestor)

    def test_get_ingestor_bybit(self):
        ingestor = self.normalizer.get_ingestor("bybit")
        assert isinstance(ingestor, BybitIngestor)

    def test_get_ingestor_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported exchange"):
            self.normalizer.get_ingestor("unknown_exchange")

    def test_normalize_binance_ohlcv(self):
        raw_data = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "open_time": 1704067200000,
            "open": "42000.00",
            "high": "42500.00",
            "low": "41800.00",
            "close": "42300.00",
            "volume": "1000.5",
            "quote_volume": "42150000.0",
        }

        normalized = self.normalizer.normalize(raw_data, "ohlcv", "binance")

        assert normalized["snapshot_type"] == "ohlcv"
        assert normalized["symbol"] == "BTCUSDT"
        assert normalized["exchange"] == "binance"
        assert normalized["open_price"] == 42000.0
        assert normalized["close_price"] == 42300.0
        assert normalized["volume"] == 1000.5

    def test_normalize_binance_funding_rate(self):
        raw_data = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "funding_rate": "0.0001",
            "funding_time": 1704067200000,
            "mark_price": "42000.00",
        }

        normalized = self.normalizer.normalize(raw_data, "funding_rate", "binance")

        assert normalized["snapshot_type"] == "funding_rate"
        assert normalized["symbol"] == "BTCUSDT"
        assert normalized["funding_rate"] == 0.0001
        assert normalized["mark_price"] == 42000.0

    def test_normalize_bybit_ohlcv(self):
        raw_data = {
            "exchange": "bybit",
            "symbol": "ETHUSDT",
            "interval": "60",
            "open_time": 1704067200000,
            "open": "2200.00",
            "high": "2250.00",
            "low": "2180.00",
            "close": "2230.00",
            "volume": "500.0",
            "turnover": "1115000.0",
        }

        normalized = self.normalizer.normalize(raw_data, "ohlcv", "bybit")

        assert normalized["snapshot_type"] == "ohlcv"
        assert normalized["symbol"] == "ETHUSDT"
        assert normalized["exchange"] == "bybit"
        assert normalized["open_price"] == 2200.0
        assert normalized["turnover"] == 1115000.0

    def test_create_raw_event(self):
        workspace_id = uuid.uuid4()
        data_source_id = uuid.uuid4()
        raw_data = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "funding_rate": "0.0001",
            "funding_time": 1704067200000,
        }

        event = self.normalizer.create_raw_event(
            workspace_id=workspace_id,
            data_source_id=data_source_id,
            raw_data=raw_data,
            data_type="funding_rate",
            symbol="BTCUSDT",
            exchange="binance",
            ingestion_job_id="test-job-123",
        )

        assert event["workspace_id"] == workspace_id
        assert event["data_source_id"] == data_source_id
        assert event["event_type"] == "funding_rate"
        assert event["symbol"] == "BTCUSDT"
        assert event["exchange"] == "binance"
        assert event["ingestion_job_id"] == "test-job-123"

    def test_normalize_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported data type"):
            self.normalizer.normalize({}, "unknown_type", "binance")
