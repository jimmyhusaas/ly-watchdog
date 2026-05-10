"""Scraper for 委員問政資料 (data.ly.gov.tw dataset id=17).

Weekly activity reports published by legislators' offices,
covering interpellations, proposals, press conferences, etc.

Run directly:
    python -m scrapers.activity_reports [--fixture]

Live API response shape (JSON):
    {
        "jsonList": [
            {
                "selectTerm":  "0800",
                "subject2":    null,
                "subject1":    "20120316立法委員吳宜臻問政動態周報",
                "term":        "8",
                "lgno":        "00015",
                "data":        "立法委員吳宜臻國會辦公室\r\n問政動態周報...",
                "date":        "2012-03-19T00:00:00+08:00"
            },
            ...
        ]
    }

NOTE: The API currently only returns term=8 data (765 records).
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
from scrapers.upsert import upsert_activity_report

log = logging.getLogger(__name__)

ACTIVITY_DATASET_ID = 17
_LY_URL = "https://data.ly.gov.tw/odw/openDatasetJson.action"
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


def _parse_date(v: Any) -> datetime | None:
    """Parse ISO-8601 date string from API. Returns UTC datetime or None."""
    s = str(v or "").strip()
    if not s or s.lower() in ("null", "none"):
        return None
    try:
        # API returns e.g. "2012-03-19T00:00:00+08:00"
        dt = datetime.fromisoformat(s)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def _activity_uid(lgno: str, date_str: str) -> str:
    return f"{lgno}_{date_str}"


async def _fetch_page(client: httpx.AsyncClient, page: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": str(ACTIVITY_DATASET_ID),
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


def _load_fixture() -> list[dict[str, Any]] | None:
    path = Path(__file__).parent.parent / "tests" / "fixtures" / "activity_reports.json"
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
        rows = _load_fixture() or []
        log.info("%d records loaded from fixture", len(rows))
        all_rows = rows
    else:
        async with httpx.AsyncClient() as client:
            try:
                all_rows = await _fetch_all(client)
                log.info("Fetched %d total records from live API", len(all_rows))
            except Exception:
                log.exception("Failed to fetch activity reports")
                stats["errors"] += 1
                return stats

    # -- upsert ----------------------------------------------------------------
    seen_uids: set[str] = set()
    async with session_factory() as session, session.begin():
        for row in all_rows:
            lgno = (row.get("lgno") or "").strip()
            # subject1 is the title; subject2 is a secondary header (often null)
            subject = (row.get("subject1") or row.get("subject2") or "").strip()
            content = (row.get("data") or "").strip()
            if not lgno or not content:
                continue

            published_at = _parse_date(row.get("date"))
            if published_at is None:
                continue

            try:
                term = int(row.get("term") or 0)
            except (TypeError, ValueError):
                continue

            if term == 0:
                continue

            sp = _to_int(row.get("selectTerm") or "0")
            # selectTerm is a 4-digit code like "0800"; extract session period digit
            if sp > 100:
                sp = sp % 100

            date_str = published_at.strftime("%Y-%m-%d")
            uid = _activity_uid(lgno, date_str)

            if uid in seen_uids:
                log.debug("Skipping duplicate UID %s", uid)
                continue
            seen_uids.add(uid)

            # The API does not return a legislator name field directly.
            # lgno is the canonical identifier; name is stored as empty string
            # (callers can join against the legislators table if needed).
            legislator_name = ""

            result = await upsert_activity_report(
                session,
                uid=uid,
                term=term,
                session_period=sp,
                lgno=lgno,
                legislator_name=legislator_name,
                subject=subject,
                content=content,
                published_at=published_at,
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
