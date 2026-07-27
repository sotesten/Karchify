"""Tests for the Step 1 database layer.

Covers:
    * init_db() is idempotent (CREATE TABLE IF NOT EXISTS).
    * get_db() exposes the sqlite3.Row factory.
    * Foreign keys are enabled on every new connection.
    * seed_db() inserts the expected demo user + 8 expenses.
    * seed_db() is idempotent across calls.
    * ON DELETE CASCADE removes expenses when the user is deleted.
"""

from werkzeug.security import check_password_hash

from database import get_db, init_db, seed_db
from database.seed import DEMO_USER


# --- init_db ------------------------------------------------------------

def test_init_db_is_idempotent(app):
    init_db()
    init_db()  # second call must not raise
    with app.app_context():
        rows = get_db().execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    assert [r["name"] for r in rows] == ["expenses", "users"]


# --- get_db / Row factory -----------------------------------------------

def test_get_db_returns_row_factory(app):
    with app.app_context():
        init_db()
        seed_db()
        row = get_db().execute(
            "SELECT email FROM users WHERE email = ?", (DEMO_USER["email"],)
        ).fetchone()
    # sqlite3.Row is dict-like AND indexable
    assert row["email"] == DEMO_USER["email"]
    assert row[0] == DEMO_USER["email"]


# --- foreign keys --------------------------------------------------------

def test_foreign_keys_enabled(app):
    with app.app_context():
        init_db()
        result = get_db().execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


# --- seed contents -------------------------------------------------------

def test_seed_db_inserts_demo_user_and_expenses(app):
    with app.app_context():
        init_db()
        seed_db()
        db = get_db()
        user = db.execute(
            "SELECT id, name, email, password_hash FROM users "
            "WHERE email = ?",
            (DEMO_USER["email"],),
        ).fetchone()
        assert user is not None
        assert user["name"] == DEMO_USER["name"]
        assert check_password_hash(user["password_hash"], DEMO_USER["password"])

        expenses = db.execute(
            "SELECT category FROM expenses WHERE user_id = ? ORDER BY date",
            (user["id"],),
        ).fetchall()

    assert len(expenses) == 8
    assert {e["category"] for e in expenses} == {"Bills", "Food", "Health", "Transport"}


def test_seed_db_is_idempotent(app):
    with app.app_context():
        init_db()
        seed_db()
        seed_db()
        n = get_db().execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        expenses = get_db().execute("SELECT COUNT(*) AS n FROM expenses").fetchone()["n"]
    assert n == 1
    assert expenses == 8


# --- cascade -------------------------------------------------------------

def test_cascade_delete_user_wipes_expenses(app):
    with app.app_context():
        init_db()
        seed_db()
        db = get_db()
        user_id = db.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_USER["email"],)
        ).fetchone()["id"]

        before = db.execute(
            "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]
        assert before == 8

        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()

        after = db.execute(
            "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]
    assert after == 0