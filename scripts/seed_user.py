"""Seed a single dummy user into PaisaFlow's users table.

Mirrors the get_db() pattern from database/db.py: opens a per-request
SQLite connection inside a Flask app context, enables FK enforcement,
and reuses the same connection lifecycle the rest of the app uses.

Run from the project root:
    python -m scripts.seed_user
"""

from __future__ import annotations

import random
import re
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project root is on sys.path so `from database import ...` works
# regardless of where the script is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from database import close_db, get_db, init_db  # noqa: E402


# Realistic Indian first + last names across regions. Picked to feel
# authentic without leaning on any single region.
_FIRST_NAMES = [
    # North
    "Aarav", "Vihaan", "Aditya", "Arjun", "Rohan", "Ishaan", "Karan", "Rahul",
    "Priya", "Ananya", "Neha", "Pooja", "Sneha", "Kavya", "Riya", "Meera",
    # South
    "Arjun", "Karthik", "Vikram", "Rohit", "Sandeep", "Anjali", "Divya", "Lakshmi",
    "Kavitha", "Sneha", "Manoj", "Pranav",
    # West
    "Harsh", "Yash", "Dev", "Jay", "Krishna", "Tejas", "Aisha", "Tanvi", "Rutuja",
    # East + North-East
    "Suman", "Rakesh", "Bikram", "Ankit", "Pallavi", "Sushmita", "Rohit",
    # Common unisex / pan-India
    "Sanjay", "Manoj", "Naveen", "Sandeep", "Suresh",
]

_LAST_NAMES = [
    # North
    "Sharma", "Verma", "Gupta", "Agarwal", "Mishra", "Pandey", "Saxena", "Sinha",
    "Kumar", "Singh", "Yadav", "Patel",
    # South
    "Iyer", "Menon", "Nair", "Pillai", "Rao", "Reddy", "Naidu", "Krishnan",
    "Subramanian", "Bhat", "Kamath", "Hegde",
    # West
    "Patel", "Shah", "Desai", "Joshi", "Mehta", "Modi", "Trivedi", "Bhatt",
    # East
    "Banerjee", "Mukherjee", "Chatterjee", "Das", "Ghosh", "Bose", "Dutta",
    "Mahapatra", "Mohanty", "Sahoo",
    # Sikh / Punjabi
    "Kaur", "Gill", "Sandhu", "Dhillon", "Bedi", "Sodhi",
]


def _slugify(name: str) -> str:
    """Lowercase, ASCII-fold, strip non-alphanumerics. Used for the email local-part."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _random_email(first: str, last: str) -> str:
    local = f"{_slugify(first)}.{_slugify(last)}"
    suffix = random.randint(10, 999)  # 2-3 digit number
    return f"{local}{suffix}@gmail.com"


def _random_name() -> tuple[str, str]:
    first = random.choice(_FIRST_NAMES)
    last = random.choice(_LAST_NAMES)
    return first, last


def _email_exists(db, email: str) -> bool:
    row = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE email = ?", (email,)
    ).fetchone()
    return bool(row["n"])


def _generate_unique_email(db) -> tuple[str, str, str]:
    """Generate a name + email, retrying until the email is free in the DB."""
    for _ in range(50):  # generous cap; collisions are rare
        first, last = _random_name()
        email = _random_email(first, last)
        if not _email_exists(db, email):
            return first, last, email
    raise RuntimeError("Could not find a unique email after 50 attempts")


def main() -> int:
    # Minimal Flask app so get_db() can stash the connection on `g`, exactly
    # like the real request lifecycle does. We point root_path at the project
    # root (not scripts/) so init_db() resolves database/schema.sql correctly.
    app = Flask(__name__)
    app.root_path = str(_PROJECT_ROOT)
    with app.app_context():
        # Make sure the schema exists (no-op if it's already there).
        init_db()

        db = get_db()
        first, last, email = _generate_unique_email(db)

        name = f"{first} {last}"
        password_hash = generate_password_hash("password123")
        now = datetime.now().isoformat(sep=" ", timespec="seconds")

        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, email, password_hash, now),
        )
        db.commit()
        new_id = cur.lastrowid

        print("Inserted user:")
        print(f"  id    : {new_id}")
        print(f"  name  : {name}")
        print(f"  email : {email}")

        # Mirror close_db() teardown so the connection is released cleanly.
        close_db()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
