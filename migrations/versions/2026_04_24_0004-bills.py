"""bills table (bi-temporal)

Revision ID: 0004_bills
Revises: 0003_votes
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_bills"
down_revision: str | None = "0003_votes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("bill_uid", sa.String(length=512), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("bill_no", sa.String(length=128), nullable=False),
        sa.Column("bill_name", sa.Text(), nullable=False),
        sa.Column("bill_org", sa.String(length=256), nullable=True),
        sa.Column("bill_proposer", sa.Text(), nullable=True),
        sa.Column("bill_cosignatory", sa.Text(), nullable=True),
        sa.Column("bill_status", sa.String(length=128), nullable=False),
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
        "ix_bills_current",
        "bills",
        ["bill_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index("ix_bills_term_session", "bills", ["term", "session_period"])
    op.create_index("ix_bills_status", "bills", ["bill_status"])


def downgrade() -> None:
    op.drop_index("ix_bills_status", table_name="bills")
    op.drop_index("ix_bills_term_session", table_name="bills")
    op.drop_index("ix_bills_current", table_name="bills")
    op.drop_table("bills")
