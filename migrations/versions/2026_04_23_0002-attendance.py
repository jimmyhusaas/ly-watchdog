"""attendance records (bi-temporal)

Revision ID: 0002_attendance
Revises: 0001_initial
Create Date: 2026-04-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_attendance"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attendance",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("attendance_uid", sa.String(length=256), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("meeting_times", sa.Integer(), nullable=False),
        sa.Column("meeting_type", sa.String(length=64), nullable=False),
        sa.Column("meeting_name", sa.String(length=256), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("legislator_uid", sa.String(length=64), nullable=False),
        sa.Column("legislator_name", sa.String(length=128), nullable=False),
        sa.Column("attend_mark", sa.String(length=16), nullable=False),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_attendance_current",
        "attendance",
        ["attendance_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index("ix_attendance_legislator", "attendance", ["legislator_uid"])
    op.create_index(
        "ix_attendance_term_session", "attendance", ["term", "session_period"]
    )


def downgrade() -> None:
    op.drop_index("ix_attendance_term_session", table_name="attendance")
    op.drop_index("ix_attendance_legislator", table_name="attendance")
    op.drop_index("ix_attendance_current", table_name="attendance")
    op.drop_table("attendance")
