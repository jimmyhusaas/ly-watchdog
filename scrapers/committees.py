"""Scraper for 委員會委員名單 (data.ly.gov.tw dataset id=14).

Records which legislators sit on which committees each term/session,
including whether they serve as convener (召委).

Run directly:
    python -m scrapers.committees [--fixture]

Live API response shape (JSON):
    {
        "jsonList": [
            {
                "isCoChairman": "N",
                "committee":    "司法及法制委員會",
                "term":         "11",
                "lgno":         "00086",
                "name":         "柯建銘",
                "sessionPeriod":"1"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx

from app.database import get_sessionmaker
from scrapers.upsert import upsert_committee_membership

log = logging.getLogger(__name__)

COMMITTEES_DATASET_ID = 14
_LY_URL = "https://data.ly.gov.tw/odw/openDatasetJson.action"
_FETCH_TERMS: frozenset[int] = frozenset([10, 11])
_PAGE_SIZE = 1000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Referer": "https://data.ly.gov.tw/",
}


def _to_int(v: Any) -> int:
    s = str(v or "").strip()
    return int(s) if s and s.lower() not in ("null", "none") else 0


def _committee_uid(term: int, session_period: int, name: str, committee: str) -> str:
    return f"{term}_{session_period}_{name}_{committee}"


async def _fetch_page(client: httpx.AsyncClient, page: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": str(COMMITTEES_DATASET_ID),
            "selectTerm": "all",
            "page": str(page),
        },
        headers=_HEADERS,
        timeout=60,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected response type: {type(data)}")
    return cast(list[dict[str, Any]], data.get("jsonList", []))


async def _fetch_all(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Paginate through all records."""
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
    path = Path(__file__).parent.parent / "tests" / "fixtures" / f"committees_term{term}_s1.json"
    if not path.exists():
        return None
    return cast(list[dict[str, Any]], json.loads(path.read_text()).get("dataList", []))


async def run(use_fixture: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    stats: dict[str, int] = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    session_factory = get_sessionmaker()

    # -- collect rows ----------------------------------------------------------
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
                log.exception("Failed to fetch committee memberships")
                stats["errors"] += 1
                return stats

    # -- upsert ----------------------------------------------------------------
    seen_uids: set[str] = set()
    async with session_factory() as session, session.begin():
        for row in all_rows:
            name = (row.get("name") or "").strip()
            committee = (row.get("committee") or "").strip()
            if not name or not committee:
                continue

            try:
                term = int(row.get("term") or 0)
            except (TypeError, ValueError):
                continue

            if term not in _FETCH_TERMS:
                continue

            sp = _to_int(row.get("sessionPeriod"))
            is_convener = (row.get("isCoChairman") or "N").strip().upper() == "Y"

            uid = _committee_uid(term, sp, name, committee)
            if uid in seen_uids:
                log.debug("Skipping duplicate UID %s", uid)
                continue
            seen_uids.add(uid)

            result = await upsert_committee_membership(
                session,
                uid=uid,
                term=term,
                session_period=sp,
                legislator_name=name,
                committee=committee,
                is_convener=is_convener,
                valid_from=now,
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
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    asyncio.run(run(use_fixture="--fixture" in sys.argv))
