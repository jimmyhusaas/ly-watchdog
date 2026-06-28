"""Bi-temporal upsert helpers — shared by all scrapers."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_report import ActivityReport
from app.models.attendance import Attendance
from app.models.bill import Bill
from app.models.committee_membership import CommitteeMembership
from app.models.interpellation import Interpellation
from app.models.legislator import Legislator
from app.models.vote import Vote


async def _get_current(
    session: AsyncSession,
    model: type[Any],
    uid_column: Any,
    uid: str,
    now: datetime,
) -> Any | None:
    """Fetch the single current (non-superseded) row for a natural key.

    Each upsert is supposed to leave at most one row per natural key with
    superseded_at/valid_to both NULL. If more than one is found — e.g. from a
    historical scraper bug that wrote duplicates before this uid was touched
    again — keep the most recently recorded row and supersede the rest, so
    the table self-heals on the next write instead of raising
    MultipleResultsFound.
    """
    stmt = (
        select(model)
        .where(uid_column == uid, model.superseded_at.is_(None), model.valid_to.is_(None))
        .order_by(model.recorded_at.desc())
    )
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        return None
    current, *stale_duplicates = rows
    for dup in stale_duplicates:
        dup.superseded_at = now
    return current


async def upsert_legislator(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    name: str,
    district: str | None,
    party: str | None,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one legislator record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: Legislator | None = await _get_current(
        session, Legislator, Legislator.legislator_uid, uid, now
    )

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
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one attendance record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: Attendance | None = await _get_current(
        session, Attendance, Attendance.attendance_uid, uid, now
    )

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
    existing: Vote | None = await _get_current(session, Vote, Vote.vote_uid, uid, now)

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


async def upsert_bill(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    bill_no: str,
    bill_name: str,
    bill_org: str | None,
    bill_proposer: str | None,
    bill_cosignatory: str | None,
    bill_status: str,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one bill record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: Bill | None = await _get_current(session, Bill, Bill.bill_uid, uid, now)

    if existing is None:
        session.add(
            Bill(
                bill_uid=uid,
                term=term,
                session_period=session_period,
                bill_no=bill_no,
                bill_name=bill_name,
                bill_org=bill_org,
                bill_proposer=bill_proposer,
                bill_cosignatory=bill_cosignatory,
                bill_status=bill_status,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.bill_status == bill_status:
        return "unchanged"

    # Review status updated — supersede old row, insert new
    existing.superseded_at = now
    session.add(
        Bill(
            bill_uid=uid,
            term=term,
            session_period=session_period,
            bill_no=bill_no,
            bill_name=bill_name,
            bill_org=bill_org,
            bill_proposer=bill_proposer,
            bill_cosignatory=bill_cosignatory,
            bill_status=bill_status,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"


async def upsert_interpellation(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    meeting_times: int,
    legislator_name: str,
    interp_content: str,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one interpellation record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: Interpellation | None = await _get_current(
        session, Interpellation, Interpellation.interp_uid, uid, now
    )

    if existing is None:
        session.add(
            Interpellation(
                interp_uid=uid,
                term=term,
                session_period=session_period,
                meeting_times=meeting_times,
                legislator_name=legislator_name,
                interp_content=interp_content,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.interp_content == interp_content:
        return "unchanged"

    # Content corrected (e.g. OCR fix) — supersede old row, insert new
    existing.superseded_at = now
    session.add(
        Interpellation(
            interp_uid=uid,
            term=term,
            session_period=session_period,
            meeting_times=meeting_times,
            legislator_name=legislator_name,
            interp_content=interp_content,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"


async def upsert_committee_membership(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    legislator_name: str,
    committee: str,
    is_convener: bool,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one committee membership record.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: CommitteeMembership | None = await _get_current(
        session, CommitteeMembership, CommitteeMembership.committee_uid, uid, now
    )

    if existing is None:
        session.add(
            CommitteeMembership(
                committee_uid=uid,
                term=term,
                session_period=session_period,
                legislator_name=legislator_name,
                committee=committee,
                is_convener=is_convener,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.is_convener == is_convener:
        return "unchanged"

    # Convener status changed -- supersede old row, insert new
    existing.superseded_at = now
    session.add(
        CommitteeMembership(
            committee_uid=uid,
            term=term,
            session_period=session_period,
            legislator_name=legislator_name,
            committee=committee,
            is_convener=is_convener,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"


async def upsert_activity_report(
    session: AsyncSession,
    *,
    uid: str,
    term: int,
    session_period: int,
    lgno: str,
    legislator_name: str,
    subject: str,
    content: str,
    published_at: datetime,
    valid_from: datetime,
    raw: dict[str, Any],
    now: datetime,
) -> str:
    """Append-only bi-temporal write for one activity report.

    Returns 'inserted', 'updated', or 'unchanged'.
    """
    existing: ActivityReport | None = await _get_current(
        session, ActivityReport, ActivityReport.activity_uid, uid, now
    )

    if existing is None:
        session.add(
            ActivityReport(
                activity_uid=uid,
                term=term,
                session_period=session_period,
                lgno=lgno,
                legislator_name=legislator_name,
                subject=subject,
                content=content,
                published_at=published_at,
                raw_data=raw,
                valid_from=valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        return "inserted"

    if existing.content == content:
        return "unchanged"

    # Content corrected -- supersede old row, insert new
    existing.superseded_at = now
    session.add(
        ActivityReport(
            activity_uid=uid,
            term=term,
            session_period=session_period,
            lgno=lgno,
            legislator_name=legislator_name,
            subject=subject,
            content=content,
            published_at=published_at,
            raw_data=raw,
            valid_from=existing.valid_from,
            valid_to=None,
            recorded_at=now,
            superseded_at=None,
        )
    )
    return "updated"
