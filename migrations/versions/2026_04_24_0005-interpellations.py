"""interpellations table (bi-temporal)

Revision ID: 0005_interpellations
Revises: 0004_bills
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_interpellations"
down_revision: str | None = "0004_bills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interpellations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("interp_uid", sa.String(length=256), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("meeting_times", sa.Integer(), nullable=False),
        sa.Column("legislator_name", sa.String(length=128), nullable=False),
        sa.Column("interp_content", sa.Text(), nullable=False),
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
        "ix_interps_current",
        "interpellations",
        ["interp_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index("ix_interps_term_session", "interpellations", ["term", "session_period"])
    op.create_index("ix_interps_legislator", "interpellations", ["legislator_name"])


def downgrade() -> None:
    op.drop_index("ix_interps_legislator", table_name="interpellations")
    op.drop_index("ix_interps_term_session", table_name="interpellations")
    op.drop_index("ix_interps_current", table_name="interpellations")
    op.drop_table("interpellations")
