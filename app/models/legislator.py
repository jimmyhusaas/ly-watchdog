"""Bi-temporal legislator model.

Design
------
This table uses the **single-table bi-temporal** pattern:

* `valid_from` / `valid_to`         → business time (when the fact is true IRL)
* `recorded_at` / `superseded_at`   → transaction time (when the system knew it)

Rows are **append-only**. Updating a legislator means:

1. Stamp the currently-active row's `superseded_at = now()` (or if the fact
   itself ended, also set `valid_to`).
2. INSERT a new row with the new values and `recorded_at = now()`.

The "current, latest-known" view of a legislator is:
    WHERE valid_to IS NULL AND superseded_at IS NULL

A point-in-time query for `as_of` (a datetime) is:
    WHERE valid_from <= :as_of
      AND (valid_to        IS NULL OR valid_to        > :as_of)
      AND recorded_at   <= :as_of
      AND (superseded_at IS NULL OR superseded_at > :as_of)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Legislator(Base):
    """A single bi-temporal record describing a legislator at a point in time."""

    __tablename__ = "legislators"

    # --- Surrogate key (row identity) ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key (from 立法院 data source) ---
    legislator_uid: Mapped[str] = mapped_column(String(64), nullable=False)

    # --- Domain data ---
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    district: Mapped[str | None] = mapped_column(String(128), nullable=True)
    party: Mapped[str | None] = mapped_column(String(64), nullable=True)
    term: Mapped[int] = mapped_column(Integer, nullable=False)  # 屆別

    # --- Original payload (auditability / debugging) ---
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # --- Bi-temporal: business time ---
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Bi-temporal: transaction time ---
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Fast "current state" queries
        Index(
            "ix_legislators_current",
            "legislator_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        # Fast "as-of" queries
        Index("ix_legislators_uid_valid", "legislator_uid", "valid_from"),
        Index("ix_legislators_term", "term"),
    )

    def __repr__(self) -> str:  # pragma: no cover — debug helper
        return (
            f"Legislator(uid={self.legislator_uid!r}, name={self.name!r}, "
            f"term={self.term}, valid_from={self.valid_from!s}, "
            f"superseded={self.superseded_at is not None})"
        )
