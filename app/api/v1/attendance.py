"""Attendance endpoints — ranking with bi-temporal as-of support."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceRankRow

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get(
    "/ranking",
    response_model=list[AttendanceRankRow],
    summary="出缺席排行榜 (by term/session, optional as-of)",
)
async def attendance_ranking(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    meeting_type: str | None = Query(default=None, description="院會 or 委員會名稱篩選"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[AttendanceRankRow]:
    # ── bi-temporal filter ──────────────────────────────────────────────
    if as_of is None:
        temporal_filter = and_(
            Attendance.valid_to.is_(None),
            Attendance.superseded_at.is_(None),
        )
    else:
        temporal_filter = and_(
            Attendance.valid_from <= as_of,
            or_(Attendance.valid_to.is_(None), Attendance.valid_to > as_of),
            Attendance.recorded_at <= as_of,
            or_(
                Attendance.superseded_at.is_(None),
                Attendance.superseded_at > as_of,
            ),
        )

    # ── aggregation ────────────────────────────────────────────────────
    attended_col = func.sum(case((Attendance.attend_mark == "出席", 1), else_=0)).label("attended")
    absent_col = func.sum(case((Attendance.attend_mark == "缺席", 1), else_=0)).label("absent")
    leave_col = func.sum(case((Attendance.attend_mark.in_(["請假", "公假"]), 1), else_=0)).label(
        "leave"
    )
    total_col = func.count().label("total")
    rate_col = (
        func.sum(case((Attendance.attend_mark == "出席", 1), else_=0)) * 100.0 / func.count()
    ).label("rate")

    stmt = (
        select(
            Attendance.legislator_uid,
            Attendance.legislator_name,
            Attendance.term,
            Attendance.session_period,
            attended_col,
            absent_col,
            leave_col,
            total_col,
            rate_col,
        )
        .where(temporal_filter)
        .where(Attendance.term == term)
    )

    if session_period is not None:
        stmt = stmt.where(Attendance.session_period == session_period)
    if meeting_type is not None:
        stmt = stmt.where(Attendance.meeting_type == meeting_type)

    stmt = stmt.group_by(
        Attendance.legislator_uid,
        Attendance.legislator_name,
        Attendance.term,
        Attendance.session_period,
    ).order_by(desc("rate"))

    rows = (await session.execute(stmt)).mappings().all()
    return [AttendanceRankRow(**r) for r in rows]
