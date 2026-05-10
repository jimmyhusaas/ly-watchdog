"""Tests for activity report scraper and API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from scrapers.activity_reports import _activity_uid, _load_fixture, _parse_date, run
from scrapers.upsert import upsert_activity_report

# -- unit: helpers -------------------------------------------------------------


def test_activity_uid() -> None:
    uid = _activity_uid("00015", "2012-03-19")
    assert uid == "00015_2012-03-19"


def test_parse_date_valid() -> None:
    dt = _parse_date("2012-03-19T00:00:00+08:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2012
    assert dt.month == 3
    assert dt.day == 18  # UTC: +08:00 midnight = previous day 16:00 UTC


def test_parse_date_null() -> None:
    assert _parse_date(None) is None
    assert _parse_date("null") is None
    assert _parse_date("") is None


def test_fixture_loads() -> None:
    rows = _load_fixture()
    assert rows is not None
    assert len(rows) == 5
    assert all(r.get("data") for r in rows)
    assert all(r.get("lgno") for r in rows)


# -- integration: upsert -------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    published = datetime(2012, 3, 19, tzinfo=UTC)
    result = await upsert_activity_report(
        db_session,
        uid="test_activity_insert_001",
        term=8,
        session_period=1,
        lgno="00015",
        legislator_name="",
        subject="測試問政週報",
        content="本週問政內容",
        published_at=published,
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_activity_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    published = datetime(2012, 3, 19, tzinfo=UTC)
    kwargs = {
        "uid": "test_activity_unchanged_001",
        "term": 8,
        "session_period": 1,
        "lgno": "00015",
        "legislator_name": "",
        "subject": "測試問政週報乙",
        "content": "本週問政內容乙",
        "published_at": published,
        "valid_from": now,
        "raw": {},
        "now": now,
    }
    await upsert_activity_report(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_activity_report(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_activity_upsert_correction(db_session) -> None:
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    published = datetime(2012, 3, 19, tzinfo=UTC)
    base = {
        "uid": "test_activity_correction_001",
        "term": 8,
        "session_period": 1,
        "lgno": "00028",
        "legislator_name": "",
        "subject": "測試問政週報丙",
        "published_at": published,
        "valid_from": t1,
        "raw": {},
    }
    await upsert_activity_report(db_session, content="原始內容", now=t1, **base)
    await db_session.flush()
    result = await upsert_activity_report(db_session, content="修正後內容", now=t2, **base)
    assert result == "updated"


# -- integration: full scraper run ---------------------------------------------


@pytest.mark.asyncio
async def test_full_activity_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 5
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_activity_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 5
    assert stats["errors"] == 0


# -- API: GET /v1/activity-reports --------------------------------------------


@pytest.mark.asyncio
async def test_activity_list_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/activity-reports?term=8")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_activity_lgno_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    import json
    from pathlib import Path

    fixture = json.loads((Path(__file__).parent / "fixtures" / "activity_reports.json").read_text())
    lgno = fixture["dataList"][0]["lgno"]
    resp = await client.get(f"/v1/activity-reports?term=8&lgno={lgno}")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1
    assert all(r["lgno"] == lgno for r in rows)
