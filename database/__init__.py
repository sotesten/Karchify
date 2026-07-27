"""PaisaFlow database package.

Re-exports the connection-lifecycle helpers, seeder, and auth helpers so
callers can write:
    from database import get_db, init_db, seed_db, init_app
    from database import login_user, logout_user, current_user, login_required
"""

from .auth import (current_user, login_required, login_user, logout_user,
                   verify_password)
from .db import close_db, get_db, init_app, init_db
from .seed import seed_db

__all__ = [
    "get_db",
    "init_db",
    "seed_db",
    "init_app",
    "close_db",
    "login_user",
    "logout_user",
    "current_user",
    "login_required",
    "verify_password",
]
