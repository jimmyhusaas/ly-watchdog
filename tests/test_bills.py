"""Tests for bill scraper pipeline and bills API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from scrapers.bills import _bill_uid, _load_fixture, run
from scrapers.upsert import upsert_bill

# -- unit: helpers -------------------------------------------------------------


def test_bill_uid() -> None:
    uid = _bill_uid(11, 1, "政府提案第17851號")
    assert uid == "11_1_政府提案第17851號"


def test_fixture_loads() -> None:
    rows = _load_fixture(11)
    assert rows is not None
    assert len(rows) == 12
    orgs = {r["billOrg"] for r in rows}
    assert "行政院" in orgs
    assert "立法委員" in orgs
    assert "黨團" in orgs


# -- integration: upsert -------------------------------------------------------


@pytest.mark.asyncio
async def test_bill_upsert_insert(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    result = await upsert_bill(
        db_session,
        uid="test_bill_insert_001",
        term=11,
        session_period=1,
        bill_no="政府提案第99001號",
        bill_name="測試法案",
        bill_org="行政院",
        bill_proposer=None,
        bill_cosignatory=None,
        bill_status="委員會審查",
        valid_from=now,
        raw={},
        now=now,
    )
    assert result == "inserted"


@pytest.mark.asyncio
async def test_bill_upsert_unchanged(db_session) -> None:
    now = datetime(2024, 2, 19, tzinfo=UTC)
    kwargs = {
        "uid": "test_bill_unchanged_001",
        "term": 11,
        "session_period": 1,
        "bill_no": "政府提案第99002號",
        "bill_name": "測試法案乙",
        "bill_org": "行政院",
        "bill_proposer": None,
        "bill_cosignatory": None,
        "bill_status": "院會審查",
        "valid_from": now,
        "raw": {},
        "now": now,
    }
    await upsert_bill(db_session, **kwargs)
    await db_session.flush()
    result = await upsert_bill(db_session, **kwargs)
    assert result == "unchanged"


@pytest.mark.asyncio
async def test_bill_upsert_correction(db_session) -> None:
    t1 = datetime(2024, 2, 19, tzinfo=UTC)
    t2 = datetime(2024, 3, 1, tzinfo=UTC)
    base = {
        "uid": "test_bill_correction_001",
        "term": 11,
        "session_period": 1,
        "bill_no": "委員提案第99003號",
        "bill_name": "測試法案丙",
        "bill_org": "立法委員",
        "bill_proposer": "測試甲",
        "bill_cosignatory": None,
        "valid_from": t1,
        "raw": {},
    }
    await upsert_bill(db_session, bill_status="委員會審查", now=t1, **base)
    await db_session.flush()
    result = await upsert_bill(db_session, bill_status="院會審查", now=t2, **base)
    assert result == "updated"


# -- integration: full scraper run ---------------------------------------------


@pytest.mark.asyncio
async def test_full_bill_run(clean_db) -> None:
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 12
    assert stats["updated"] == 0
    assert stats["unchanged"] == 0
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_full_bill_run_idempotent(clean_db) -> None:
    await run(use_fixture=True)
    stats = await run(use_fixture=True)
    assert stats["inserted"] == 0
    assert stats["unchanged"] == 12
    assert stats["errors"] == 0


# -- API: GET /v1/bills --------------------------------------------------------


@pytest.mark.asyncio
async def test_bills_list_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/bills?term=11")
    assert resp.status_code == 200
    assert len(resp.json()) == 12


@pytest.mark.asyncio
async def test_bills_filter_by_status(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/bills?term=11&bill_status=完成立法")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 4
    assert all(r["bill_status"] == "完成立法" for r in rows)


@pytest.mark.asyncio
async def test_bills_filter_by_proposer(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/bills?term=11&bill_proposer=柯建銘")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    assert all("柯建銘" in (r["bill_proposer"] or "") for r in rows)


# -- API: GET /v1/bills/stats --------------------------------------------------


@pytest.mark.asyncio
async def test_bills_stats_api(client: AsyncClient, clean_db) -> None:
    await run(use_fixture=True)
    resp = await client.get("/v1/bills/stats?term=11")
    assert resp.status_code == 200
    data = {row["bill_org"]: row["count"] for row in resp.json()}
    assert data["行政院"] == 4
    assert data["立法委員"] == 6
    assert data["黨團"] == 2
