"""Scraper for 立委基本資料 (data.ly.gov.tw dataset id=16).

Run directly:
    python -m scrapers.legislators

The scraper fetches all legislators for the configured terms and writes
them to Postgres using the bi-temporal append-only pattern.

data.ly.gov.tw API shape (JSON):
    {
        "dataList": [
            {
                "term":         "11",
                "name":         "王大明",
                "ename":        "WANG DA-MING",
                "sex":          "男",
                "party":        "民主進步黨",
                "partyGroup":   "民主進步黨黨團",
                "areaName":     "台北市第一選舉區",
                "committee":    "司法及法制委員會",
                "onboardDate":  "113/02/01",   ← ROC calendar
                "degree":       "...",
                "experience":   "..."
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
from scrapers.upsert import upsert_legislator

log = logging.getLogger(__name__)

# data.ly.gov.tw: dataset 16 = 委員基本資料
_LY_URL = "https://data.ly.gov.tw/odw/openDatasetJson.action"
_FETCH_TERMS = [10, 11]
_PAGE_SIZE = 1000


def _roc_to_datetime(date_str: str | None) -> datetime | None:
    """Convert ROC calendar string '113/02/01' → UTC datetime."""
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        year = int(parts[0]) + 1911
        return datetime(year, int(parts[1]), int(parts[2]), tzinfo=UTC)
    except (ValueError, IndexError, AttributeError):
        return None


def _uid(term: int, name: str) -> str:
    return f"{term}_{name}"


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


async def _fetch_page(client: httpx.AsyncClient, term: int, offset: int) -> list[dict[str, Any]]:
    resp = await client.get(
        _LY_URL,
        params={
            "id": "16",
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
    """Return fixture data for a term, or None if no fixture exists."""
    path = Path(__file__).parent.parent / "tests" / "fixtures" / f"legislators_term{term}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return cast(list[dict[str, Any]], data.get("dataList", []))


async def run(use_fixture: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    stats: dict[str, int] = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    session_factory = get_sessionmaker()

    async with httpx.AsyncClient() as client:
        for term in _FETCH_TERMS:
            log.info("Fetching term %d …", term)

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
                    name = (row.get("name") or "").strip()
                    if not name:
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

            log.info("Term %d done. stats so far: %s", term, stats)

    log.info("Scrape complete: %s", stats)
    return stats


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    fixture_mode = "--fixture" in sys.argv
    asyncio.run(run(use_fixture=fixture_mode))
