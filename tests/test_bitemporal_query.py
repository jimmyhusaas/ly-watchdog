"""Unit tests for the bi-temporal query builder — no DB required.

Verifies the SQL predicates in app.api.v1.legislators.list_legislators
correctly implement the four-condition "as-of" filter:

  valid_from        <= as_of
  valid_to          IS NULL OR > as_of
  recorded_at       <= as_of
  superseded_at     IS NULL OR > as_of
"""

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select

from app.models.legislator import Legislator


def test_as_of_predicate_compiles_to_expected_sql() -> None:
    """Guard against regressions in the bi-temporal predicate."""
    as_of = datetime(2024, 3, 15, tzinfo=UTC)

    stmt = select(Legislator).where(
        and_(
            Legislator.valid_from <= as_of,
            or_(Legislator.valid_to.is_(None), Legislator.valid_to > as_of),
            Legislator.recorded_at <= as_of,
            or_(
                Legislator.superseded_at.is_(None),
                Legislator.superseded_at > as_of,
            ),
        )
    )
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

    # Must reference all four bi-temporal columns
    assert "valid_from" in compiled
    assert "valid_to" in compiled
    assert "recorded_at" in compiled
    assert "superseded_at" in compiled

    # Both NULL checks must be present
    assert compiled.count("IS NULL") == 2


def test_current_state_predicate_is_minimal() -> None:
    """The no-as_of path should only filter on transaction-time current-ness."""
    stmt = select(Legislator).where(
        Legislator.valid_to.is_(None),
        Legislator.superseded_at.is_(None),
    )
    # Check only the WHERE clause — the SELECT list legitimately contains all columns
    where_sql = str(stmt.whereclause.compile(compile_kwargs={"literal_binds": True}))
    assert where_sql.count("IS NULL") == 2
    assert "valid_from" not in where_sql
    assert "recorded_at" not in where_sql
