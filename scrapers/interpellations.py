"""Scraper for 質詢事項 (data.ly.gov.tw dataset id=8).

Run directly:
    python -m scrapers.interpellations [--fixture]

API response shape (JSON):
    {
        "dataList": [
            {
                "term":          "11",
                "sessionPeriod": "1",
                "meetingTimes":  "1",
                "legislatorName":"柯建銘",
                "interp":        "質詢內容文字..."
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
from scrapers.upsert import upsert_interpellation

log = logging.getLogger(__name__)

INTERPS_DATASET_ID = 8
_LY_URL = "https://data.ly.gov.tw/odw/usageRecord.action"
_FETCH_TERMS = [10, 11]
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


def _interp_uid(
    term: int,
    session_period: int,
    meeting_times: int,
    legislator_name: str,
) -> str:
    return f"{term}_{session_period}_{meeting_times}_{legislator_name}"


async def _fetch_page(client: httpx.AsyncClient, term: int, offset: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": str(INTERPS_DATASET_ID),
            "type": "JSON",
            "fileType": "JSON",
            "term": str(term),
            "offset": str(offset),
            "limit": str(_PAGE_SIZE),
        },
        headers=_HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected response type: {type(data)}")
    return cast(list[dict[str, Any]], data.get("dataList", []))


async def _fetch_term(client: httpx.AsyncClient, term: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await _fetch_page(client, term, offset)
        results.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
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

    async with httpx.AsyncClient() as client:
        for term in _FETCH_TERMS:
            log.info("Fetching interpellations for term %d ...", term)

            if use_fixture:
                rows = _load_fixture(term) or []
                log.info("Term %d: %d records loaded from fixture", term, len(rows))
            else:
                try:
                    rows = await _fetch_term(client, term)
                except Exception:
                    log.exception("Failed to fetch term %d", term)
                    stats["errors"] += 1
                    continue
                log.info("Term %d: %d records fetched", term, len(rows))

            async with session_factory() as session, session.begin():
                for row in rows:
                    legislator_name = (row.get("legislatorName") or "").strip()
                    if not legislator_name:
                        continue

                    interp_content = (row.get("interp") or "").strip()
                    if not interp_content:
                        continue

                    try:
                        sp = int(row.get("sessionPeriod") or 0)
                        mt = int(row.get("meetingTimes") or 0)
                    except (ValueError, TypeError):
                        continue

                    uid = _interp_uid(term, sp, mt, legislator_name)

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

            log.info("Term %d done. stats so far: %s", term, stats)

    log.info("Scrape complete: %s", stats)
    return stats


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    asyncio.run(run(use_fixture="--fixture" in sys.argv))
