"""Clean up duplicate "current" rows and enforce uniqueness at the DB level.

Every bi-temporal table should have at most one row per natural key with
superseded_at IS NULL AND valid_to IS NULL ("the current row"). Before the
scrapers had per-term filtering and the correct data.ly.gov.tw endpoint,
some scrape runs wrote conflicting rows under the same natural key without
ever superseding the older one, leaving two or more "current" rows for the
same key. Application code that expects exactly one ("scalar_one_or_none")
then raises sqlalchemy.exc.MultipleResultsFound on any later upsert of that
key.

This migration:
1. For every affected natural key, keeps the most-recently-recorded row as
   current and supersedes the rest (data fix).
2. Replaces each table's non-unique "current" index with a unique partial
   index, so this class of duplicate can never be written again.

Revision ID: 0009_dedupe_current_rows
Revises: 0008_trgm_indexes
Create Date: 2026-06-28

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_dedupe_current_rows"
down_revision: str | None = "0008_trgm_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, natural key column, old non-unique index name)
_TABLES = [
    ("legislators", "legislator_uid", "ix_legislators_current"),
    ("attendance", "attendance_uid", "ix_attendance_current"),
    ("votes", "vote_uid", "ix_votes_current"),
    ("bills", "bill_uid", "ix_bills_current"),
    ("interpellations", "interp_uid", "ix_interps_current"),
    ("committee_memberships", "committee_uid", "ix_committees_current"),
    ("activity_reports", "activity_uid", "ix_activity_current"),
]


def _dedupe_sql(table: str, uid_col: str) -> str:
    return f"""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY {uid_col}
                       ORDER BY recorded_at DESC, id DESC
                   ) AS rn
            FROM {table}
            WHERE superseded_at IS NULL AND valid_to IS NULL
        )
        UPDATE {table}
        SET superseded_at = now()
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """


def upgrade() -> None:
    for table, uid_col, old_index in _TABLES:
        op.execute(_dedupe_sql(table, uid_col))
        op.drop_index(old_index, table_name=table)
        op.create_index(
            f"ux_{table}_{uid_col}_current",
            table,
            [uid_col],
            unique=True,
            postgresql_where="superseded_at IS NULL AND valid_to IS NULL",
        )


def downgrade() -> None:
    for table, uid_col, old_index in _TABLES:
        op.drop_index(f"ux_{table}_{uid_col}_current", table_name=table)
        op.create_index(
            old_index,
            table,
            [uid_col],
            postgresql_where="superseded_at IS NULL",
        )
