"""Vote endpoints — list and party discipline with bi-temporal as-of support."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.vote import Vote
from app.schemas.vote import PartyDisciplineRow, VoteRead

router = APIRouter(prefix="/votes", tags=["votes"])


def _temporal_filter(model: type[Vote], as_of: datetime | None) -> ColumnElement[bool]:
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
    response_model=list[VoteRead],
    summary="表決記錄列表 (by term, optional as-of)",
)
async def list_votes(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    meeting_times: int | None = Query(default=None, description="院會次別篩選"),
    legislator_name: str | None = Query(default=None, description="立委姓名篩選"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp — 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[VoteRead]:
    temporal_filter = _temporal_filter(Vote, as_of)

    stmt = select(Vote).where(temporal_filter).where(Vote.term == term)

    if session_period is not None:
        stmt = stmt.where(Vote.session_period == session_period)
    if meeting_times is not None:
        stmt = stmt.where(Vote.meeting_times == meeting_times)
    if legislator_name is not None:
        stmt = stmt.where(Vote.legislator_name == legislator_name)

    stmt = stmt.order_by(Vote.vote_date.desc(), Vote.meeting_times, Vote.vote_times)

    rows = (await session.execute(stmt)).scalars().all()
    return [VoteRead.model_validate(r) for r in rows]


@router.get(
    "/party-discipline",
    response_model=list[PartyDisciplineRow],
    summary="黨紀偏離率排行榜 (by term, optional session_period and as-of)",
)
async def party_discipline(
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp — 時間旅行查詢; 省略則回傳當前最新狀態",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[PartyDisciplineRow]:
    temporal_filter = _temporal_filter(Vote, as_of)

    # CTE 1: per (vote_session, party, vote_result) counts — exclude 棄權
    vote_counts = (
        select(
            Vote.term,
            Vote.session_period,
            Vote.meeting_times,
            Vote.vote_times,
            Vote.party,
            Vote.vote_result,
            func.count().label("n"),
        )
        .where(temporal_filter)
        .where(Vote.term == term)
        .where(Vote.vote_result.in_(["贊成", "反對"]))
        .group_by(
            Vote.term,
            Vote.session_period,
            Vote.meeting_times,
            Vote.vote_times,
            Vote.party,
            Vote.vote_result,
        )
        .cte("vote_counts")
    )

    if session_period is not None:
        vote_counts = (
            select(
                Vote.term,
                Vote.session_period,
                Vote.meeting_times,
                Vote.vote_times,
                Vote.party,
                Vote.vote_result,
                func.count().label("n"),
            )
            .where(temporal_filter)
            .where(Vote.term == term)
            .where(Vote.session_period == session_period)
            .where(Vote.vote_result.in_(["贊成", "反對"]))
            .group_by(
                Vote.term,
                Vote.session_period,
                Vote.meeting_times,
                Vote.vote_times,
                Vote.party,
                Vote.vote_result,
            )
            .cte("vote_counts")
        )

    # CTE 2: total valid votes per (vote_session, party)
    party_totals = (
        select(
            vote_counts.c.term,
            vote_counts.c.session_period,
            vote_counts.c.meeting_times,
            vote_counts.c.vote_times,
            vote_counts.c.party,
            func.sum(vote_counts.c.n).label("total_valid"),
        )
        .group_by(
            vote_counts.c.term,
            vote_counts.c.session_period,
            vote_counts.c.meeting_times,
            vote_counts.c.vote_times,
            vote_counts.c.party,
        )
        .cte("party_totals")
    )

    # CTE 3: majority position — only where one result strictly > 50%
    party_position = (
        select(
            vote_counts.c.term,
            vote_counts.c.session_period,
            vote_counts.c.meeting_times,
            vote_counts.c.vote_times,
            vote_counts.c.party,
            vote_counts.c.vote_result.label("majority_result"),
        )
        .join(
            party_totals,
            and_(
                vote_counts.c.term == party_totals.c.term,
                vote_counts.c.session_period == party_totals.c.session_period,
                vote_counts.c.meeting_times == party_totals.c.meeting_times,
                vote_counts.c.vote_times == party_totals.c.vote_times,
                vote_counts.c.party == party_totals.c.party,
            ),
        )
        .where(vote_counts.c.n * 2 > party_totals.c.total_valid)
        .cte("party_position")
    )

    # Final: per-legislator deviation stats
    stmt = (
        select(
            Vote.legislator_name,
            Vote.party,
            Vote.term,
            Vote.session_period,
            func.count().label("votes_with_party_position"),
            func.sum(
                case((Vote.vote_result != party_position.c.majority_result, 1), else_=0)
            ).label("deviations"),
            (
                func.sum(
                    case(
                        (Vote.vote_result != party_position.c.majority_result, 1),
                        else_=0,
                    )
                )
                * 100.0
                / func.count()
            ).label("deviation_rate"),
        )
        .join(
            party_position,
            and_(
                Vote.term == party_position.c.term,
                Vote.session_period == party_position.c.session_period,
                Vote.meeting_times == party_position.c.meeting_times,
                Vote.vote_times == party_position.c.vote_times,
                Vote.party == party_position.c.party,
            ),
        )
        .where(temporal_filter)
        .where(Vote.term == term)
        .where(Vote.vote_result.in_(["贊成", "反對"]))
        .group_by(Vote.legislator_name, Vote.party, Vote.term, Vote.session_period)
        .order_by(desc("deviation_rate"))
    )

    if session_period is not None:
        stmt = stmt.where(Vote.session_period == session_period)

    rows = (await session.execute(stmt)).mappings().all()
    return [PartyDisciplineRow(**r) for r in rows]
