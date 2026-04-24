"""
Execute pending tasks from SQLite using async IB requests in parallel.

For each pending/error row, issue reqHistoricalDataAsync for the right
quote_type, mark the row done / no_data / error based on the result.
Concurrency and pacing are controlled in common.ol_ib.
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
sys.path.append(uppath(os.path.realpath(__file__), 2))

# NYSE closes at 16:00 US/Eastern. After that, today's 1-min bars are complete
# and safe to include in the default run scope.
_MARKET_CLOSE_HOUR_ET = 16
_ET = ZoneInfo("US/Eastern")

from ib_insync import Contract
from tqdm import tqdm

import common.ol_const as olc
import common.ol_db as db
import common.ol_ib as oli
import common.ol_util as olu


def row_to_contract(row) -> Contract:
    return Contract(
        conId=int(row["con_id"]),
        secType=row["sec_type"],
        exchange=row["exchange"],
        symbol=row["symbol"],
        localSymbol=row["local_symbol"] or "",
        currency="USD",
    )


async def run_one(conn, row, pbar: tqdm) -> None:
    contract = row_to_contract(row)
    end_date = str(row["window_end_date"])
    qt = row["quote_type"]

    try:
        result = await oli.pull_historical_async(contract, end_date, qt)
    except Exception as e:
        db.update_status(conn, row["con_id"], row["window_end_date"], qt,
                         status="error", error=f"{type(e).__name__}: {e}")
        pbar.update(1)
        return

    err = (f"{result.error_code}: {result.error_msg}"
           if result.error_code or result.error_msg else None)
    db.update_status(conn, row["con_id"], row["window_end_date"], qt,
                     status=result.status, error=err)
    pbar.update(1)


async def run_all(conn, rows) -> None:
    # Concurrency is bounded by the semaphore inside ol_ib; we can schedule all
    # coroutines and let the semaphore gate them.
    with tqdm(total=len(rows), desc="Tasks", unit="task", ncols=100) as pbar:
        await asyncio.gather(*(run_one(conn, r, pbar) for r in rows))


def _default_include_today() -> tuple[bool, str]:
    """Include today by default iff the US/Eastern clock is past 16:00."""
    et_now = datetime.now(_ET)
    if et_now.hour >= _MARKET_CLOSE_HOUR_ET:
        return True, f"market closed ({et_now:%H:%M %Z})"
    return False, f"market still open ({et_now:%H:%M %Z})"


def execute(*, date: int | None = None,
            include_today: bool | None = None) -> None:
    et_today_int = int(datetime.now(_ET).strftime("%Y%m%d"))

    with db.connect() as conn:
        if date is not None:
            rows = db.fetch_pending(conn, window_end_date=date)
            scope = f"window_end_date={date}"
        else:
            if include_today is None:
                include_today, reason = _default_include_today()
            else:
                reason = "explicit flag"

            if include_today:
                rows = db.fetch_pending(conn)
                scope = f"all pending incl. today — {reason}"
            else:
                rows = db.fetch_pending(conn, before=et_today_int)
                scope = (f"window_end_date < {et_today_int} "
                         f"(today excluded — {reason})")

        if not rows:
            print(olu.tn() + f"No pending tasks for scope: {scope}.")
            return

        print(olu.tn() + f"Executing {len(rows)} tasks — {scope} "
                         f"(concurrency={olc.IB_CONCURRENCY}, "
                         f"pacing={olc.IB_MAX_PER_10MIN}/10min)")

        ib = oli.get_ib()
        ib.run(run_all(conn, rows))

        summary = db.status_summary(conn)
        print(olu.tn() + f"Status summary: {summary}")


def _parse_args():
    p = argparse.ArgumentParser(
        description=("Execute pending IB historical-data tasks from SQLite. "
                     "By default, today's window is included only after "
                     "16:00 US/Eastern (NYSE close)."),
    )
    p.add_argument(
        "--date", type=int, metavar="YYYYMMDD",
        help="Only process tasks with this exact window_end_date.",
    )
    p.add_argument(
        "--include-today", action=argparse.BooleanOptionalAction, default=None,
        help="Force include/exclude today's window. Overrides the "
             "market-close default.",
    )
    args = p.parse_args()
    if args.date is not None and args.include_today is not None:
        p.error("--date cannot be combined with --include-today/--no-include-today")
    return args


if __name__ == "__main__":
    args = _parse_args()
    execute(date=args.date, include_today=args.include_today)
    print(olu.tn() + "4-execute-tasks done!")
