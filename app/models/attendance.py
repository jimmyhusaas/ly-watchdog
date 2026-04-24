"""Bi-temporal attendance record model.

One row = one legislator's attendance mark at one meeting.

Natural key (attendance_uid):
    "{term}_{session_period}_{meeting_type}_{meeting_times}_{legislator_name}"

Bi-temporal columns follow the same pattern as the legislators table:
    valid_from / valid_to        — business time (when the fact is true IRL)
    recorded_at / superseded_at  — transaction time (when the system knew it)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    attendance_uid: Mapped[str] = mapped_column(String(256), nullable=False)

    # --- Meeting context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    meeting_times: Mapped[int] = mapped_column(Integer, nullable=False)
    meeting_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 院會 / 委員會
    meeting_name: Mapped[str] = mapped_column(String(256), nullable=False)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Legislator ---
    legislator_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    legislator_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # --- Attendance mark ---
    attend_mark: Mapped[str] = mapped_column(String(16), nullable=False)
    # 出席 | 缺席 | 請假 | 公假 | 列席

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
            "ix_attendance_current",
            "attendance_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_attendance_legislator", "legislator_uid"),
        Index("ix_attendance_term_session", "term", "session_period"),
    )
