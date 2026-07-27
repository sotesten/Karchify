"""Session + login helpers for PaisaFlow.

Provides:
    login_user(user_id)       — store the logged-in user's id in the session.
    logout_user()             — clear the session.
    current_user()            — fetch the logged-in user row (or None).
    login_required(view)      — decorator: 401-style redirect to /login otherwise.

Sessions rely on a configured SECRET_KEY (see app.py).
"""

from functools import wraps

from flask import g, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from .db import get_db


SESSION_KEY = "user_id"


def login_user(user_id: int) -> None:
    session[SESSION_KEY] = user_id


def logout_user() -> None:
    session.pop(SESSION_KEY, None)
    g.pop("current_user", None)


def current_user():
    """Return the logged-in user row (as sqlite3.Row), or None."""
    if "current_user" in g:
        return g.current_user

    user_id = session.get(SESSION_KEY)
    if user_id is None:
        return None

    g.current_user = get_db().execute(
        "SELECT id, name, email, password_hash FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return g.current_user


def login_required(view):
    """Decorator: redirect anonymous requests to /login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def verify_password(user_row, password: str) -> bool:
    """True iff password matches the user's stored hash."""
    if user_row is None:
        return False
    return check_password_hash(user_row["password_hash"], password)