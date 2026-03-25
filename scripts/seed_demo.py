"""Seed demo data for testing and development."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import random

from src.database import async_session_factory
from src.models.normalized_market_snapshot import NormalizedMarketSnapshot
from src.models.derived_signal import DerivedSignal

DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


async def main() -> None:
    print("Seeding demo data...")

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)

        for symbol in SYMBOLS:
            for i in range(24):
                timestamp = now - timedelta(hours=i)
                base_price = (
                    42000.0 if symbol == "BTCUSDT" else 2200.0 if symbol == "ETHUSDT" else 100.0
                )
                price_variation = random.uniform(-0.05, 0.05)
                close_price = base_price * (1 + price_variation)

                ohlcv = NormalizedMarketSnapshot(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    raw_event_id=uuid.uuid4(),
                    symbol=symbol,
                    snapshot_type="ohlcv",
                    event_timestamp=timestamp,
                    open_price=close_price * 0.99,
                    high_price=close_price * 1.01,
                    low_price=close_price * 0.98,
                    close_price=close_price,
                    volume=random.uniform(1000, 5000),
                    exchange="binance",
                )
                session.add(ohlcv)

                funding = NormalizedMarketSnapshot(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    raw_event_id=uuid.uuid4(),
                    symbol=symbol,
                    snapshot_type="funding_rate",
                    event_timestamp=timestamp,
                    funding_rate=random.uniform(-0.001, 0.001),
                    exchange="binance",
                )
                session.add(funding)

            for signal_type in [
                "funding_diff",
                "funding_zscore",
                "volatility_proxy",
                "data_quality_score",
            ]:
                signal = DerivedSignal(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    symbol=symbol,
                    signal_type=signal_type,
                    event_timestamp=now,
                    value=random.uniform(-2.0, 2.0),
                    is_anomaly=random.random() > 0.9,
                    signal_metadata={"source": "demo_seed"},
                )
                session.add(signal)

        await session.commit()

    print("Demo data seeded successfully.")
    print(f"Created OHLCV and funding rate data for: {', '.join(SYMBOLS)}")


if __name__ == "__main__":
    asyncio.run(main())
