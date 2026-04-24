"""Integration tests for the legislator scraper pipeline.

Uses fixture data (tests/fixtures/legislators_term11.json) so the test
suite runs without a live connection to data.ly.gov.tw.

Covers:
- First run inserts all records
- Second run is idempotent (unchanged)
- A field change (party) triggers a supersede + new insert
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.legislator import Legislator
from scrapers.legislators import _load_fixture, _roc_to_datetime, run
from scrapers.upsert import upsert_legislator

# ── unit: helpers ─────────────────────────────────────────────────────────────


def test_roc_date_conversion() -> None:
    dt = _roc_to_datetime("113/02/01")
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 2
    assert dt.day == 1


def test_roc_date_invalid_returns_none() -> None:
    assert _roc_to_datetime(None) is None
    assert _roc_to_datetime("") is None
    assert _roc_to_datetime("bad/data") is None


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 5
    names = {r["name"] for r in rows}
    assert "柯建銘" in names
    assert "韓國瑜" in names


# ── integration: upsert ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 1, tzinfo=UTC)
    result = await upsert_legislator(
        db_session,
        uid="test_insert_a001",
        term=11,
        name="測試議員甲",
        district="測試選區",
        party="民主進步黨",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"
    await db_session.flush()

    rows = (
        (
            await db_session.execute(
                select(Legislator).where(Legislator.legislator_uid == "test_insert_a001")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].party == "民主進步黨"
    assert rows[0].superseded_at is None


@pytest.mark.asyncio
async def test_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 1, tzinfo=UTC)
    await upsert_legislator(
        db_session,
        uid="test_unchanged_b001",
        term=11,
        name="測試議員乙",
        district="測試選區二",
        party="民主進步黨",
        valid_from=now,
        raw={},
        now=now,
    )
    await db_session.flush()

    result = await upsert_legislator(
        db_session,
        uid="test_unchanged_b001",
        term=11,
        name="測試議員乙",
        district="測試選區二",
        party="民主進步黨",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "unchanged"

    rows = (
        (
            await db_session.execute(
                select(Legislator).where(Legislator.legislator_uid == "test_unchanged_b001")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_upsert_party_change_supersedes(db_session) -> None:
    t1 = datetime(2024, 2, 1, tzinfo=UTC)
    t2 = datetime(2024, 9, 1, tzinfo=UTC)

    await upsert_legislator(
        db_session,
        uid="test_party_change_c001",
        term=11,
        name="測試議員丙",
        district="不分區",
        party="台灣民眾黨",
        valid_from=t1,
        raw={},
        now=t1,
    )
    await db_session.flush()

    result = await upsert_legislator(
        db_session,
        uid="test_party_change_c001",
        term=11,
        name="測試議員丙",
        district="不分區",
        party="無黨籍",
        valid_from=t1,
        raw={},
        now=t2,
    )
    assert result == "updated"
    await db_session.flush()

    rows = (
        (
            await db_session.execute(
                select(Legislator)
                .where(Legislator.legislator_uid == "test_party_change_c001")
                .order_by(Legislator.recorded_at)
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 2
    old, new = rows
    assert old.party == "台灣民眾黨"
    assert old.superseded_at == t2
    assert new.party == "無黨籍"
    assert new.superseded_at is None
    assert new.valid_from == t1  # preserves original valid_from


# ── integration: full scraper run ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_run_fixture_inserts_all(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 5
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 5
    assert stats["errors"] == 0
