# Spec Document

## 1. Overview

Implement the complete SQLite database layer for **PaisaFlow** by replacing the existing database stub with a production-ready implementation.

This step establishes the **core persistence layer** of the application. Every future feature—including authentication, user profiles, expense management, analytics, budgeting, and reporting—depends on this database foundation.

The implementation must initialize the database automatically, enforce data integrity through constraints, and provide reusable helper functions for future development.

---

## 2. Depends on

Nothing — this is the first implementation step.

---

## 3. Routes

No new routes should be created.

All existing placeholder routes in `app.py` must remain unchanged.

Only the database layer should be implemented.

---

# 4. Database Schema

---

## A. `users`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | Primary key, autoincrement |
| name | TEXT | Not null |
| email | TEXT | Unique, not null |
| password_hash | TEXT | Not null |
| created_at | TEXT | Default `datetime('now')` |

---

## B. `expenses`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → `users.id`, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (`YYYY-MM-DD` format) |
| description | TEXT | Nullable |
| created_at | TEXT | Default `datetime('now')` |

---

## 5. Functions to Implement (`database/db.py`)

---

### A. `get_db()`

Responsibilities:

- Opens a connection to `paisaflow.db` in the project root.
- Creates the database automatically if it does not exist.
- Enables:

```python
conn.row_factory = sqlite3.Row
```

and

```sql
PRAGMA foreign_keys = ON;
```

Returns:

- Active SQLite connection.

---

### B. `init_db()`

Responsibilities:

- Creates the complete schema using:

```sql
CREATE TABLE IF NOT EXISTS
```

Creates:

- users
- expenses

Creates indexes if they do not already exist.

Safe to call multiple times.

Must never delete user data.

---

### C. `seed_db()`

Responsibilities:

Checks whether demo data already exists.

If demo user exists:

- Return immediately.
- Do not insert duplicate data.

Otherwise:

Create demo user:

| Field | Value |
|--------|-------|
| name | Demo User |
| email | demo@paisaflow.com |
| password | demo123 (hashed) |

Insert exactly **8 demo expenses**.

Requirements:

- All belong to demo user
- Cover multiple categories
- Dates spread across current month
- Realistic descriptions
- Positive amounts

---

## 6. Database Initialization

On application startup:

Import:

- get_db
- init_db
- seed_db

Inside:

```python
with app.app_context():
```

execute:

```python
init_db()
seed_db()
```

before any routes become active.

---

## 7. Files to Modify

### database/db.py

Implement:

- get_db()
- init_db()
- seed_db()

---

### app.py

Import database functions.

Initialize database during startup.

No other logic should change.

---

## 8. Files to Create

None.

---

## 9. Dependencies

No additional pip packages.

Only use:

- sqlite3
- werkzeug.security

---

## 10. Categories (Fixed Values)

Use exactly these values.

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

No additional categories should be inserted during seeding.

---

## 11. SQL Schema

### users

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### expenses

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);
```

---

### Index

```sql
CREATE INDEX IF NOT EXISTS idx_expenses_user_date
ON expenses(user_id, date);
```

---

## 12. Rules for Implementation

### Database

- SQLite only
- No ORM
- No SQLAlchemy

### Queries

Only parameterized queries.

Correct:

```python
cursor.execute(
    "INSERT INTO users(name,email) VALUES (?,?)",
    (name, email)
)
```

Never:

```python
f"INSERT INTO users VALUES ({name})"
```

---

### Foreign Keys

Every connection must execute:

```sql
PRAGMA foreign_keys = ON;
```

---

### Password Storage

Passwords must never be stored as plain text.

Use:

```python
from werkzeug.security import generate_password_hash
```

---

### Amount Storage

Store as:

```text
REAL
```

Never INTEGER.

---

### Dates

Always:

```text
YYYY-MM-DD
```

---

### Seed Rules

Seed exactly once.

Subsequent executions must insert nothing.

---

## 13. Expected Behavior

### get_db()

Returns:

- SQLite connection
- sqlite3.Row support
- Foreign keys enabled

---

### init_db()

Creates:

- users
- expenses
- indexes

Can run repeatedly without errors.

Never removes existing data.

---

### seed_db()

Creates:

- 1 demo user
- 8 demo expenses

Running multiple times never duplicates data.

---

### Database Constraints

Database must enforce:

- UNIQUE email
- NOT NULL columns
- Foreign keys
- Cascading delete
- Primary keys
- Autoincrement IDs

---

## 14. Error Handling

The database should naturally raise SQLite exceptions for invalid operations.

Examples:

Duplicate email

```
sqlite3.IntegrityError
```

Invalid foreign key

```
sqlite3.IntegrityError
```

Malformed SQL

```
sqlite3.OperationalError
```

Application code should not silently ignore database errors.

---

## 15. Verification Checklist

After implementation, verify:

### Database

- Database file (`paisaflow.db`) is automatically created.
- Only one database file is used by the application.
- Schema matches the specification exactly.
- Index exists.

---

### users Table

Contains:

- id
- name
- email
- password_hash
- created_at

Email uniqueness works.

Passwords are hashed.

---

### expenses Table

Contains:

- id
- user_id
- amount
- category
- date
- description
- created_at

Foreign keys are enforced.

---

### Seed Data

Contains:

- 1 demo user
- 8 demo expenses

No duplicate records after restarting the app.

---

### Application

App starts successfully.

Database initializes automatically.

No schema errors occur.

Existing placeholder routes continue to work unchanged.

---

## 16. Definition of Done

- [ ] `paisaflow.db` is created automatically
- [ ] Only one SQLite database file exists and is used
- [ ] `users` table matches the required schema
- [ ] `expenses` table matches the required schema
- [ ] Foreign key enforcement is enabled
- [ ] Demo user is inserted with hashed password
- [ ] Exactly 8 demo expenses are inserted
- [ ] Seed process is idempotent (no duplicates)
- [ ] All SQL uses parameterized queries
- [ ] Index `idx_expenses_user_date` exists
- [ ] Database initializes without errors
- [ ] Placeholder routes remain unchanged
- [ ] Ready for future authentication and expense management features
