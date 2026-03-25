"""Database initialization script."""

import asyncio
import uuid

from sqlalchemy.exc import IntegrityError

from src.config import get_settings
from src.database import async_session_factory, init_db
from src.models.data_source import DataSource
from src.models.workspace import Workspace

settings = get_settings()

DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def main() -> None:
    print("Initializing database...")
    await init_db()
    print("Database schema created.")

    async with async_session_factory() as session:
        # Guard against duplicate runs — skip if the default workspace already exists.
        existing_workspace = await session.get(Workspace, DEFAULT_WORKSPACE_ID)
        if existing_workspace:
            print("Default workspace already exists — skipping seed.")
            return

        workspace = Workspace(
            id=DEFAULT_WORKSPACE_ID,
            name="Default Workspace",
            slug="default",
            is_active=True,
        )
        session.add(workspace)
        await session.flush()

        data_sources = [
            DataSource(
                workspace_id=workspace.id,
                name="Binance Funding Rate",
                source_type="funding_rate",
                exchange="binance",
                is_active=True,
            ),
            DataSource(
                workspace_id=workspace.id,
                name="Bybit Funding Rate",
                source_type="funding_rate",
                exchange="bybit",
                is_active=True,
            ),
            DataSource(
                workspace_id=workspace.id,
                name="Binance OHLCV",
                source_type="ohlcv",
                exchange="binance",
                is_active=True,
            ),
            DataSource(
                workspace_id=workspace.id,
                name="Bybit OHLCV",
                source_type="ohlcv",
                exchange="bybit",
                is_active=True,
            ),
        ]
        session.add_all(data_sources)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("Default workspace already exists (concurrent init) — skipping.")
            return

    print("Default workspace and data sources created.")
    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(main())
