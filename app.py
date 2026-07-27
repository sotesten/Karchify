"""PaisaFlow — Flask app entry point.

Routes use the GET/POST split: GET renders the form, POST processes the
submission. All DB access goes through database.get_db() so every query
shares the same per-request connection.
"""

import os
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database import (current_user, get_db, init_app as init_db_app,
                      init_db, login_required, login_user, logout_user,
                      seed_db)

app = Flask(__name__)
# SECRET_KEY is required for session cookies. In production, override via env.
app.config["SECRET_KEY"] = os.environ.get("PAISAFLOW_SECRET", "dev-secret-change-me")

init_db_app(app)  # registers close_db teardown + `flask init-db` CLI


# ------------------------------------------------------------------ #
# Public pages                                                        #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Auth: /register /login /logout                                      #
# ------------------------------------------------------------------ #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = (request.form.get("name")     or "").strip()
        email    = (request.form.get("email")    or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            db.commit()
        except Exception:  # sqlite3.IntegrityError on duplicate email
            db.rollback()
            return render_template("register.html", error="An account with that email already exists.")

        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        login_user(user["id"])
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = (request.form.get("email")    or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        user = get_db().execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()

        from database.auth import verify_password  # local import to avoid cycle in tests
        if not user or not verify_password(user, password):
            return render_template("login.html", error="Invalid email or password.")

        login_user(user["id"])
        nxt = request.args.get("next")
        return redirect(nxt or url_for("profile"))

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Profile                                                             #
# ------------------------------------------------------------------ #

@app.route("/profile")
@login_required
def profile():
    user = current_user()
    db = get_db()
    totals_row = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
        "FROM expenses WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    by_cat = db.execute(
        "SELECT category, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY category",
        (user["id"],),
    ).fetchall()

    return _render_simple_profile(user, totals_row, by_cat)


def _render_simple_profile(user, totals_row, by_cat):
    """Fallback HTML if no profile.html template exists yet."""
    rows = "\n".join(
        f"<tr><td>{r['category']}</td><td>{r['total']:.2f}</td><td>{r['n']}</td></tr>"
        for r in by_cat
    )
    return (
        f"<!doctype html><meta charset=utf-8>"
        f"<title>Profile · {user['name']}</title>"
        f"<h1>{user['name']} ({user['email']})</h1>"
        f"<p>Total spent: {totals_row['total']:.2f} across {totals_row['n']} expenses</p>"
        f"<table border=1 cellpadding=6><tr><th>Category</th><th>Total</th><th>Count</th></tr>{rows}</table>"
        f"<p><a href=/expenses/add>Add expense</a> · "
        f"<a href=/logout>Sign out</a></p>"
    )


# ------------------------------------------------------------------ #
# Expenses CRUD                                                       #
# ------------------------------------------------------------------ #

CATEGORIES = ("Bills", "Food", "Health", "Transport")


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        return _upsert_expense(None, request.form, current_user()["id"])

    return _render_expense_form(None, request.args, today=date.today().isoformat())


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = _owned_expense_or_404(id, current_user()["id"])
    if expense is None:
        return ("Not found", 404)

    if request.method == "POST":
        return _upsert_expense(id, request.form, current_user()["id"])

    return _render_expense_form(expense, request.args)


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete_expense(id):
    expense = _owned_expense_or_404(id, current_user()["id"])
    if expense is None:
        return ("Not found", 404)

    if request.method == "POST":
        get_db().execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (id, current_user()["id"]))
        get_db().commit()
        return redirect(url_for("profile"))

    # GET: confirm-and-submit form (HTML built inline — no template needed)
    return (
        f"<!doctype html><meta charset=utf-8>"
        f"<title>Delete expense #{id}</title>"
        f"<h1>Delete expense #{id}?</h1>"
        f"<p><b>{expense['category']}</b> · ₹{expense['amount']:.2f} · {expense['date']} · {expense['description'] or ''}</p>"
        f"<form method=POST action=/expenses/{id}/delete>"
        f"<button type=submit>Yes, delete</button> "
        f"<a href=/profile>Cancel</a></form>"
    )


# ------- CRUD helpers ------------------------------------------------ #

def _owned_expense_or_404(expense_id: int, user_id: int):
    """Return the expense row if it belongs to user_id, else None."""
    row = get_db().execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    return row


def _upsert_expense(expense_id, form, user_id):
    """Insert (if expense_id is None) or update an expense; redirect on success."""
    amount      = (form.get("amount") or "").strip()
    category    = (form.get("category") or "").strip()
    date_str    = (form.get("date") or "").strip()
    description = (form.get("description") or "").strip()

    error = _validate_expense(amount, category, date_str, CATEGORIES)
    if error:
        return _render_expense_form(
            {"id": expense_id, "amount": amount, "category": category,
             "date": date_str, "description": description},
            error=error,
        )

    db = get_db()
    if expense_id is None:
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, float(amount), category, date_str, description or None),
        )
    else:
        db.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (float(amount), category, date_str, description or None,
             expense_id, user_id),
        )
    db.commit()
    return redirect(url_for("profile"))


def _validate_expense(amount, category, date_str, categories):
    if not amount:
        return "Amount is required."
    try:
        v = float(amount)
    except ValueError:
        return "Amount must be a number."
    if v < 0:
        return "Amount cannot be negative."
    if category not in categories:
        return "Pick a valid category."
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "Date must be YYYY-MM-DD."
    return None


def _render_expense_form(expense, *args, **kwargs):
    """Inline expense form (HTML). amount / category / date / description.

    Pass expense=None for the "add" case; existing-row dict for "edit".
    """
    error = kwargs.get("error")
    predef = kwargs.get("today", date.today().isoformat())
    e = expense or {}
    cats_html = "".join(
        f'<option value="{c}" {"selected" if c == e.get("category") else ""}>{c}</option>'
        for c in CATEGORIES
    )
    title = "Add expense" if expense is None else f"Edit expense #{e.get('id', '')}"
    err_html = f'<p style="color:#d62828"><b>{error}</b></p>' if error else ""
    action = "/expenses/add" if expense is None else f"/expenses/{e.get('id')}/edit"
    return (
        f"<!doctype html><meta charset=utf-8><title>{title}</title>"
        f"<h1>{title}</h1>"
        f"{err_html}"
        f'<form method=POST action="{action}">'
        f'<p><label>Amount <input name=amount value="{e.get("amount", "")}"></label></p>'
        f'<p><label>Category <select name=category>{cats_html}</select></label></p>'
        f'<p><label>Date <input name=date type=date value="{e.get("date", predef)}"></label></p>'
        f'<p><label>Description <input name=description value="{e.get("description", "") or ""}"></label></p>'
        f'<p><button type=submit>Save</button> '
        f'<a href=/profile>Cancel</a></p>'
        f"</form>"
    )


# ------------------------------------------------------------------ #
# Entrypoint                                                           #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    # CREATE TABLE IF NOT EXISTS — safe every run; idempotent seed via count-guard.
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
