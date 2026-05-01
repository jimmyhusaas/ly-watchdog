"""Bi-temporal vote record model.

One row = one legislator's vote on one division in one meeting.

Natural key (vote_uid):
    "{term}_{session_period}_{meeting_times}_{vote_times}_{legislator_name}"

Bi-temporal columns follow the same pattern as the other tables:
    valid_from / valid_to        — business time (when the fact is true IRL)
    recorded_at / superseded_at  — transaction time (when the system knew it)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Vote(Base):
    __tablename__ = "votes"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    vote_uid: Mapped[str] = mapped_column(String(256), nullable=False)

    # --- Vote context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    meeting_times: Mapped[int] = mapped_column(Integer, nullable=False)  # 本會期第幾次院會
    vote_times: Mapped[int] = mapped_column(Integer, nullable=False)  # 本次院會第幾個表決
    vote_date: Mapped[date] = mapped_column(Date, nullable=False)
    bill_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bill_name: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Legislator ---
    legislator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    party: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- Vote result ---
    vote_result: Mapped[str] = mapped_column(String(16), nullable=False)
    # 贊成 | 反對 | 棄權

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
            "ix_votes_current",
            "vote_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_votes_term_session", "term", "session_period"),
        Index("ix_votes_legislator", "legislator_name"),
    )
