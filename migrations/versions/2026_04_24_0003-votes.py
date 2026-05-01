"""votes table (bi-temporal)

Revision ID: 0003_votes
Revises: 0002_attendance
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_votes"
down_revision: str | None = "0002_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "votes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("vote_uid", sa.String(length=256), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("meeting_times", sa.Integer(), nullable=False),
        sa.Column("vote_times", sa.Integer(), nullable=False),
        sa.Column("vote_date", sa.Date(), nullable=False),
        sa.Column("bill_no", sa.String(length=128), nullable=True),
        sa.Column("bill_name", sa.Text(), nullable=False),
        sa.Column("legislator_name", sa.String(length=128), nullable=False),
        sa.Column("party", sa.String(length=64), nullable=True),
        sa.Column("vote_result", sa.String(length=16), nullable=False),
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
        "ix_votes_current",
        "votes",
        ["vote_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index("ix_votes_term_session", "votes", ["term", "session_period"])
    op.create_index("ix_votes_legislator", "votes", ["legislator_name"])


def downgrade() -> None:
    op.drop_index("ix_votes_legislator", table_name="votes")
    op.drop_index("ix_votes_term_session", table_name="votes")
    op.drop_index("ix_votes_current", table_name="votes")
    op.drop_table("votes")
