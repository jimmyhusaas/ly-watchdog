"""Tests for interpellation scraper pipeline and interpellations API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from scrapers.interpellations import _interp_uid, _load_fixture, run
from scrapers.upsert import upsert_interpellation

# -- unit: helpers -------------------------------------------------------------


def test_interp_uid() -> None:
    uid = _interp_uid(11, 1, 1, "柯建銘")
    assert uid == "11_1_1_柯建銘"


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 10
    names = {r["legislatorName"] for r in rows}
    assert "柯建銘" in names
    assert "韓國瑜" in names
    assert "王世堅" in names


# -- integration: upsert -------------------------------------------------------


@pytest.mark.asyncio
async def test_interp_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    result = await upsert_interpellation(
        db_session,
        uid="test_interp_insert_001",
        term=11,
        session_period=1,
        meeting_times=1,
        legislator_name="測試甲",
        interp_content="質詢內容測試",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_interp_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    kwargs = {
        "uid": "test_interp_unchanged_001",
        "term": 11,
        "session_period": 1,
        "meeting_times": 1,
        "legislator_name": "測試乙",
        "interp_content": "質詢內容測試乙",
        "valid_from": now,
        "raw": {},
        "now": now,
    }
    await upsert_interpellation(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_interpellation(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_interp_upsert_correction(db_session) -> None:
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    base = {
        "uid": "test_interp_correction_001",
        "term": 11,
        "session_period": 1,
        "meeting_times": 1,
        "legislator_name": "測試丙",
        "valid_from": t1,
        "raw": {},
    }
    await upsert_interpellation(db_session, interp_content="原始質詢內容", now=t1, **base)
    await db_session.flush()
    result = await upsert_interpellation(
        db_session, interp_content="修正後質詢內容", now=t2, **base
    )
    assert result == "updated"


# -- integration: full scraper run ---------------------------------------------


@pytest.mark.asyncio
async def test_full_interp_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 10
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_interp_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 10
    assert stats["errors"] == 0


# -- API: GET /v1/interpellations ----------------------------------------------


@pytest.mark.asyncio
async def test_interps_list_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/interpellations?term=11")
    assert resp.status_code == 200
    assert len(resp.json()) == 10


@pytest.mark.asyncio
async def test_interps_legislator_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/interpellations?term=11&legislator_name=柯建銘")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 4
    assert all(r["legislator_name"] == "柯建銘" for r in rows)


@pytest.mark.asyncio
async def test_interps_keyword_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/interpellations?term=11&keyword=預算")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 4
    assert all("預算" in r["interp_content"] for r in rows)
