"""
SQLite-backed task state for the data-collection pipeline.

One row per (con_id, window_end_date, quote_type) — i.e. one row per IB
reqHistoricalData call we intend to make. Replaces data/status/todo.csv.

Status values:
    pending   — needs to be pulled
    done      — bars written to disk
    no_data   — IB returned no data (error 162 or empty result). Never retry.
    error     — transient failure (pacing/disconnect). Will retry on next run.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

import common.ol_const as olc


SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
    con_id           INTEGER NOT NULL,
    local_symbol     TEXT,
    symbol           TEXT    NOT NULL,
    sec_type         TEXT    NOT NULL,
    exchange         TEXT,
    expiry           TEXT,
    strike           REAL,
    right            TEXT,
    multiplier       REAL,
    window_end_date  INTEGER NOT NULL,
    quote_type       TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'pending',
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    last_attempt_at  TEXT,
    last_error       TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (con_id, window_end_date, quote_type)
);

CREATE INDEX IF NOT EXISTS idx_task_status_date
    ON task(status, window_end_date);
"""


@contextmanager
def connect():
    Path(olc.task_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(olc.task_db, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    try:
        yield conn
    finally:
        conn.close()


TASK_COLUMNS = (
    "con_id", "local_symbol", "symbol", "sec_type", "exchange",
    "expiry", "strike", "right", "multiplier",
    "window_end_date", "quote_type", "status",
    "attempt_count", "last_error",
)


def insert_tasks(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    """Insert tasks, skipping rows that already exist. Returns count of new rows."""
    rows = list(rows)
    if not rows:
        return 0
    sql = (
        "INSERT OR IGNORE INTO task (" + ", ".join(TASK_COLUMNS) + ") "
        "VALUES (" + ", ".join(f":{c}" for c in TASK_COLUMNS) + ")"
    )
    cur = conn.executemany(sql, rows)
    return cur.rowcount


def fetch_pending(conn: sqlite3.Connection, *,
                  window_end_date: int | None = None,
                  before: int | None = None) -> list[sqlite3.Row]:
    """
    Tasks that still need an IB call: pending + (error, to be retried).

    Filters:
        window_end_date=YYYYMMDD  — exactly that window (takes precedence).
        before=YYYYMMDD           — window_end_date < this value (strict).
    """
    sql = "SELECT * FROM task WHERE status IN ('pending', 'error')"
    params: list = []
    if window_end_date is not None:
        sql += " AND window_end_date = ?"
        params.append(int(window_end_date))
    elif before is not None:
        sql += " AND window_end_date < ?"
        params.append(int(before))
    sql += " ORDER BY window_end_date DESC, con_id"
    return conn.execute(sql, params).fetchall()


def update_status(conn: sqlite3.Connection, con_id: int, window_end_date: int,
                  quote_type: str, status: str, error: str | None = None) -> None:
    conn.execute(
        """
        UPDATE task
           SET status          = :status,
               attempt_count   = attempt_count + 1,
               last_attempt_at = datetime('now'),
               last_error      = :error,
               updated_at      = datetime('now')
         WHERE con_id = :con_id
           AND window_end_date = :window_end_date
           AND quote_type = :quote_type
        """,
        dict(con_id=con_id, window_end_date=window_end_date,
             quote_type=quote_type, status=status, error=error),
    )


def status_summary(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.execute("SELECT status, COUNT(*) FROM task GROUP BY status")
    return {row[0]: row[1] for row in cur}
