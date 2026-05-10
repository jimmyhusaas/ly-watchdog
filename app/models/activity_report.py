"""Bi-temporal activity report model (dataset id=17: 委員問政資料).

One row = one legislator's weekly activity report.

Natural key (activity_uid):
    "{lgno}_{date_str}"  e.g. "00015_2012-03-19"

Bi-temporal columns:
    valid_from / valid_to        -- business time
    recorded_at / superseded_at  -- transaction time
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ActivityReport(Base):
    __tablename__ = "activity_reports"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    activity_uid: Mapped[str] = mapped_column(String(256), nullable=False)

    # --- Context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    lgno: Mapped[str] = mapped_column(String(16), nullable=False)
    legislator_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # --- Content ---
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

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
            "ix_activity_current",
            "activity_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_activity_term", "term"),
        Index("ix_activity_legislator", "legislator_name"),
        Index("ix_activity_lgno", "lgno"),
    )
