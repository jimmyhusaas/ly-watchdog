"""Tests for committee membership scraper and API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from scrapers.committees import _committee_uid, _load_fixture, run
from scrapers.upsert import upsert_committee_membership

# -- unit: helpers -------------------------------------------------------------


def test_committee_uid() -> None:
    uid = _committee_uid(11, 1, "柯建銘", "司法及法制委員會")
    assert uid == "11_1_柯建銘_司法及法制委員會"


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 10
    names = {r["name"] for r in rows}
    assert len(names) > 1


# -- integration: upsert -------------------------------------------------------


@pytest.mark.asyncio
async def test_committee_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    result = await upsert_committee_membership(
        db_session,
        uid="test_committee_001",
        term=11,
        session_period=1,
        legislator_name="測試甲",
        committee="司法及法制委員會",
        is_convener=False,
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_committee_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    kwargs = {
        "uid": "test_committee_unchanged_001",
        "term": 11,
        "session_period": 1,
        "legislator_name": "測試乙",
        "committee": "內政委員會",
        "is_convener": False,
        "valid_from": now,
        "raw": {},
        "now": now,
    }
    await upsert_committee_membership(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_committee_membership(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_committee_upsert_convener_change(db_session) -> None:
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    base = {
        "uid": "test_committee_convener_001",
        "term": 11,
        "session_period": 1,
        "legislator_name": "測試丙",
        "committee": "財政委員會",
        "valid_from": t1,
        "raw": {},
    }
    await upsert_committee_membership(db_session, is_convener=False, now=t1, **base)
    await db_session.flush()
    result = await upsert_committee_membership(db_session, is_convener=True, now=t2, **base)
    assert result == "updated"


# -- integration: full scraper run ---------------------------------------------


@pytest.mark.asyncio
async def test_full_committee_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 10
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_committee_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 10
    assert stats["errors"] == 0


# -- API: GET /v1/committees ---------------------------------------------------


@pytest.mark.asyncio
async def test_committees_list_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/committees?term=11")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 10


@pytest.mark.asyncio
async def test_committees_filter_by_committee(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/committees?term=11&committee=外交")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    assert all("外交" in r["committee"] for r in rows)


@pytest.mark.asyncio
async def test_legislator_committees_endpoint(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    # pick a name from the fixture
    import json
    from pathlib import Path

    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "committees_term11_s1.json").read_text()
    )
    name = fixture["dataList"][0]["name"]
    resp = await client.get(f"/v1/legislators/{name}/committees?term=11")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    assert all(r["legislator_name"] == name for r in rows)
