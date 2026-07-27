"""Database connection lifecycle for PaisaFlow.

Public API:
    get_db()   — returns a per-request SQLite connection with row_factory
                 and foreign-key enforcement enabled.
    close_db() — teardown helper that closes the connection on app context exit.
    init_db()  — executes database/schema.sql (idempotent via IF NOT EXISTS).
    seed_db()  — see database/seed.py; re-exported here for convenience.
    init_app(app) — wire teardown + `flask init-db` CLI into a Flask app.
"""

import os
import sqlite3
from pathlib import Path

import click
from flask import current_app, g


# Resolve paths relative to the project root (where `python app.py` runs),
# not Flask's instance folder, so the DB lives at ./paisaflow.db.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = _PROJECT_ROOT / "paisaflow.db"


def _resolve_db_path() -> Path:
    """Return the SQLite file path.

    Precedence:
      1. PAISAFLOW_DB env var (lets tests point at a tmp file).
      2. ./paisaflow.db in the project root.
    """
    env = os.environ.get("PAISAFLOW_DB")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection cached on flask.g."""
    if "db" not in g:
        conn = sqlite3.connect(_resolve_db_path())
        conn.row_factory = sqlite3.Row
        # FK enforcement must be enabled per connection — SQLite default is OFF.
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(exception=None) -> None:
    """Close the connection at end of request / app context."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create all tables from schema.sql. Idempotent (IF NOT EXISTS)."""
    db = get_db()
    schema_path = Path(current_app.root_path, "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()


@click.command("init-db")
def init_db_command() -> None:
    """CLI: `flask init-db` creates tables."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app) -> None:
    """Wire teardown + CLI into the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
