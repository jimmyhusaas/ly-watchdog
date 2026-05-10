"""activity_reports table (bi-temporal)

Revision ID: 0007_activity_reports
Revises: 0006_committee_memberships
Create Date: 2026-05-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_activity_reports"
down_revision: str | None = "0006_committee_memberships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activity_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("activity_uid", sa.String(length=256), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("lgno", sa.String(length=16), nullable=False),
        sa.Column("legislator_name", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
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
        "ix_activity_current",
        "activity_reports",
        ["activity_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index("ix_activity_term", "activity_reports", ["term"])
    op.create_index("ix_activity_legislator", "activity_reports", ["legislator_name"])
    op.create_index("ix_activity_lgno", "activity_reports", ["lgno"])


def downgrade() -> None:
    op.drop_index("ix_activity_lgno", table_name="activity_reports")
    op.drop_index("ix_activity_legislator", table_name="activity_reports")
    op.drop_index("ix_activity_term", table_name="activity_reports")
    op.drop_index("ix_activity_current", table_name="activity_reports")
    op.drop_table("activity_reports")
