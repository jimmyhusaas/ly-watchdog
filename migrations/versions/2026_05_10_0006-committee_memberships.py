"""committee_memberships table (bi-temporal)

Revision ID: 0006_committee_memberships
Revises: 0005_interpellations
Create Date: 2026-05-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_committee_memberships"
down_revision: str | None = "0005_interpellations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "committee_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("committee_uid", sa.String(length=256), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("session_period", sa.Integer(), nullable=False),
        sa.Column("legislator_name", sa.String(length=128), nullable=False),
        sa.Column("committee", sa.String(length=128), nullable=False),
        sa.Column("is_convener", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        "ix_committees_current",
        "committee_memberships",
        ["committee_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index(
        "ix_committees_term_session", "committee_memberships", ["term", "session_period"]
    )
    op.create_index("ix_committees_legislator", "committee_memberships", ["legislator_name"])
    op.create_index("ix_committees_name", "committee_memberships", ["committee"])


def downgrade() -> None:
    op.drop_index("ix_committees_name", table_name="committee_memberships")
    op.drop_index("ix_committees_legislator", table_name="committee_memberships")
    op.drop_index("ix_committees_term_session", table_name="committee_memberships")
    op.drop_index("ix_committees_current", table_name="committee_memberships")
    op.drop_table("committee_memberships")
