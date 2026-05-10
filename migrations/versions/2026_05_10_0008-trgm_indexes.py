"""Enable pg_trgm and add GIN indexes for fast Chinese text search.

pg_trgm splits strings into 3-character n-grams and builds a GIN index,
turning O(n) sequential ILIKE '%keyword%' scans into O(log n) index lookups.
Works well for CJK text since each character is its own "trigram unit".

Revision ID: 0008_trgm_indexes
Revises: 0007_activity_reports
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_trgm_indexes"
down_revision: str | None = "0007_activity_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Bills: name + proposer keyword search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bills_name_trgm "
        "ON bills USING GIN (bill_name gin_trgm_ops) "
        "WHERE superseded_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bills_proposer_trgm "
        "ON bills USING GIN (bill_proposer gin_trgm_ops) "
        "WHERE superseded_at IS NULL AND bill_proposer IS NOT NULL"
    )

    # Interpellations: speech content keyword search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_interps_content_trgm "
        "ON interpellations USING GIN (interp_content gin_trgm_ops) "
        "WHERE superseded_at IS NULL"
    )

    # Activity reports: content keyword search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_activity_content_trgm "
        "ON activity_reports USING GIN (content gin_trgm_ops) "
        "WHERE superseded_at IS NULL"
    )

    # Legislators: name search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_legislators_name_trgm "
        "ON legislators USING GIN (name gin_trgm_ops) "
        "WHERE superseded_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_legislators_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_activity_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_interps_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_bills_proposer_trgm")
    op.execute("DROP INDEX IF EXISTS ix_bills_name_trgm")
