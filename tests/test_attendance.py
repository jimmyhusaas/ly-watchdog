"""Tests for attendance scraper pipeline and ranking API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.models.attendance import Attendance
from scrapers.attendance import _attendance_uid, _roc_to_date, _load_fixture, run
from scrapers.upsert import upsert_attendance


# ── unit: helpers ─────────────────────────────────────────────────────────────

def test_roc_to_date() -> None:
    d = _roc_to_date("113/02/19")
    assert d is not None
    assert d.year == 2024
    assert d.month == 2
    assert d.day == 19


def test_roc_to_date_invalid() -> None:
    assert _roc_to_date(None) is None
    assert _roc_to_date("") is None


def test_attendance_uid() -> None:
    uid = _attendance_uid(11, 1, "院會", 3, "柯建銘")
    assert uid == "11_1_院會_3_柯建銘"


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 20  # 5 legislators × 4 meetings
    names = {r["legislatorName"] for r in rows}
    assert "柯建銘" in names
    assert "韓國瑜" in names


# ── integration: upsert ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_attendance_upsert_insert(db_session) -> None:
    from datetime import date
    now = datetime(2024, 2, 19, tzinfo=UTC)
    result = await upsert_attendance(
        db_session,
        uid="test_att_insert_001",
        term=11,
        session_period=1,
        meeting_times=1,
        meeting_type="院會",
        meeting_name="第11屆第1會期第1次院會",
        meeting_date=date(2024, 2, 19),
        legislator_uid="11_測試甲",
        legislator_name="測試甲",
        attend_mark="出席",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_attendance_upsert_unchanged(db_session) -> None:
    from datetime import date
    now = datetime(2024, 2, 19, tzinfo=UTC)
    kwargs = dict(
        uid="test_att_unchanged_001",
        term=11, session_period=1, meeting_times=1,
        meeting_type="院會", meeting_name="第11屆第1會期第1次院會",
        meeting_date=date(2024, 2, 19),
        legislator_uid="11_測試乙", legislator_name="測試乙",
        attend_mark="出席", valid_from=now, raw={}, now=now,
    )
    await upsert_attendance(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_attendance(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_attendance_upsert_correction(db_session) -> None:
    from datetime import date
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    base = dict(
        uid="test_att_correction_001",
        term=11, session_period=1, meeting_times=1,
        meeting_type="院會", meeting_name="第11屆第1會期第1次院會",
        meeting_date=date(2024, 2, 19),
        legislator_uid="11_測試丙", legislator_name="測試丙",
        valid_from=t1, raw={},
    )
    await upsert_attendance(db_session, attend_mark="缺席", now=t1, **base)
    await db_session.flush()
    result = await upsert_attendance(db_session, attend_mark="請假", now=t2, **base)
    assert result == "updated"


# ── integration: full scraper run ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_attendance_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 20
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_attendance_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 20
    assert stats["errors"] == 0


# ── API: ranking ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ranking_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/attendance/ranking?term=11&session_period=1")
    assert resp.status_code == 200
    rows = resp.json()

    assert len(rows) == 5

    # Sorted by rate descending — 韓國瑜 4/4 = 100% should be first
    assert rows[0]["legislator_name"] == "韓國瑜"
    assert rows[0]["attended"] == 4
    assert rows[0]["total"] == 4
    assert rows[0]["rate"] == 100.0

    # 王世堅 1/4 = 25% should be last
    assert rows[-1]["legislator_name"] == "王世堅"
    assert rows[-1]["attended"] == 1
    assert rows[-1]["absent"] == 3
    assert rows[-1]["rate"] == 25.0


@pytest.mark.asyncio
async def test_ranking_meeting_type_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get(
        "/v1/attendance/ranking?term=11&session_period=1&meeting_type=院會"
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 5
    assert all(r["total"] == 4 for r in rows)
