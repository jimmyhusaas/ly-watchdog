"""Legislator endpoints with bi-temporal "as-of" support."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.bill import Bill
from app.models.interpellation import Interpellation
from app.models.legislator import Legislator
from app.schemas.bill import BillRead
from app.schemas.interpellation import InterpellationRead
from app.schemas.legislator import LegislatorDetail, LegislatorRead

router = APIRouter(prefix="/legislators", tags=["legislators"])


def _current_filter(model: type) -> object:  # type: ignore[type-arg]
    return and_(
        model.valid_to.is_(None),
        model.superseded_at.is_(None),
    )


def _as_of_filter(model: type, as_of: datetime) -> object:  # type: ignore[type-arg]
    return and_(
        model.valid_from <= as_of,
        or_(model.valid_to.is_(None), model.valid_to > as_of),
        model.recorded_at <= as_of,
        or_(model.superseded_at.is_(None), model.superseded_at > as_of),
    )


@router.get(
    "",
    response_model=list[LegislatorRead],
    summary="立委列表 (current or as-of a specific point in time)",
)
async def list_legislators(
    term: int | None = Query(default=None, description="屆別篩選"),
    party: str | None = Query(default=None, description="黨籍篩選"),
    district: str | None = Query(default=None, description="選區篩選 (模糊比對)"),
    as_of: datetime | None = Query(
        default=None,
        description="ISO-8601 timestamp. 查詢在該時點系統記錄的立委資料快照。省略則回傳當前最新狀態。",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[Legislator]:
    stmt = select(Legislator)
    stmt = stmt.where(
        _current_filter(Legislator) if as_of is None else _as_of_filter(Legislator, as_of)
    )

    if term is not None:
        stmt = stmt.where(Legislator.term == term)
    if party is not None:
        stmt = stmt.where(Legislator.party == party)
    if district is not None:
        stmt = stmt.where(Legislator.district.ilike(f"%{district}%"))

    stmt = stmt.order_by(Legislator.term.desc(), Legislator.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{name}",
    response_model=LegislatorDetail,
    summary="立委個人資料 + 提案數 / 發言數統計",
)
async def get_legislator(
    name: str,
    term: int | None = Query(default=None, description="屆別 (省略則回傳最新屆)"),
    session: AsyncSession = Depends(get_session),
) -> LegislatorDetail:
    stmt = select(Legislator).where(
        _current_filter(Legislator),
        Legislator.name == name,
    )
    if term is not None:
        stmt = stmt.where(Legislator.term == term)
    else:
        stmt = stmt.order_by(Legislator.term.desc()).limit(1)

    legislator = (await session.execute(stmt)).scalars().first()
    if legislator is None:
        raise HTTPException(status_code=404, detail=f"立委「{name}」找不到")

    # bill count
    bill_count = (
        await session.execute(
            select(func.count())
            .select_from(Bill)
            .where(
                _current_filter(Bill),
                Bill.term == legislator.term,
                Bill.bill_proposer.ilike(f"%{name}%"),
            )
        )
    ).scalar_one()

    # speech count
    speech_count = (
        await session.execute(
            select(func.count())
            .select_from(Interpellation)
            .where(
                _current_filter(Interpellation),
                Interpellation.term == legislator.term,
                Interpellation.legislator_name == name,
            )
        )
    ).scalar_one()

    return LegislatorDetail(
        **LegislatorRead.model_validate(legislator).model_dump(),
        bill_count=bill_count,
        speech_count=speech_count,
    )


@router.get(
    "/{name}/bills",
    response_model=list[BillRead],
    summary="立委提案列表 (模糊比對 bill_proposer)",
)
async def legislator_bills(
    name: str,
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[BillRead]:
    stmt = select(Bill).where(
        _current_filter(Bill),
        Bill.term == term,
        Bill.bill_proposer.ilike(f"%{name}%"),
    )
    if session_period is not None:
        stmt = stmt.where(Bill.session_period == session_period)

    stmt = stmt.order_by(Bill.session_period, Bill.bill_no).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return [BillRead.model_validate(r) for r in rows]


@router.get(
    "/{name}/speeches",
    response_model=list[InterpellationRead],
    summary="立委院會發言列表",
)
async def legislator_speeches(
    name: str,
    term: int = Query(description="屆別"),
    session_period: int | None = Query(default=None, description="會期篩選"),
    keyword: str | None = Query(default=None, description="發言內容關鍵字搜尋"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[InterpellationRead]:
    stmt = select(Interpellation).where(
        _current_filter(Interpellation),
        Interpellation.term == term,
        Interpellation.legislator_name == name,
    )
    if session_period is not None:
        stmt = stmt.where(Interpellation.session_period == session_period)
    if keyword is not None:
        stmt = stmt.where(Interpellation.interp_content.ilike(f"%{keyword}%"))

    stmt = (
        stmt.order_by(
            Interpellation.session_period,
            Interpellation.meeting_times,
        )
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [InterpellationRead.model_validate(r) for r in rows]
