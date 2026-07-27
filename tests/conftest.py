"""Test fixtures for PaisaFlow.

The `app` fixture points the database at a per-test tmp file via the
PAISAFLOW_DB env var, so every test gets a fresh, isolated SQLite DB.
"""

import pytest

from app import app as flask_app
from database import init_app as init_db_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PAISAFLOW_DB", str(tmp_path / "test.db"))
    flask_app.config.update(TESTING=True)
    init_db_app(flask_app)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()