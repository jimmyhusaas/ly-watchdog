"""Bi-temporal committee membership model.

One row = one legislator serving on one committee in one term/session.

Natural key (committee_uid):
    "{term}_{session_period}_{legislator_name}_{committee}"

Bi-temporal columns:
    valid_from / valid_to        -- business time
    recorded_at / superseded_at  -- transaction time
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CommitteeMembership(Base):
    __tablename__ = "committee_memberships"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    committee_uid: Mapped[str] = mapped_column(String(256), nullable=False)

    # --- Context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    legislator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    committee: Mapped[str] = mapped_column(String(128), nullable=False)

    # --- Mutable field: chairmanship status ---
    is_convener: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Original payload ---
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
        Index(
            "ix_committees_current",
            "committee_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_committees_term_session", "term", "session_period"),
        Index("ix_committees_legislator", "legislator_name"),
        Index("ix_committees_name", "committee"),
    )
