-- PaisaFlow schema — Step 1: Database Setup
-- Idempotent: safe to run on every startup.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL CHECK (amount >= 0),
    category    TEXT    NOT NULL CHECK (category IN ('Bills', 'Food', 'Health', 'Transport')),
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
    ON expenses (user_id, date);
