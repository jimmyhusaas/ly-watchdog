"""Bill endpoints — list and org-level stats with bi-temporal as-of support."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.bill import Bill
from app.schemas.bill import BillOrgStatRow, BillRead

router = APIRouter(prefix="/bills", tags=["bills"])


def _temporal_filter(model: type[Bill], as_of: datetime | None) -> ColumnElement[bool]:
    if as_of is None:
        return and_(
            model.valid_to.is_(None),
            model.superseded_at.is_(None),
        )
    return and_(
        model.valid_from <= as_of,
        or_(model.valid_to.is_(None), model.valid_to > as_of),
        model.recorded_at <= as_of,
        or_(model.superseded_at.is_(None), model.superseded_at > as_of),
    )


@router.get(
    "",
    response_model=list[BillRead],
    summary="法案列表 (by term, optional as-of, paginated)",
)
async def list_bills(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    bill_status: str | None = Query(default=None, description="審查進度篩選"),
    bill_proposer: str | None = Query(default=None, description="提案委員姓名篩選 (模糊比對)"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="每頁筆數 (max 500)"),
    offset: int = Query(default=0, ge=0, description="跳過筆數"),
    session: AsyncSession = Depends(get_session),
) -> list[BillRead]:
    temporal_filter = _temporal_filter(Bill, as_of)

    stmt = select(Bill).where(temporal_filter).where(Bill.term == term)

    if session_period is not None:
        stmt = stmt.where(Bill.session_period == session_period)
    if bill_status is not None:
        stmt = stmt.where(Bill.bill_status == bill_status)
    if bill_proposer is not None:
        stmt = stmt.where(Bill.bill_proposer.ilike(f"%{bill_proposer}%"))

    stmt = stmt.order_by(Bill.session_period, Bill.bill_no).limit(limit).offset(offset)

    rows = (await session.execute(stmt)).scalars().all()
    return [BillRead.model_validate(r) for r in rows]


@router.get(
    "/stats",
    response_model=list[BillOrgStatRow],
    summary="提案類型統計 — 依提案機關分組 (by term)",
)
async def bills_stats(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[BillOrgStatRow]:
    temporal_filter = _temporal_filter(Bill, as_of)

    stmt = (
        select(
            Bill.bill_org,
            func.count().label("count"),
        )
        .where(temporal_filter)
        .where(Bill.term == term)
    )

    if session_period is not None:
        stmt = stmt.where(Bill.session_period == session_period)

    stmt = stmt.group_by(Bill.bill_org).order_by(desc("count"))

    rows = (await session.execute(stmt)).mappings().all()
    return [BillOrgStatRow(**r) for r in rows]
