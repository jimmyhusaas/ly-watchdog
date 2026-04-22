"""Pytest fixtures.

DB fixtures use NullPool (no connection reuse) so every test gets a fresh
asyncpg connection on the current event loop, avoiding "Future attached to a
different loop" errors when pytest-asyncio creates a new loop per test.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.main import app


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create a fresh engine + sessionmaker with NullPool for test isolation."""
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a session backed by NullPool that rolls back after each test."""
    factory = _make_session_factory()
    async with factory() as session:
        await session.begin()
        yield session
        await session.rollback()


@pytest.fixture
async def clean_db() -> AsyncIterator[None]:
    """Truncate legislators table and reset the app engine before a pipeline test.

    The scraper's run() uses the app-level cached engine. Resetting it here
    ensures it's recreated on the current event loop rather than a stale one.
    """
    import app.database as db_mod

    db_mod._engine = None
    db_mod._sessionmaker = None

    factory = _make_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM legislators"))
    yield
