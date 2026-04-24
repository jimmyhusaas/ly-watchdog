"""Bi-temporal interpellation record model.

One row = one legislator's interpellation at one plenary session.

Natural key (interp_uid):
    "{term}_{session_period}_{meeting_times}_{legislator_name}"

Bi-temporal columns follow the same pattern as the other tables:
    valid_from / valid_to        — business time (when the fact is true IRL)
    recorded_at / superseded_at  — transaction time (when the system knew it)
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


class Interpellation(Base):
    __tablename__ = "interpellations"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    interp_uid: Mapped[str] = mapped_column(String(256), nullable=False)

    # --- Interpellation context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    meeting_times: Mapped[int] = mapped_column(Integer, nullable=False)
    legislator_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # --- Content (the field that changes over time, e.g. OCR corrections) ---
    interp_content: Mapped[str] = mapped_column(Text, nullable=False)

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
            "ix_interps_current",
            "interp_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_interps_term_session", "term", "session_period"),
        Index("ix_interps_legislator", "legislator_name"),
    )
