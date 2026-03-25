"""Integration tests for health API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthAPI:
    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, client: AsyncClient):
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "signalpulse-financial-data-pipeline"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        response = await client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database_connected" in data
        assert "stage0_configured" in data
        assert "stage0_mode" in data
