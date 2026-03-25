"""Integration tests for market API endpoints."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import DerivedSignalFactory, NormalizedMarketSnapshotFactory


class TestMarketAPI:
    @pytest.mark.asyncio
    async def test_get_snapshot_unsupported_symbol_returns_400(
        self,
        client: AsyncClient,
        session: AsyncSession,  # noqa: ARG002
    ):
        response = await client.get("/market/UNKNOWNSYMBOL/snapshot")

        assert response.status_code == 400
        assert "not in allowed list" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_snapshot_returns_data(
        self,
        client: AsyncClient,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ):
        snapshot = NormalizedMarketSnapshotFactory.create(
            workspace_id=workspace_id,
            symbol="BTCUSDT",
            snapshot_type="ohlcv",
            close_price=50000.0,
        )
        session.add(snapshot)
        await session.commit()

        response = await client.get("/market/BTCUSDT/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_features(
        self,
        client: AsyncClient,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ):
        signal = DerivedSignalFactory.create(
            workspace_id=workspace_id,
            symbol="BTCUSDT",
            signal_type="funding_diff",
            value=0.0001,
        )
        session.add(signal)
        await session.commit()

        response = await client.get("/market/BTCUSDT/features")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_signals(
        self,
        client: AsyncClient,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ):
        signal = DerivedSignalFactory.create(
            workspace_id=workspace_id,
            symbol="ETHUSDT",
            signal_type="volatility_proxy",
            value=0.05,
        )
        session.add(signal)
        await session.commit()

        response = await client.get("/market/ETHUSDT/signals")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ETHUSDT"
        assert len(data["signals"]) >= 1
