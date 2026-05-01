"""Scraper for 立委基本資料 (data.ly.gov.tw dataset id=16 歷屆委員資料).

Run directly:
    python -m scrapers.legislators [--fixture]

Uses openDatasetJson.action?id=16 which returns all terms' legislators.
Pages of 1000 records; uses page=N pagination.

Live API response shape (JSON):
    {
        "jsonList": [
            {
                "term":        "11",
                "name":        "王大明",
                "ename":       "WANG DA-MING",
                "sex":         "男",
                "party":       "民主進步黨",
                "partyGroup":  "民主進步黨黨團",
                "areaName":    "台北市第一選舉區",
                "committee":   "司法及法制委員會",
                "onboardDate": "2024/02/01",   ← Western calendar YYYY/MM/DD
                "leaveFlag":   "否",
                "leaveDate":   null,
                "leaveReason": null,
                ...
            },
            ...
        ]
    }

Fixture files (tests/fixtures/legislators_term{N}.json) use the older
"dataList" key and ROC calendar dates (e.g. "113/02/01") — both are
handled transparently by _roc_to_datetime().
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.database import get_sessionmaker
from scrapers.upsert import upsert_legislator

log = logging.getLogger(__name__)

# data.ly.gov.tw: dataset 16 = 歷屆委員資料 (all terms)
_LY_URL = "https://data.ly.gov.tw/odw/openDatasetJson.action"
_DATASET_ID = "16"
_FETCH_TERMS: frozenset[int] = frozenset([10, 11])
_PAGE_SIZE = 1000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://data.ly.gov.tw/",
}


def _roc_to_datetime(date_str: str | None) -> datetime | None:
    """Parse a date string to UTC datetime.

    Accepts both formats:
    - ROC calendar:     '113/02/01'  (year < 1912 → add 1911)
    - Western calendar: '2024/02/01' (year ≥ 1912 → use as-is)
    """
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        year = int(parts[0])
        if year < 1912:          # ROC year (e.g. 113 → 2024)
            year += 1911
        return datetime(year, int(parts[1]), int(parts[2]), tzinfo=UTC)
    except (ValueError, IndexError, AttributeError):
        return None


def _uid(term: int, name: str) -> str:
    return f"{term}_{name}"


async def _fetch_page(
    client: httpx.AsyncClient, page: int
) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": _DATASET_ID,
            "selectTerm": "all",
            "page": str(page),
        },
        headers=_HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected response type: {type(data)}")
    return data.get("jsonList", [])


async def _fetch_all(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Paginate through all records across all terms."""
    results: list[dict[str, Any]] = []
    page = 1
    while True:
        page_data = await _fetch_page(client, page)
        results.extend(page_data)
        log.debug("Page %d: %d records", page, len(page_data))
        if len(page_data) < _PAGE_SIZE:
            break
        page += 1
    return results


def _load_fixture(term: int) -> list[dict[str, Any]] | None:
    """Return fixture data for a term, or None if no fixture exists."""
    path = (
        Path(__file__).parent.parent
        / "tests"
        / "fixtures"
        / f"legislators_term{term}.json"
    )
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    # Fixtures use the older "dataList" key
    return data.get("dataList", data.get("jsonList", []))


async def run(use_fixture: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    stats: dict[str, int] = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    session_factory = get_sessionmaker()

    # ── collect rows ──────────────────────────────────────────────────────────
    all_rows: list[dict[str, Any]] = []

    if use_fixture:
        for term in sorted(_FETCH_TERMS):
            rows = _load_fixture(term) or []
            log.info("Term %d: %d records loaded from fixture", term, len(rows))
            all_rows.extend(rows)
    else:
        async with httpx.AsyncClient() as client:
            try:
                all_rows = await _fetch_all(client)
                log.info("Fetched %d total records from live API", len(all_rows))
            except Exception:
                log.exception("Failed to fetch legislators")
                stats["errors"] += 1
                return stats

    # ── upsert ────────────────────────────────────────────────────────────────
    async with session_factory() as session:
        async with session.begin():
            for row in all_rows:
                name = (row.get("name") or "").strip()
                if not name:
                    continue

                try:
                    term = int(row.get("term") or 0)
                except (TypeError, ValueError):
                    continue

                if term not in _FETCH_TERMS:
                    continue

                result = await upsert_legislator(
                    session,
                    uid=_uid(term, name),
                    term=term,
                    name=name,
                    district=row.get("areaName") or None,
                    party=row.get("party") or None,
                    valid_from=_roc_to_datetime(row.get("onboardDate")) or now,
                    raw=row,
                    now=now,
                )
                stats[result] += 1

    log.info("Scrape complete: %s", stats)
    return stats


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    asyncio.run(run(use_fixture="--fixture" in sys.argv))
