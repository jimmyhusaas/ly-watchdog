"""Committee membership endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.committee_membership import CommitteeMembership
from app.schemas.committee_membership import CommitteeMembershipRead

router = APIRouter(prefix="/committees", tags=["committees"])


def _temporal_filter(
    model: type[CommitteeMembership], as_of: datetime | None
) -> ColumnElement[bool]:
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
    response_model=list[CommitteeMembershipRead],
    summary="委員會成員列表 (by term/session, optional committee or legislator filter)",
)
async def list_committee_memberships(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    committee: str | None = Query(default=None, description="委員會名稱 (模糊比對)"),
    legislator_name: str | None = Query(default=None, description="立委姓名篩選"),
    convener_only: bool = Query(default=False, description="只顯示召委"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp - 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[CommitteeMembershipRead]:
    temporal_filter = _temporal_filter(CommitteeMembership, as_of)

    stmt = (
        select(CommitteeMembership).where(temporal_filter).where(CommitteeMembership.term == term)
    )

    if session_period is not None:
        stmt = stmt.where(CommitteeMembership.session_period == session_period)
    if committee is not None:
        stmt = stmt.where(CommitteeMembership.committee.ilike(f"%{committee}%"))
    if legislator_name is not None:
        stmt = stmt.where(CommitteeMembership.legislator_name == legislator_name)
    if convener_only:
        stmt = stmt.where(CommitteeMembership.is_convener.is_(True))

    stmt = (
        stmt.order_by(
            CommitteeMembership.committee,
            CommitteeMembership.legislator_name,
        )
        .limit(limit)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).scalars().all()
    return [CommitteeMembershipRead.model_validate(r) for r in rows]
