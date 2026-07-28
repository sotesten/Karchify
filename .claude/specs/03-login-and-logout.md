# Spec: Login and Logout

## Overview
Login and Logout let an existing PaisaFlow user return to their account and
end their session. The feature exposes a public `/login` route that renders
a sign-in form on GET and verifies credentials on POST, plus a `/logout`
route that clears the session. On success the user lands on `/profile` (or
the safe `?next=` target they were sent from); on failure the form
re-renders with a single generic error so the message never leaks whether
the email exists. This is the third milestone in the roadmap and is the
companion to Step 2 (Registration): together they form the full
auth-on-the-edge layer that every later feature assumes.

## Depends on
- **Step 1 — Database setup** — the `users` table with `email UNIQUE` and
  `password_hash`, and the per-request connection helper (`get_db`).
- **Step 2 — Registration** — the session helpers (`login_user`,
  `logout_user`, `current_user`, `login_required`) in `database/auth.py`,
  the `verify_password` helper, and the `/register` flow that produces
  the `users` rows this feature reads.

## Routes
- `GET /login` — render the sign-in form — public
- `POST /login` — verify credentials, start a session, redirect to
  `?next=` or `/profile` — public
- `GET /logout` — show a confirmation page ("Sign out of PaisaFlow?")
  with a POST submit button — logged-in
- `POST /logout` — clear the session, redirect to `/` — logged-in

## Database changes
No database changes. This feature only reads the existing `users` table
created in Step 1.

## Templates
- **Modify:** `templates/login.html` — already exists; this spec freezes
  its structure. The template must:
  - Extend `base.html`.
  - Render `{{ error }}` inside `auth-card` when the route passes one.
  - Submit to `POST /login` with fields `email`, `password`.
  - Use CSS-variable-driven classes (no inline `style="color:#…"`).
  - Show a "Create one free" link to `/register` for users who don't
    have an account yet.
- **Create:** `templates/logout.html` — minimal page extending `base.html`
  with a confirmation form. Must contain:
  - A heading explaining the action ("Sign out?").
  - A `<form method="POST" action="/logout">` with a single submit
    button ("Yes, sign out") and a cancel link back to `/profile`.
  - Use CSS-variable-driven classes.

## Files to change
- `app.py` — the existing `/login` view is the implementation; the spec
  freezes its behaviour. The existing `/logout` view is rewritten: GET
  now renders `logout.html` instead of immediately clearing the session;
  POST clears the session and redirects to `/`. The `?next=` parameter
  is validated to refuse absolute / off-site URLs.

## Files to create
- `tests/test_auth.py` — extended (the file already exists from Step 2
  with register tests) with the login + logout cases listed below.

## New dependencies
No new dependencies. The view uses:
- `flask` — `render_template`, `redirect`, `request`, `url_for`
- `urllib.parse` — `urlparse` for `?next=` validation
- `database.get_db`, `database.login_user`, `database.logout_user` —
  already wired

## Rules for implementation
- **No SQLAlchemy or ORMs.** All persistence stays on raw `sqlite3`
  accessed through `get_db()`.
- **Parameterised queries only.** Every `SELECT` must use `?`
  placeholders. No f-strings, `.format()`, or `%` interpolation in SQL.
- **Passwords verified with werkzeug.** Use
  `database.auth.verify_password(user_row, password)` which calls
  `werkzeug.security.check_password_hash`. Never compare hashes with
  `==`; never decode or re-encode.
- **Generic credential-failure message.** Both "no such user" and
  "wrong password" return the exact same `error` string
  `"Invalid email or password."` so the page never reveals whether an
  email is registered.
- **Email normalisation on login.** Lowercase and strip whitespace on
  the submitted email before the `SELECT`, mirroring Step 2's
  registration rule. This is what makes a `Foo@Bar.com` registration
  reachable by typing `foo@bar.com` at sign-in.
- **`?next=` must be same-origin.** If `request.args.get("next")` is set
  and parses as an absolute URL whose netloc differs from the current
  request host, treat it as missing (fall through to `url_for("profile")`).
  Relative paths and `None` are accepted. The check uses
  `urllib.parse.urlparse` and compares `netloc` against
  `request.host`.
- **No flash messages.** Errors re-render `login.html` with an `error`
  string, the same way `register.html` does.
- **POST-only logout.** `GET /logout` must not clear the session — it
  renders a confirmation page instead. This blocks accidental sign-out
  via `<img src="/logout">` or prefetch. A logged-out user hitting
  `GET /logout` is redirected to `/login?next=/logout`.
- **Use CSS variables — never hardcode hex values.** All colours come
  from the design tokens declared in `static/css` (read via
  `var(--…)`). Inline `style="color:#…"` is forbidden in templates and
  inline HTML in `app.py`.
- **All templates extend `base.html`.** No standalone HTML files.
- **Reuse `login_required`.** `/logout` (both GET and POST) is wrapped
  with the existing `database.auth.login_required` decorator. An
  anonymous request to either method redirects to `/login?next=/logout`.

## Definition of done
- [ ] `GET /login` returns `200` and renders `templates/login.html`
      (extending `base.html`).
- [ ] `POST /login` with a valid email + matching password starts a
      session and redirects to `/profile` (status `302`).
- [ ] After a successful login, the session contains `user_id` and
      `GET /profile` returns `200`.
- [ ] `POST /login` with an unknown email returns `200` and renders
      `login.html` with `error = "Invalid email or password."`. No row
      is leaked via timing or message wording.
- [ ] `POST /login` with a known email and a wrong password returns
      `200` and renders the **same** `error` string as the unknown-email
      case. No row is leaked.
- [ ] Email matching is case-insensitive and whitespace-trimmed: a user
      registered as `Foo@Bar.com` can sign in as `  foo@bar.com  `.
- [ ] `POST /login` with `?next=/profile` redirects to `/profile`.
      `POST /login` with no `?next=` also redirects to `/profile`.
- [ ] `POST /login?next=https://evil.example.com/steal` does **not**
      redirect off-site; it falls through to `/profile`.
- [ ] `POST /login?next=//evil.example.com` does **not** redirect
      off-site; it falls through to `/profile`.
- [ ] `GET /logout` while logged in returns `200` and renders
      `templates/logout.html` (extending `base.html`). The session is
      **not** cleared by this request.
- [ ] `POST /logout` while logged in clears the session and redirects
      to `/` (status `302`).
- [ ] `GET /logout` while logged out redirects to `/login?next=/logout`
      (status `302`). The session stays empty.
- [ ] `POST /logout` while logged out redirects to
      `/login?next=/logout` (status `302`). The session stays empty.
- [ ] `templates/login.html` and `templates/logout.html` contain no
      inline `style="…#hex…"` colour declarations.
- [ ] `app.py` contains no SQL string interpolation in the `/login` or
      `/logout` handlers.
- [ ] `tests/test_auth.py` covers the success and failure paths for
      `/login` and `/logout` (including the two `?next=` rejection
      cases) and the suite passes.