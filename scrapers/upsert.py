"""Bi-temporal upsert helper — shared by all scrapers."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legislator import Legislator


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

    changed = (
        existing.name != name
        or existing.district != district
        or existing.party != party
    )
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
