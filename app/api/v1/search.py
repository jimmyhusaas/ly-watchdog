"""Unified cross-collection search endpoint.

Searches legislators, bills, and interpellations in parallel and returns
ranked results with type discriminators and a short content highlight.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.bill import Bill
from app.models.interpellation import Interpellation
from app.models.legislator import Legislator

router = APIRouter(prefix="/search", tags=["search"])

_HIGHLIGHT_WINDOW = 80  # chars around match to show


def _highlight(body: str, keyword: str) -> str:
    """Return a short snippet with the keyword in context."""
    kw = re.escape(keyword)
    m = re.search(kw, body, re.IGNORECASE)
    if not m:
        return body[: _HIGHLIGHT_WINDOW * 2].rstrip()
    start = max(0, m.start() - _HIGHLIGHT_WINDOW)
    end = min(len(body), m.end() + _HIGHLIGHT_WINDOW)
    snippet = body[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(body):
        snippet = snippet + "…"
    return snippet


def _current() -> Any:
    return and_(
        text("superseded_at IS NULL"),
        text("valid_to IS NULL"),
    )


class SearchResult(BaseModel):
    type: Literal["legislator", "bill", "speech"]
    term: int
    # legislator
    name: str | None = None
    party: str | None = None
    district: str | None = None
    # bill
    bill_no: str | None = None
    bill_name: str | None = None
    bill_status: str | None = None
    bill_proposer: str | None = None
    session_period: int | None = None
    # speech
    legislator_name: str | None = None
    # shared
    highlight: str | None = None


@router.get(
    "",
    response_model=list[SearchResult],
    summary="跨資料集關鍵字搜尋 (立委 + 法案 + 院會發言)",
)
async def search(
    q: str = Query(min_length=1, description="搜尋關鍵字"),
    term: int | None = Query(default=None, description="屆別篩選 (省略則搜尋全部)"),
    limit: int = Query(default=20, ge=1, le=100, description="每種類型最多回傳筆數"),
    session: AsyncSession = Depends(get_session),
) -> list[SearchResult]:
    results: list[SearchResult] = []
    pattern = f"%{q}%"

    # -- legislators -----------------------------------------------------------
    leg_stmt = select(Legislator).where(
        _current(),
        Legislator.name.ilike(pattern),
    )
    if term is not None:
        leg_stmt = leg_stmt.where(Legislator.term == term)
    leg_stmt = leg_stmt.order_by(Legislator.term.desc()).limit(limit)
    for leg in (await session.execute(leg_stmt)).scalars():
        results.append(
            SearchResult(
                type="legislator",
                term=leg.term,
                name=leg.name,
                party=leg.party,
                district=leg.district,
            )
        )

    # -- bills -----------------------------------------------------------------
    bill_stmt = select(Bill).where(
        _current(),
        or_(
            Bill.bill_name.ilike(pattern),
            Bill.bill_proposer.ilike(pattern),
        ),
    )
    if term is not None:
        bill_stmt = bill_stmt.where(Bill.term == term)
    bill_stmt = bill_stmt.order_by(Bill.term.desc(), Bill.session_period.desc()).limit(limit)
    for bill in (await session.execute(bill_stmt)).scalars():
        hl = _highlight(bill.bill_name, q)
        results.append(
            SearchResult(
                type="bill",
                term=bill.term,
                bill_no=bill.bill_no,
                bill_name=bill.bill_name,
                bill_status=bill.bill_status,
                bill_proposer=bill.bill_proposer,
                session_period=bill.session_period,
                highlight=hl,
            )
        )

    # -- speeches --------------------------------------------------------------
    speech_stmt = select(Interpellation).where(
        _current(),
        Interpellation.interp_content.ilike(pattern),
    )
    if term is not None:
        speech_stmt = speech_stmt.where(Interpellation.term == term)
    speech_stmt = speech_stmt.order_by(
        Interpellation.term.desc(),
        Interpellation.session_period.desc(),
    ).limit(limit)
    for sp in (await session.execute(speech_stmt)).scalars():
        results.append(
            SearchResult(
                type="speech",
                term=sp.term,
                legislator_name=sp.legislator_name,
                session_period=sp.session_period,
                highlight=_highlight(sp.interp_content, q),
            )
        )

    return results
