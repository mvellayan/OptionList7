"""
One-shot, idempotent migration of data/status/todo.csv into SQLite.

Each old row represents one (contract, pull_date) × (BID_ASK + TRADES implicitly).
We explode into two rows per old row — one per quote_type — and map status:

    5-done                  → done
    9-error, after 3 tries  → no_data   (empirically: empty every time)
    1-todo                  → pending   (never actually tried)
    2-todo                  → no_data   (tried once, came up empty — stop retrying)
    3-todo                  → no_data   (tried twice, came up empty — stop retrying)

`last_error` records the migration source so the rows can be reviewed later.

Idempotent: if the task table already has rows, this does nothing. Delete
ol7.sqlite to force a re-migration.
"""
import os
import sys

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
sys.path.append(uppath(os.path.realpath(__file__), 2))

import pandas as pd

import common.ol_const as olc
import common.ol_db as db
import common.ol_util as olu


STATUS_MAP = {
    "5-done": ("done", None),
    "9-error, after 3 tries": ("no_data", "migrated-from-9-error"),
    "1-todo": ("pending", None),
    "2-todo": ("no_data", "migrated-from-2-todo"),
    "3-todo": ("no_data", "migrated-from-3-todo"),
}


def _attempt_count(old_status: str) -> int:
    return {"1-todo": 0, "2-todo": 1, "3-todo": 2}.get(old_status, 3)


def _row_to_tasks(row: pd.Series) -> list[dict]:
    """Explode one todo.csv row into (up to) two task rows — BID_ASK + TRADES."""
    old_status = row["status"]
    if old_status not in STATUS_MAP:
        return []
    new_status, err = STATUS_MAP[old_status]
    attempts = _attempt_count(old_status)
    symbol = row["symbol"]

    quote_types = ["BID_ASK", "TRADES"]
    # VIX has no BID_ASK series — matches the VIX-skip branch in ol_ib.
    if symbol == "VIX":
        quote_types = ["TRADES"]

    base = dict(
        con_id=int(row["conId"]),
        local_symbol=row.get("localSymbol") if pd.notna(row.get("localSymbol")) else None,
        symbol=symbol,
        sec_type=row["secType"],
        exchange=row.get("exchange") if pd.notna(row.get("exchange")) else None,
        expiry=str(int(row["lastTradeDateOrContractMonth"]))
               if pd.notna(row.get("lastTradeDateOrContractMonth")) else None,
        strike=float(row["strike"]) if pd.notna(row.get("strike")) else None,
        right=row.get("right") if pd.notna(row.get("right")) else None,
        multiplier=float(row["multiplier"])
                   if pd.notna(row.get("multiplier")) else None,
        window_end_date=int(row["pull_date"]),
        status=new_status,
        attempt_count=attempts,
        last_error=err,
    )
    return [{**base, "quote_type": qt} for qt in quote_types]


def migrate():
    with db.connect() as conn:
        existing = db.status_summary(conn)
        if existing:
            print(olu.tn() + f"DB already populated: {existing}. Skipping migration.")
            return

        if not os.path.exists(olc.todo_file):
            print(olu.tn() + f"No {olc.todo_file} to migrate. Nothing to do.")
            return

        todo = pd.read_csv(olc.todo_file, index_col=None)
        print(olu.tn() + f"Loaded {len(todo):,} rows from {olc.todo_file}")

        todo = todo.dropna(subset=["conId", "pull_date", "status"])
        # Older todo.csv snapshots have leading whitespace on the error status.
        todo["status"] = todo["status"].astype(str).str.strip()

        tasks: list[dict] = []
        unknown_statuses: dict[str, int] = {}
        for _, row in todo.iterrows():
            new_rows = _row_to_tasks(row)
            if not new_rows:
                unknown_statuses[row["status"]] = unknown_statuses.get(row["status"], 0) + 1
            tasks.extend(new_rows)

        if unknown_statuses:
            print(olu.tn() + f"WARNING: skipped unknown statuses: {unknown_statuses}")

        inserted = db.insert_tasks(conn, tasks)
        print(olu.tn() + f"Inserted {inserted:,} task rows into SQLite.")
        print(olu.tn() + f"Final status summary: {db.status_summary(conn)}")


if __name__ == "__main__":
    migrate()
    print(olu.tn() + "2dc-migrate-todo-to-sqlite done!")
