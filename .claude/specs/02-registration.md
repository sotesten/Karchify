# Spec: Registration

## Overview
Registration gives new visitors a way to create a PaisaFlow account. The
feature exposes a public `/register` route that renders a sign-up form on
GET and creates a `users` row on POST. On success the user is signed in
and redirected to their profile, so the rest of the app (expenses,
analytics) is reachable immediately. This is the entry point of the
authenticated experience and the second milestone in the roadmap (step 1
was the database setup).

## Depends on
- **Step 1 — Database setup** — the `users` table (id, name, email,
  password_hash, created_at) and the per-request connection helper
  (`get_db`) must exist.

## Routes
- `GET /register` — render the sign-up form — public
- `POST /register` — create the user, start a session, redirect to
  `/profile` — public

## Database changes
No database changes. This feature writes to the existing `users` table
created in step 1; no new tables, columns, or constraints.

## Templates
- **Modify:** `templates/register.html` — already exists; this spec
  freezes its structure. The template must:
  - Extend `base.html`.
  - Render `{{ error }}` inside `auth-card` when the route passes one.
  - Submit to `POST /register` with fields `name`, `email`, `password`.
  - Use CSS-variable-driven classes (no inline `style="color:#…"`).
  - Show a "Sign in" link to `/login` for users who already have an
    account.

## Files to change
- `app.py` — the existing `/register` view is the implementation; the
  spec freezes its behaviour. No structural rewrites expected; if
  anything changes it must stay within the rules below.

## Files to create
None. The route, helper, and template already exist.

## New dependencies
No new dependencies. The view uses:
- `flask` — `render_template`, `redirect`, `request`, `url_for`
- `werkzeug.security` — `generate_password_hash`
- `database.get_db`, `database.login_user` — already wired

## Rules for implementation
- **No SQLAlchemy or ORMs.** All persistence stays on raw `sqlite3`
  accessed through `get_db()`.
- **Parameterised queries only.** Every `INSERT` / `SELECT` must use
  `?` placeholders. No f-strings, `.format()`, or `%` interpolation in
  SQL.
- **Passwords hashed with werkzeug.** Use
  `werkzeug.security.generate_password_hash`; never store the raw
  password. The matching `check_password_hash` lives in
  `database/auth.py` and is used by `/login`.
- **Use CSS variables — never hardcode hex values.** All colours come
  from the design tokens declared in `static/css` (read via
  `var(--…)`). Inline `style="color:#…"` is forbidden in templates and
  inline HTML in `app.py`.
- **All templates extend `base.html`.** No standalone HTML files.
- **Validate on the server.** Required fields, min password length of 8,
  and duplicate-email handling are server responsibilities — the form's
  `required` attribute is a UX nicety, not the gate.
- **Email normalisation.** Lowercase and strip whitespace on the email
  before insert and before the duplicate check; uniqueness is enforced
  at the DB layer (`UNIQUE` on `users.email`).
- **Auto-login after sign-up.** On successful insert, look up the
  new user's id, call `login_user(user_id)`, then `redirect` to
  `/profile`. No intermediate "you're registered" page.
- **Error surface.** Validation failures and duplicate-email errors
  re-render `register.html` with a short, human-readable `error`
  string. Do not flash; do not raise to the user.
- **No raw-HTML inline form in `app.py` for this route.** The
  register flow must use `register.html`, mirroring how `/login`
  delegates to `login.html`. Inline HTML is reserved for routes that
  do not yet have a template (see the existing inline expense
  form/delete confirmation).

## Definition of done
- [ ] `GET /register` returns `200` and renders
      `templates/register.html` (extending `base.html`).
- [ ] `POST /register` with valid `name`, `email`, `password` (≥8
      chars) inserts a row into `users` with a hashed password and
      redirects to `/profile` (status `302`).
- [ ] After a successful registration, the session contains
      `user_id` and `GET /profile` returns `200`.
- [ ] Submitting with any empty field re-renders the form with
      `error = "All fields are required."` and does not insert a row.
- [ ] Submitting with a password shorter than 8 characters re-renders
      the form with `error = "Password must be at least 8 characters."`
      and does not insert a row.
- [ ] Submitting with an email that already exists re-renders the
      form with `error = "An account with that email already exists."`
      and does not insert a duplicate row.
- [ ] The stored `password_hash` is a werkzeug hash (starts with
      `pbkdf2:` / `scrypt:`), never plaintext.
- [ ] No SQL string interpolation appears in `app.py` for the
      `/register` handler.
- [ ] `register.html` contains no inline `style="…#hex…"` colour
      declarations.
- [ ] An existing test (`tests/test_auth.py` or equivalent) covers
      the success and failure paths and passes.
