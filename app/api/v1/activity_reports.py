"""Activity report endpoints (dataset id=17: 委員問政資料)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.activity_report import ActivityReport
from app.schemas.activity_report import ActivityReportRead

router = APIRouter(prefix="/activity-reports", tags=["activity-reports"])


def _temporal_filter(model: type[ActivityReport], as_of: datetime | None) -> ColumnElement[bool]:
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
    response_model=list[ActivityReportRead],
    summary="委員問政週報列表 (by term, optional lgno/keyword filter, paginated)",
)
async def list_activity_reports(
    term: int = Query(description="屆別"),
    lgno: str | None = Query(default=None, description="立委編號 (e.g. '00015') -- 主要篩選方式"),
    keyword: str | None = Query(default=None, description="內容關鍵字搜尋"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    limit: int = Query(default=20, ge=1, le=100, description="每頁筆數 (max 100)"),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityReportRead]:
    temporal_filter = _temporal_filter(ActivityReport, as_of)

    stmt = select(ActivityReport).where(temporal_filter).where(ActivityReport.term == term)

    if lgno is not None:
        stmt = stmt.where(ActivityReport.lgno == lgno)
    if keyword is not None:
        stmt = stmt.where(ActivityReport.content.ilike(f"%{keyword}%"))

    stmt = stmt.order_by(ActivityReport.published_at.desc()).limit(limit).offset(offset)

    rows = (await session.execute(stmt)).scalars().all()
    return [ActivityReportRead.model_validate(r) for r in rows]
