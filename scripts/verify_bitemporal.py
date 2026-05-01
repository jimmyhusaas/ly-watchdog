"""
Bi-temporal verification script.

Inserts controlled test data directly into postgres, then hits the API
to verify all query paths:
  1. Current state  (no as_of)
  2. Point-in-time  (as_of=T1, T2, T3)
  3. Filters        (term, party)

Usage:
    python scripts/verify_bitemporal.py
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

import psycopg2

# ── connection ────────────────────────────────────────────────────────────────
DB = {
    "host": "localhost",
    "port": 5432,
    "dbname": "ly_watchdog",
    "user": "watchdog",
    "password": "watchdog_dev",
}
API = "http://localhost:8000"

# ── time anchors ──────────────────────────────────────────────────────────────
T1 = datetime(2024, 1, 1, tzinfo=UTC)  # 第一筆資料生效
T2 = datetime(2024, 6, 1, tzinfo=UTC)  # 換黨後新資料記錄
T3 = datetime(2025, 1, 1, tzinfo=UTC)  # 立委離任

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

errors: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS} {label}")
    else:
        msg = f"{label}" + (f": {detail}" if detail else "")
        print(f"  {FAIL} {msg}")
        errors.append(msg)


def api_get(path: str) -> list[dict]:
    url = API + path
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {url}: {body}") from e


# ── setup ─────────────────────────────────────────────────────────────────────
def seed(cur) -> None:
    cur.execute("DELETE FROM legislators")

    rows = [
        # uid        name   district party  term  valid_from  valid_to    recorded_at  superseded_at
        # Legislator A: joined T1, changed party at T2 (old row superseded)
        (
            "A001",
            "王大明",
            "台北一",
            "民主進步黨",
            11,
            T1,
            None,
            T1,
            T2,
        ),  # old record, superseded at T2
        (
            "A001",
            "王大明",
            "台北一",
            "台灣民眾黨",
            11,
            T1,
            None,
            T2,
            None,
        ),  # current record after party change
        # Legislator B: joined T1, resigned at T3
        (
            "B002",
            "李小花",
            "高雄三",
            "中國國民黨",
            11,
            T1,
            T3,
            T1,
            None,
        ),  # valid_to = T3 (resigned), still current knowledge
        # Legislator C: 10th term, current
        ("C003", "陳志遠", "不分區", "民主進步黨", 10, T1, None, T1, None),
    ]

    cur.executemany(
        """
        INSERT INTO legislators
          (id, legislator_uid, name, district, party, term,
           raw_data, valid_from, valid_to, recorded_at, superseded_at)
        VALUES
          (gen_random_uuid(), %s, %s, %s, %s, %s,
           '{}', %s, %s, %s, %s)
        """,
        rows,
    )


# ── tests ─────────────────────────────────────────────────────────────────────
def test_health() -> None:
    print("\n[1] Health check")
    data = api_get("/health")
    check("status == ok", data.get("status") == "ok", str(data))


def test_current_state() -> None:
    print("\n[2] Current state (no as_of)")
    data = api_get("/v1/legislators")
    uids = {r["legislator_uid"] for r in data}

    # B002 resigned (valid_to=2025-01-01), so only 2 active records
    check("returns 2 rows", len(data) == 2, f"got {len(data)}: {uids}")
    check("A001 present", "A001" in uids)
    check("B002 NOT present (resigned)", "B002" not in uids)
    check("C003 present", "C003" in uids)

    # A001 must have the NEW party
    a001 = next((r for r in data if r["legislator_uid"] == "A001"), None)
    check("A001 party is 台灣民眾黨", a001 is not None and a001["party"] == "台灣民眾黨", str(a001))


def test_as_of_before_party_change() -> None:
    """As-of T1+1day — A001 should still have old party."""
    print("\n[3] as_of = 2024-01-15 (before party change)")
    ts = "2024-01-15T00:00:00Z"
    data = api_get(f"/v1/legislators?as_of={ts}")
    uids = {r["legislator_uid"] for r in data}

    check("A001 present", "A001" in uids)
    check("B002 present", "B002" in uids)
    check("C003 present", "C003" in uids)

    a001 = next((r for r in data if r["legislator_uid"] == "A001"), None)
    check("A001 party is 民主進步黨", a001 is not None and a001["party"] == "民主進步黨", str(a001))


def test_as_of_after_party_change() -> None:
    """As-of T2+1day — A001 should have new party."""
    print("\n[4] as_of = 2024-06-15 (after party change)")
    ts = "2024-06-15T00:00:00Z"
    data = api_get(f"/v1/legislators?as_of={ts}")
    uids = {r["legislator_uid"] for r in data}

    a001 = next((r for r in data if r["legislator_uid"] == "A001"), None)
    check("A001 party is 台灣民眾黨", a001 is not None and a001["party"] == "台灣民眾黨", str(a001))
    check("B002 still present (not resigned yet)", "B002" in uids)


def test_as_of_after_resignation() -> None:
    """As-of T3+1day — B002 (resigned at T3) should be gone."""
    print("\n[5] as_of = 2025-01-15 (after B002 resignation)")
    ts = "2025-01-15T00:00:00Z"
    data = api_get(f"/v1/legislators?as_of={ts}")
    uids = {r["legislator_uid"] for r in data}

    check("B002 NOT present (resigned)", "B002" not in uids, f"uids={uids}")
    check("A001 still present", "A001" in uids)


def test_filter_term() -> None:
    print("\n[6] Filter ?term=10")
    data = api_get("/v1/legislators?term=10")
    check(
        "only C003 returned",
        len(data) == 1 and data[0]["legislator_uid"] == "C003",
        str([r["legislator_uid"] for r in data]),
    )


def test_filter_party() -> None:
    print("\n[7] Filter ?party=中國國民黨 (as_of when B002 was active)")
    ts = "2024-06-15T00:00:00Z"
    data = api_get(
        f"/v1/legislators?party=%E4%B8%AD%E5%9C%8B%E5%9C%8B%E6%B0%91%E9%BB%A8&as_of={ts}"
    )
    check(
        "only B002 returned",
        len(data) == 1 and data[0]["legislator_uid"] == "B002",
        str([r["legislator_uid"] for r in data]),
    )


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Connecting to postgres …")
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor()

    print("Seeding test data …")
    seed(cur)
    cur.close()
    conn.close()

    test_health()
    test_current_state()
    test_as_of_before_party_change()
    test_as_of_after_party_change()
    test_as_of_after_resignation()
    test_filter_term()
    test_filter_party()

    print()
    if errors:
        print(f"\033[31mFAILED ({len(errors)} error(s)):\033[0m")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\033[32mAll checks passed.\033[0m")


if __name__ == "__main__":
    main()
