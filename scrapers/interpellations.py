"""Scraper for 院會發言紀錄 (data.ly.gov.tw dataset id=7).

Covers 委員在院會的發言內容, 包含質詢、討論等各類發言。

Run directly:
    python -m scrapers.interpellations [--fixture]

NOTE: Originally targeted dataset id=8 (公報委員會紀錄, committee gazette),
which has no per-legislator fields.  Corrected to id=7 (院會發言紀錄) which
provides legislatorName + full speech content.

Live API response shape (JSON):
    {
        "jsonList": [
            {
                "term":           "11",
                "sessionPeriod":  "1",
                "meetingTimes":   "1",
                "selectTerm":     "1101",
                "legislatorName": "柯建銘",
                "speakType":      "質詢",
                "content":        "發言內容文字...",
                "dateTimeDesc":   "...",
                "meetingRoom":    "議場",
                "chairman":       "..."
            },
            ...
        ]
    }
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx

from app.database import get_sessionmaker
from scrapers.upsert import upsert_interpellation

log = logging.getLogger(__name__)

INTERPS_DATASET_ID = 7  # 院會發言紀錄 (id=8 is committee gazette, no per-legislator fields)
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
    """Parse int from a value that may be None, 0, or the string 'null'."""
    s = str(v or "").strip()
    return int(s) if s and s.lower() not in ("null", "none") else 0


def _interp_uid(
    term: int,
    session_period: int,
    session_times: str,
    legislator_name: str,
    content: str,
) -> str:
    # sessionTimes differentiates meetings; content hash differentiates multiple
    # speeches by the same person at the same meeting (e.g. point-of-order + speech).
    content_hash = hashlib.md5(content[:500].encode()).hexdigest()[:8]
    return f"{term}_{session_period}_{session_times}_{legislator_name}_{content_hash}"


async def _fetch_page(client: httpx.AsyncClient, page: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": str(INTERPS_DATASET_ID),
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
    path = (
        Path(__file__).parent.parent / "tests" / "fixtures" / f"interpellations_term{term}_s1.json"
    )
    if not path.exists():
        return None
    return cast(list[dict[str, Any]], json.loads(path.read_text()).get("dataList", []))


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
                log.exception("Failed to fetch interpellations")
                stats["errors"] += 1
                return stats

    # ── upsert ────────────────────────────────────────────────────────────────
    seen_uids: set[str] = set()
    async with session_factory() as session, session.begin():
        for row in all_rows:
            legislator_name = (row.get("legislatorName") or "").strip()
            if not legislator_name:
                continue

            # Live API uses "content"; fixture may use "interp" (legacy key)
            interp_content = (row.get("content") or row.get("interp") or "").strip()
            if not interp_content:
                continue

            try:
                term = int(row.get("term") or 0)
            except (TypeError, ValueError):
                continue

            if term not in _FETCH_TERMS:
                continue

            try:
                sp = _to_int(row.get("sessionPeriod"))
                mt = _to_int(row.get("meetingTimes"))
            except (ValueError, TypeError):
                continue

            # sessionTimes is always populated (e.g. "01"); meetingTimes is often null
            session_times = (row.get("sessionTimes") or "00").strip()
            uid = _interp_uid(term, sp, session_times, legislator_name, interp_content)

            # Skip exact duplicates within the same batch (identical source records)
            if uid in seen_uids:
                log.debug("Skipping duplicate UID %s", uid)
                continue
            seen_uids.add(uid)

            result = await upsert_interpellation(
                session,
                uid=uid,
                term=term,
                session_period=sp,
                meeting_times=mt,
                legislator_name=legislator_name,
                interp_content=interp_content,
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
