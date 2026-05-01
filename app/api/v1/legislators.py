"""Legislator endpoints with bi-temporal "as-of" support."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.legislator import Legislator
from app.schemas.legislator import LegislatorRead

router = APIRouter(prefix="/legislators", tags=["legislators"])


@router.get(
    "",
    response_model=list[LegislatorRead],
    summary="List legislators (current or as-of a specific point in time)",
)
async def list_legislators(
    term: int | None = Query(default=None, description="屆別篩選"),
    party: str | None = Query(default=None, description="黨籍篩選"),
    as_of: datetime | None = Query(
        default=None,
        description=(
            "ISO-8601 timestamp. 查詢在該時點系統記錄的立委資料快照。省略則回傳當前最新狀態。"
        ),
    ),
    session: AsyncSession = Depends(get_session),
) -> list[Legislator]:
    """Return legislators.

    - Without ``as_of``: the current, latest-known state.
    - With ``as_of``: bi-temporal point-in-time query (business + transaction time).
    """
    stmt = select(Legislator)

    if as_of is None:
        # Current state: facts still valid AND system record still current
        stmt = stmt.where(
            Legislator.valid_to.is_(None),
            Legislator.superseded_at.is_(None),
        )
    else:
        stmt = stmt.where(
            and_(
                Legislator.valid_from <= as_of,
                or_(Legislator.valid_to.is_(None), Legislator.valid_to > as_of),
                Legislator.recorded_at <= as_of,
                or_(
                    Legislator.superseded_at.is_(None),
                    Legislator.superseded_at > as_of,
                ),
            )
        )

    if term is not None:
        stmt = stmt.where(Legislator.term == term)
    if party is not None:
        stmt = stmt.where(Legislator.party == party)

    stmt = stmt.order_by(Legislator.legislator_uid)

    result = await session.execute(stmt)
    return list(result.scalars().all())
