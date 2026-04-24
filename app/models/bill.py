"""Bi-temporal bill record model.

One row = one bill (議案) at a given audit snapshot.

Natural key (bill_uid):
    "{term}_{session_period}_{bill_no}"

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


class Bill(Base):
    __tablename__ = "bills"

    # --- Surrogate key ---
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --- Natural business key ---
    bill_uid: Mapped[str] = mapped_column(String(512), nullable=False)

    # --- Bill context ---
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    session_period: Mapped[int] = mapped_column(Integer, nullable=False)
    bill_no: Mapped[str] = mapped_column(String(128), nullable=False)
    bill_name: Mapped[str] = mapped_column(Text, nullable=False)
    bill_org: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bill_proposer: Mapped[str | None] = mapped_column(Text, nullable=True)
    bill_cosignatory: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Status (the field that changes over time) ---
    bill_status: Mapped[str] = mapped_column(String(128), nullable=False)

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
            "ix_bills_current",
            "bill_uid",
            postgresql_where="superseded_at IS NULL",
        ),
        Index("ix_bills_term_session", "term", "session_period"),
        Index("ix_bills_status", "bill_status"),
    )
