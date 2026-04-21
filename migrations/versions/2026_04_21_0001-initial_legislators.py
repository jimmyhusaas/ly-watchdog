"""initial legislators (bi-temporal)

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "legislators",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("legislator_uid", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("party", sa.String(length=64), nullable=True),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Bi-temporal: business time
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        # Bi-temporal: transaction time
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial index for "current system record" queries
    op.create_index(
        "ix_legislators_current",
        "legislators",
        ["legislator_uid"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    # As-of queries benefit from (uid, valid_from)
    op.create_index(
        "ix_legislators_uid_valid",
        "legislators",
        ["legislator_uid", "valid_from"],
    )

    op.create_index("ix_legislators_term", "legislators", ["term"])


def downgrade() -> None:
    op.drop_index("ix_legislators_term", table_name="legislators")
    op.drop_index("ix_legislators_uid_valid", table_name="legislators")
    op.drop_index("ix_legislators_current", table_name="legislators")
    op.drop_table("legislators")
