"""
6dc-row-count-report

For a given calendar year, emit one CSV per ISO week summarizing how many
1-min TRADES bars we have for each AAPL option contract. Columns are the
five weekdays (Mon-Fri); rows are contracts sorted by (expiry, right, strike)
with calls before puts within each expiry. The underlying stock is skipped.

Usage:
    python3 6dc-row-count-report.py <year> [quotes_dir]
"""
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
sys.path.append(uppath(os.path.realpath(__file__), 2))

import common.ol_const as olc
import common.ol_util as olu


# Matches e.g. "sq-TRADES-AAPL260403C00235000.csv" but not
# "sq-TRADES-AAPL.csv" (the underlying) nor BID_ASK files.
CONTRACT_RE = re.compile(r"^sq-TRADES-AAPL(\d{6})([CP])(\d{8})\.csv$")


def count_rows(path: Path) -> int:
    """Fast header-excluding line count. Avoids pandas.read_csv overhead."""
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        return 0
    return max(0, n - 1)


def parse_contract(name: str):
    """(expiry:YYYYMMDD, right:'C'|'P', strike:float) or None if not an option."""
    m = CONTRACT_RE.match(name)
    if not m:
        return None
    yymmdd, right, strike_str = m.groups()
    return "20" + yymmdd, right, int(strike_str) / 1000.0


def monday_of(iso_year: int, iso_week: int) -> date:
    """ISO year + week number → the Monday of that week."""
    jan4 = date(iso_year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    return week1_monday + timedelta(weeks=iso_week - 1)


def scan_year(year: int, quotes_path: Path):
    """
    Walk data/quotes/{year}/MM/DD/ and collect:
        weekly[(iso_year, iso_week)][(expiry, right, strike, contract_name)][d] = row_count
    """
    weekly: dict[tuple[int, int], dict[tuple, dict[date, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    year_dir = quotes_path / f"{year:04d}"
    if not year_dir.exists():
        return weekly, 0

    files_seen = 0
    for month_dir in sorted(year_dir.iterdir()):
        if not month_dir.is_dir() or not month_dir.name.isdigit():
            continue
        for day_dir in sorted(month_dir.iterdir()):
            if not day_dir.is_dir() or not day_dir.name.isdigit():
                continue
            try:
                d = date(year, int(month_dir.name), int(day_dir.name))
            except ValueError:
                continue
            iso = d.isocalendar()
            wk_key = (iso.year, iso.week)
            for f in day_dir.glob("sq-TRADES-AAPL*.csv"):
                parsed = parse_contract(f.name)
                if parsed is None:
                    continue
                expiry, right, strike = parsed
                contract_name = f.name.removeprefix("sq-TRADES-").removesuffix(".csv")
                key = (expiry, right, strike, contract_name)
                weekly[wk_key][key][d] = count_rows(f)
                files_seen += 1

    return weekly, files_seen


def write_week_report(out_fn: Path, iso_year: int, iso_week: int,
                       contracts: dict[tuple, dict[date, int]]) -> None:
    mon = monday_of(iso_year, iso_week)
    week_dates = [mon + timedelta(days=i) for i in range(5)]  # Mon..Fri

    # Sort: expiry ASC, calls before puts, strike ASC.
    sorted_keys = sorted(
        contracts.keys(),
        key=lambda k: (k[0], 0 if k[1] == "C" else 1, k[2]),
    )

    headers = ["expiry", "right", "strike", "contract"] + \
              [d.isoformat() for d in week_dates] + ["total"]

    with open(out_fn, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for key in sorted_keys:
            expiry, right, strike, contract_name = key
            counts = contracts[key]
            day_counts = [counts.get(d, 0) for d in week_dates]
            w.writerow([expiry, right, f"{strike:.2f}", contract_name,
                        *day_counts, sum(day_counts)])


def generate_weekly_reports(year: int, quotes_dir: str | None = None) -> int:
    quotes_path = Path(quotes_dir) if quotes_dir else Path(olc.DATA_DIR)
    summary_dir = quotes_path / "summary"
    summary_dir.mkdir(exist_ok=True)

    print(olu.tn() + f"Scanning {quotes_path / f'{year:04d}'}")
    weekly, files_seen = scan_year(year, quotes_path)
    print(olu.tn() + f"Scanned {files_seen} AAPL option files across "
                     f"{len(weekly)} ISO weeks.")

    for (iso_year, iso_week), contracts in sorted(weekly.items()):
        out_fn = summary_dir / f"row-count-{iso_year}-W{iso_week:02d}.csv"
        write_week_report(out_fn, iso_year, iso_week, contracts)
        print(olu.tn() + f"  {out_fn.name}: {len(contracts)} contracts")

    print(olu.tn() + f"Wrote {len(weekly)} weekly reports to {summary_dir}")
    return len(weekly)


if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print("Usage: 6dc-row-count-report.py <year> [quotes_dir]")
        sys.exit(1)

    year_arg = int(sys.argv[1])
    quotes_dir_arg = sys.argv[2] if len(sys.argv) > 2 else None

    start = datetime.now()
    print(olu.tn() + f"6dc-row-count-report Starting! year={year_arg}")
    count = generate_weekly_reports(year_arg, quotes_dir_arg)
    dur = (datetime.now() - start).total_seconds()
    print(olu.tn() + f"6dc-row-count-report done! {count} reports in {dur:.1f}s")
