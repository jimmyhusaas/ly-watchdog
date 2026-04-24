"""Tests for vote scraper pipeline and votes API."""

from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient

from scrapers.upsert import upsert_vote
from scrapers.votes import _load_fixture, _roc_to_date, _vote_uid, run

# ── unit: helpers ──────────────────────────────────────────────────────────────


def test_roc_to_date() -> None:
    d = _roc_to_date("113/02/19")
    assert d is not None
    assert d.year == 2024
    assert d.month == 2
    assert d.day == 19


def test_roc_to_date_invalid() -> None:
    assert _roc_to_date(None) is None
    assert _roc_to_date("") is None


def test_vote_uid() -> None:
    uid = _vote_uid(11, 1, 1, 1, "柯建銘")
    assert uid == "11_1_1_1_柯建銘"


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 15  # 5 legislators x 3 vote sessions
    names = {r["legislatorName"] for r in rows}
    assert "柯建銘" in names
    assert "韓國瑜" in names
    assert "王世堅" in names


# ── integration: upsert ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vote_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    result = await upsert_vote(
        db_session,
        uid="test_vote_insert_001",
        term=11,
        session_period=1,
        meeting_times=1,
        vote_times=1,
        vote_date=date(2024, 2, 19),
        bill_no="政府提案第17851號",
        bill_name="測試議案",
        legislator_name="測試甲",
        party="測試黨",
        vote_result="贊成",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_vote_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    kwargs = {
        "uid": "test_vote_unchanged_001",
        "term": 11,
        "session_period": 1,
        "meeting_times": 1,
        "vote_times": 1,
        "vote_date": date(2024, 2, 19),
        "bill_no": None,
        "bill_name": "測試議案",
        "legislator_name": "測試乙",
        "party": "測試黨",
        "vote_result": "反對",
        "valid_from": now,
        "raw": {},
        "now": now,
    }
    await upsert_vote(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_vote(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_vote_upsert_correction(db_session) -> None:
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    base = {
        "uid": "test_vote_correction_001",
        "term": 11,
        "session_period": 1,
        "meeting_times": 1,
        "vote_times": 1,
        "vote_date": date(2024, 2, 19),
        "bill_no": None,
        "bill_name": "測試議案",
        "legislator_name": "測試丙",
        "party": "測試黨",
        "valid_from": t1,
        "raw": {},
    }
    await upsert_vote(db_session, vote_result="贊成", now=t1, **base)
    await db_session.flush()
    result = await upsert_vote(db_session, vote_result="反對", now=t2, **base)
    assert result == "updated"


# ── integration: full scraper run ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_vote_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 15
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_vote_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 15
    assert stats["errors"] == 0


# ── API: GET /v1/votes ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_votes_list_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/votes?term=11")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 15


@pytest.mark.asyncio
async def test_votes_list_session_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/votes?term=11&session_period=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 15


@pytest.mark.asyncio
async def test_votes_list_legislator_filter(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/votes?term=11&legislator_name=柯建銘")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 3  # 3 vote sessions
    assert all(r["legislator_name"] == "柯建銘" for r in rows)


# ── API: GET /v1/votes/party-discipline ───────────────────────────────────────


@pytest.mark.asyncio
async def test_party_discipline_basic(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/votes/party-discipline?term=11&session_period=1")
    assert resp.status_code == 200
    rows = resp.json()

    # 5 legislators should appear
    assert len(rows) == 5

    # Sorted by deviation_rate descending — 柯建銘 has the highest
    names = [r["legislator_name"] for r in rows]
    assert names[0] == "柯建銘"

    # 柯建銘: 1 deviation in vote session 2 (DPP majority=反對, 柯=贊成)
    # eligible in 3 vote sessions where DPP has majority (sessions 1, 2, 3)
    ke = next(r for r in rows if r["legislator_name"] == "柯建銘")
    assert ke["deviations"] == 1
    assert ke["votes_with_party_position"] == 3
    assert abs(ke["deviation_rate"] - 33.33) < 0.1

    # All others have 0 deviations
    for r in rows:
        if r["legislator_name"] != "柯建銘":
            assert r["deviations"] == 0
            assert r["deviation_rate"] == 0.0


@pytest.mark.asyncio
async def test_party_discipline_no_majority_excluded(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/votes/party-discipline?term=11&session_period=1")
    assert resp.status_code == 200
    rows = resp.json()

    # KMT has majority in vote sessions 1 and 2 only (session 3 is 1 贊成 / 1 反對)
    kmt_rows = [r for r in rows if r["party"] == "中國國民黨"]
    for r in kmt_rows:
        assert r["votes_with_party_position"] == 2
