"""Test configuration and fixtures."""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.database import Base
from src.dependencies import get_session
from src.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_INTERNAL_API_KEY = "test-internal-api-key"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    test_settings = Settings(
        internal_api_key=TEST_INTERNAL_API_KEY,
        stage0_mock_mode=True,
        supported_symbols="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT",
    )

    async def override_get_session():
        yield session

    with (
        patch("src.api.actions.settings", test_settings),
        patch("src.api.market.settings", test_settings),
        patch("src.api.ingest.settings", test_settings),
        patch("src.api.health.settings", test_settings),
    ):
        app.dependency_overrides[get_session] = override_get_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client

        app.dependency_overrides.clear()


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def internal_api_key() -> str:
    return TEST_INTERNAL_API_KEY
