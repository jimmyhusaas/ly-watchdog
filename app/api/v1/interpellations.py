"""Interpellation endpoints — list with keyword search and bi-temporal as-of support."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.interpellation import Interpellation
from app.schemas.interpellation import InterpellationRead

router = APIRouter(prefix="/interpellations", tags=["interpellations"])


def _temporal_filter(model: type[Interpellation], as_of: datetime | None) -> ColumnElement[bool]:
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
    response_model=list[InterpellationRead],
    summary="院會發言紀錄列表 (by term, optional keyword search, as-of, paginated)",
)
async def list_interpellations(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    legislator_name: str | None = Query(default=None, description="立委姓名篩選"),
    keyword: str | None = Query(default=None, description="發言內容關鍵字搜尋"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    limit: int = Query(default=20, ge=1, le=100, description="每頁筆數 (max 100, 因內容較長)"),
    offset: int = Query(default=0, ge=0, description="跳過筆數"),
    session: AsyncSession = Depends(get_session),
) -> list[InterpellationRead]:
    temporal_filter = _temporal_filter(Interpellation, as_of)

    stmt = select(Interpellation).where(temporal_filter).where(Interpellation.term == term)

    if session_period is not None:
        stmt = stmt.where(Interpellation.session_period == session_period)
    if legislator_name is not None:
        stmt = stmt.where(Interpellation.legislator_name == legislator_name)
    if keyword is not None:
        stmt = stmt.where(Interpellation.interp_content.ilike(f"%{keyword}%"))

    stmt = (
        stmt.order_by(
            Interpellation.session_period,
            Interpellation.meeting_times,
            Interpellation.legislator_name,
        )
        .limit(limit)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).scalars().all()
    return [InterpellationRead.model_validate(r) for r in rows]
