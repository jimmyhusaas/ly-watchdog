"""Pytest fixtures."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_sessionmaker
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _reset_engine() -> None:
    """Discard the cached engine so the next test gets a fresh one on the current loop."""
    import app.database as db_mod

    db_mod._engine = None
    db_mod._sessionmaker = None


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a session that rolls back after each test, then resets the engine."""
    _reset_engine()
    factory = get_sessionmaker()
    async with factory() as session:
        await session.begin()
        yield session
        await session.rollback()
    _reset_engine()


@pytest.fixture
async def clean_db() -> AsyncIterator[None]:
    """Truncate legislators table before a full-pipeline test."""
    _reset_engine()
    factory = get_sessionmaker()
    async with factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM legislators"))
    _reset_engine()
    yield
    _reset_engine()
