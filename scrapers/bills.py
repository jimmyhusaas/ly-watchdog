"""Scraper for 議案資料 (data.ly.gov.tw dataset id=20).

Run directly:
    python -m scrapers.bills [--fixture]

API response shape (JSON):
    {
        "dataList": [
            {
                "term":            "11",
                "sessionPeriod":   "1",
                "billNo":          "政府提案第17851號",
                "billName":        "行政院函請審議...",
                "billOrg":         "行政院",
                "billProposer":    "",
                "billCosignatory": "",
                "billStatus":      "完成立法",
                "pdfUrl":          ""
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
from scrapers.upsert import upsert_bill

log = logging.getLogger(__name__)

BILLS_DATASET_ID = 20
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


def _bill_uid(term: int, session_period: int, bill_no: str) -> str:
    return f"{term}_{session_period}_{bill_no}"


async def _fetch_page(client: httpx.AsyncClient, term: int, offset: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": str(BILLS_DATASET_ID),
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
    path = Path(__file__).parent.parent / "tests" / "fixtures" / f"bills_term{term}_s1.json"
    if not path.exists():
        return None
    return cast(list[dict[str, Any]], json.loads(path.read_text()).get("dataList", []))


async def run(use_fixture: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    stats: dict[str, int] = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    session_factory = get_sessionmaker()

    async with httpx.AsyncClient() as client:
        for term in _FETCH_TERMS:
            log.info("Fetching bills for term %d ...", term)

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
                    bill_no = (row.get("billNo") or "").strip()
                    if not bill_no:
                        continue

                    try:
                        sp = int(row.get("sessionPeriod") or 0)
                    except (ValueError, TypeError):
                        continue

                    bill_status = (row.get("billStatus") or "").strip()
                    if not bill_status:
                        continue

                    uid = _bill_uid(term, sp, bill_no)

                    result = await upsert_bill(
                        session,
                        uid=uid,
                        term=term,
                        session_period=sp,
                        bill_no=bill_no,
                        bill_name=(row.get("billName") or "").strip(),
                        bill_org=(row.get("billOrg") or "").strip() or None,
                        bill_proposer=(row.get("billProposer") or "").strip() or None,
                        bill_cosignatory=(row.get("billCosignatory") or "").strip() or None,
                        bill_status=bill_status,
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
