"""Bi-temporal upsert helpers — shared by all scrapers."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.legislator import Legislator
from app.models.vote import Vote


async def upsert_legislator(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    name: str,
    district: str | None,
    party: str | None,
    valid_from: datetime,
    raw: dict,
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one legislator record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    stmt = select(Legislator).where(
        Legislator.legislator_uid == uid,
        Legislator.superseded_at.is_(None),
        Legislator.valid_to.is_(None),
    )
    existing: Legislator | None = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        session.add(
            Legislator(
                legislator_uid=uid,
                term=term,
                name=name,
                district=district,
                party=party,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    changed = existing.name != name or existing.district != district or existing.party != party
    if not changed:
        return "unchanged"

    # Supersede old row, insert corrected row preserving original valid_from
    existing.superseded_at = now
    session.add(
        Legislator(
            legislator_uid=uid,
            term=term,
            name=name,
            district=district,
            party=party,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"


async def upsert_attendance(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    meeting_times: int,
    meeting_type: str,
    meeting_name: str,
    meeting_date: object,  # datetime.date
    legislator_uid: str,
    legislator_name: str,
    attend_mark: str,
    valid_from: datetime,
    raw: dict,
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one attendance record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    stmt = select(Attendance).where(
        Attendance.attendance_uid == uid,
        Attendance.superseded_at.is_(None),
        Attendance.valid_to.is_(None),
    )
    existing: Attendance | None = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        session.add(
            Attendance(
                attendance_uid=uid,
                term=term,
                session_period=session_period,
                meeting_times=meeting_times,
                meeting_type=meeting_type,
                meeting_name=meeting_name,
                meeting_date=meeting_date,
                legislator_uid=legislator_uid,
                legislator_name=legislator_name,
                attend_mark=attend_mark,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.attend_mark == attend_mark:
        return "unchanged"

    # Corrected attendance mark — supersede old row, insert new
    existing.superseded_at = now
    session.add(
        Attendance(
            attendance_uid=uid,
            term=term,
            session_period=session_period,
            meeting_times=meeting_times,
            meeting_type=meeting_type,
            meeting_name=meeting_name,
            meeting_date=meeting_date,
            legislator_uid=legislator_uid,
            legislator_name=legislator_name,
            attend_mark=attend_mark,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"


async def upsert_vote(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    meeting_times: int,
    vote_times: int,
    vote_date: date,
    bill_no: str | None,
    bill_name: str,
    legislator_name: str,
    party: str | None,
    vote_result: str,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one vote record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    stmt = select(Vote).where(
        Vote.vote_uid == uid,
        Vote.superseded_at.is_(None),
        Vote.valid_to.is_(None),
    )
    existing: Vote | None = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        session.add(
            Vote(
                vote_uid=uid,
                term=term,
                session_period=session_period,
                meeting_times=meeting_times,
                vote_times=vote_times,
                vote_date=vote_date,
                bill_no=bill_no,
                bill_name=bill_name,
                legislator_name=legislator_name,
                party=party,
                vote_result=vote_result,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.vote_result == vote_result:
        return "unchanged"

    # Corrected vote result — supersede old row, insert new
    existing.superseded_at = now
    session.add(
        Vote(
            vote_uid=uid,
            term=term,
            session_period=session_period,
            meeting_times=meeting_times,
            vote_times=vote_times,
            vote_date=vote_date,
            bill_no=bill_no,
            bill_name=bill_name,
            legislator_name=legislator_name,
            party=party,
            vote_result=vote_result,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"
