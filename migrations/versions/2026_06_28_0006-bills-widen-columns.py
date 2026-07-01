"""widen bill_uid and bill_no to Text

Revision ID: 0006_bills_widen
Revises: 0005_interpellations
Create Date: 2026-06-28

bill_no was VARCHAR(128) and bill_uid VARCHAR(512); some API rows have
bill_no values exceeding 128 chars, causing DataError on insert.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_bills_widen"
down_revision: str | None = "0005_interpellations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("bills", "bill_uid", type_=sa.Text(), existing_type=sa.String(512))
    op.alter_column("bills", "bill_no", type_=sa.Text(), existing_type=sa.String(128))
    op.alter_column("bills", "bill_org", type_=sa.Text(), existing_type=sa.String(256), existing_nullable=True)
    op.alter_column("bills", "bill_status", type_=sa.Text(), existing_type=sa.String(128))


def downgrade() -> None:
    op.alter_column("bills", "bill_status", type_=sa.String(128), existing_type=sa.Text())
    op.alter_column("bills", "bill_org", type_=sa.String(256), existing_type=sa.Text(), existing_nullable=True)
    op.alter_column("bills", "bill_no", type_=sa.String(128), existing_type=sa.Text())
    op.alter_column("bills", "bill_uid", type_=sa.String(512), existing_type=sa.Text())
