"""Pytest fixtures.

These tests use httpx.AsyncClient against the FastAPI app in-process. DB-backed
tests will be added in Week 1 Day 5-7 once the scraper pipeline lands.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
