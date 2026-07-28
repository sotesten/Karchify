"""Seed <count> realistic expenses for a given user across the last <months> months.

Reads DB path from database/db.py (no hardcoded filename) and uses a single
transaction with parameterised queries.
"""

import argparse
import os
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

# Make `database/` importable so we can reuse its path resolver.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import _resolve_db_path  # noqa: E402


# (label_for_log, amount_min, amount_max, descriptions, weight)
# Weights are relative — Food is the most common, Health/Bills the least,
# within the four categories the schema CHECK constraint actually allows.
CATEGORIES = [
    (
        "Food",
        50, 800,
        [
            "Chai and samosa",
            "Lunch thali",
            "Dinner at restaurant",
            "Groceries — weekly",
            "Idli sambhar breakfast",
            "Biryani takeout",
            "Street food — pav bhaji",
            "Coffee and biscuits",
            "Dosa and chutney",
            "Sunday family lunch",
        ],
        4,
    ),
    (
        "Transport",
        20, 500,
        [
            "Auto rickshaw to office",
            "Metro pass top-up",
            "Ola ride to airport",
            "Petrol refill",
            "Cab to railway station",
            "Bus ticket",
            "Two-wheeler service",
        ],
        3,
    ),
    (
        "Bills",
        200, 3000,
        [
            "Electricity bill",
            "Internet recharge",
            "Mobile postpaid bill",
            "Gas cylinder refill",
            "DTH recharge",
            "Water bill",
        ],
        1,
    ),
    (
        "Health",
        100, 2000,
        [
            "Pharmacy — medicines",
            "Doctor consultation",
            "Gym membership",
            "Lab tests",
            "Dental checkup",
            "Health supplements",
        ],
        1,
    ),
]


def weighted_pick(rng: random.Random):
    pool = []
    for cat, lo, hi, descs, w in CATEGORIES:
        pool.extend([(cat, lo, hi, d) for d in descs for _ in range(w)])
    return rng.choice(pool)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", type=int)
    parser.add_argument("count", type=int)
    parser.add_argument("months", type=int)
    args = parser.parse_args()

    if args.user_id <= 0 or args.count <= 0 or args.months <= 0:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        return 1

    db_path = _resolve_db_path()
    # Allow override via env (same precedence as db.py uses internally).
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    user = conn.execute(
        "SELECT id FROM users WHERE id = ?", (args.user_id,)
    ).fetchone()
    if user is None:
        print(f"No user found with id {args.user_id}.")
        conn.close()
        return 1

    today = date.today()
    # Inclusive window: first day of the (today - months) month → today.
    start = (today.replace(day=1) - timedelta(days=0))
    # Walk back `months` months by stepping from the 1st of this month.
    year, month = today.year, today.month
    for _ in range(args.months - 1):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    start = date(year, month, 1)
    span_days = (today - start).days

    rng = random.Random()
    rows = []
    for _ in range(args.count):
        cat, lo, hi, desc = weighted_pick(rng)
        amount = round(rng.uniform(lo, hi), 2)
        days_offset = rng.randint(0, span_days)
        d = (start + timedelta(days=days_offset)).isoformat()
        rows.append((args.user_id, amount, cat, d, desc))

    try:
        conn.execute("BEGIN")
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Insert failed, transaction rolled back: {e}")
        conn.close()
        return 1

    # ---- confirmation ----
    # Use the first id from this batch onward so we report *just* the rows
    # we inserted, not pre-existing ones for the same user.
    first_id = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? AND id >= last_insert_rowid() - ? + 1 "
        "ORDER BY id ASC LIMIT 1",
        (args.user_id, args.count),
    ).fetchone()
    # Simpler & reliable: query by rowid range using last_insert_rowid().
    last_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    first_id = last_id - args.count + 1
    inserted_only_now = conn.execute(
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE id BETWEEN ? AND ? ORDER BY date DESC",
        (first_id, last_id),
    ).fetchall()
    dates = [r["date"] for r in inserted_only_now]
    sample = inserted_only_now[:5]

    print(f"Inserted {len(inserted_only_now)} expenses for user {args.user_id}.")
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)} (span: {span_days + 1} days)")
    print("Sample (newest 5):")
    for r in sample:
        print(
            f"  id={r['id']:>4}  {r['date']}  Rs.{r['amount']:>8.2f}  "
            f"{r['category']:<10}  {r['description']}"
        )

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
