"""Idempotent demo data for PaisaFlow.

seed_db() inserts one demo user (demo@demo.com / demo1234) plus 8 sample
expenses across the four landing-page categories. Safe to call repeatedly:
it early-returns once the demo user exists.
"""

from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from .db import get_db


DEMO_USER = {
    "name":     "Demo User",
    "email":    "demo@demo.com",
    "password": "demo1234",
}


def seed_db() -> None:
    """Insert demo user + 8 sample expenses. Safe to call repeatedly."""
    db = get_db()

    # ---- idempotency guard ----
    if db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE email = ?",
        (DEMO_USER["email"],),
    ).fetchone()["n"]:
        return

    # ---- demo user ----
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (
            DEMO_USER["name"],
            DEMO_USER["email"],
            generate_password_hash(DEMO_USER["password"]),
        ),
    )
    db.commit()

    user_id = db.execute(
        "SELECT id FROM users WHERE email = ?",
        (DEMO_USER["email"],),
    ).fetchone()["id"]

    # ---- sample expenses over the last ~30 days ----
    today = date.today()
    samples = [
        # (days_ago, amount, category,    description)
        (1,   4500.00, "Bills",     "Electricity bill"),
        (3,    320.00, "Food",      "Groceries — weekly"),
        (5,    180.00, "Transport", "Metro pass top-up"),
        (7,    950.00, "Health",    "Pharmacy + checkup"),
        (10,  1200.00, "Food",      "Dinner with family"),
        (14,   780.00, "Bills",     "Internet recharge"),
        (20,   220.00, "Transport", "Cab to airport"),
        (28,   450.00, "Health",    "Gym membership"),
    ]
    for days_ago, amount, category, description in samples:
        d = (today - timedelta(days=days_ago)).isoformat()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, d, description),
        )
    db.commit()
