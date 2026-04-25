"""Scraper for 委員出缺席紀錄 (data.ly.gov.tw dataset id=36).

Run directly:
    python -m scrapers.attendance [--fixture]

API response shape (JSON):
    {
        "dataList": [
            {
                "term":           "11",
                "sessionPeriod":  "1",
                "sessionTimes":   "11011001",
                "meetingTimes":   "1",
                "meetingTypeName":"院會",
                "meetingName":    "第11屆第1會期第1次院會",
                "meetingDate":    "113/02/19",
                "legislatorName": "柯建銘",
                "attendMark":     "出席"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import httpx

from app.database import get_sessionmaker
from scrapers.upsert import upsert_attendance

log = logging.getLogger(__name__)

_LY_URL = "https://data.ly.gov.tw/odw/openDatasetJson.action"
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


def _roc_to_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        return date(int(parts[0]) + 1911, int(parts[1]), int(parts[2]))
    except (ValueError, IndexError, AttributeError):
        return None


def _attendance_uid(
    term: int, session_period: int, meeting_type: str, meeting_times: int, legislator_name: str
) -> str:
    return f"{term}_{session_period}_{meeting_type}_{meeting_times}_{legislator_name}"


def _legislator_uid(term: int, name: str) -> str:
    return f"{term}_{name}"


async def _fetch_page(client: httpx.AsyncClient, term: int, offset: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": "36",
            "fileType": "JSON",
            "term": str(term),
        },
        headers=_HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected response type: {type(data)}")
    return cast(list[dict[str, Any]], data.get("jsonList", []))


async def _fetch_term(client: httpx.AsyncClient, term: int) -> list[dict[str, Any]]:
    return await _fetch_page(client, term, 0)


def _load_fixture(term: int) -> list[dict[str, Any]] | None:
    path = Path(__file__).parent.parent / "tests" / "fixtures" / f"attendance_term{term}_s1.json"
    if not path.exists():
        return None
    return cast(list[dict[str, Any]], json.loads(path.read_text()).get("dataList", []))


async def run(use_fixture: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    stats: dict[str, int] = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    session_factory = get_sessionmaker()

    async with httpx.AsyncClient() as client:
        for term in _FETCH_TERMS:
            log.info("Fetching attendance for term %d …", term)

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

                    try:
                        sp = int(row.get("sessionPeriod") or 0)
                        mt = int(row.get("meetingTimes") or 0)
                    except (ValueError, TypeError):
                        continue

                    meeting_type = (row.get("meetingTypeName") or "").strip()
                    meeting_date = _roc_to_date(row.get("meetingDate"))
                    if meeting_date is None:
                        continue

                    uid = _attendance_uid(term, sp, meeting_type, mt, legislator_name)
                    valid_from = datetime(
                        meeting_date.year,
                        meeting_date.month,
                        meeting_date.day,
                        tzinfo=UTC,
                    )

                    result = await upsert_attendance(
                        session,
                        uid=uid,
                        term=term,
                        session_period=sp,
                        meeting_times=mt,
                        meeting_type=meeting_type,
                        meeting_name=(row.get("meetingName") or "").strip(),
                        meeting_date=meeting_date,
                        legislator_uid=_legislator_uid(term, legislator_name),
                        legislator_name=legislator_name,
                        attend_mark=(row.get("attendMark") or "").strip(),
                        valid_from=valid_from,
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
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    asyncio.run(run(use_fixture="--fixture" in sys.argv))
