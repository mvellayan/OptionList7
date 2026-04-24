"""
Plan which (contract × window_end_date × quote_type) rows need pulling.

Strategy:
  1. Pick NUM_WINDOWS recent trading days as window_end_dates, spaced ~5
     trading days apart. Each IB call with durationStr="8 D" + useRTH=True
     returns ~6 trading days of 1-min bars, so 5-day spacing gives slight
     overlap and covers ~30 trading days of history.
  2. Pull the base stock (AAPL) windows synchronously so we can read the
     trading range from the per-day TRADES files.
  3. Walk every trading day in the configured range, look up its range from
     the TRADES file, and union the resulting option lists.
  4. Insert (contract × window_end_date × quote_type) rows into SQLite as
     pending. Duplicates are skipped by the primary key.
"""
import os
import sys
from datetime import datetime
import warnings

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
sys.path.append(uppath(os.path.realpath(__file__), 2))

import pandas as pd
from tqdm import tqdm

import common.ol_const as olc
import common.ol_db as db
import common.ol_ib as oli
import common.ol_pd as olpd
import common.ol_util as olu

warnings.simplefilter(action="ignore", category=FutureWarning)


VIX_CONID = 13455763  # matches the old hardcoded value


def pick_window_end_dates(working_dates: list[int]) -> list[int]:
    sorted_desc = sorted(working_dates, reverse=True)
    chosen = sorted_desc[::5][:olc.NUM_WINDOWS]
    return sorted(chosen)


def pull_stock_windows(stock, window_end_dates: list[int]) -> None:
    for d in window_end_dates:
        sDate = str(d)
        df = oli.check_pull_historical_quote_to_file(sDate, stock)
        if df.empty:
            print(olu.tn() + f"  Stock {stock.symbol} {sDate}: no TRADES data")


def trading_range_for(stock, date_int: int) -> tuple[float, float] | None:
    sDate = str(date_int)
    sym = (stock.symbol.replace(" ", "") if stock.secType in ("STK", "IND")
           else stock.localSymbol.replace(" ", ""))
    fn = (olc.DATA_DIR + sDate[0:4] + "/" + sDate[4:6] + "/" + sDate[6:8]
          + "/sq-TRADES-" + sym + ".csv")
    if not os.path.exists(fn):
        return None
    df = pd.read_csv(fn)
    if df.empty or "open" not in df.columns:
        return None
    return float(df["open"].min()), float(df["open"].max())


def build_option_list_for_day(stock, sDate: str) -> pd.DataFrame:
    rng = trading_range_for(stock, int(sDate))
    if rng is None:
        return pd.DataFrame()
    min_, max_ = rng
    return olpd.getOptionlist(stock, sDate, min_, max_,
                              olc.StrikeRange, olc.ExpiryOut)


def _opt_cell(row, key, cast=None):
    val = row.get(key)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if cast is not None:
        return cast(val)
    return val


def rows_to_task_dicts(options_by_conid: dict[int, pd.Series],
                        window_end_dates: list[int]) -> list[dict]:
    out: list[dict] = []
    for conid, r in options_by_conid.items():
        for d in window_end_dates:
            for qt in ("BID_ASK", "TRADES"):
                if r["symbol"] == "VIX" and qt == "BID_ASK":
                    continue
                expiry = _opt_cell(r, "lastTradeDateOrContractMonth",
                                   cast=lambda x: str(int(float(x))))
                out.append(dict(
                    con_id=int(conid),
                    local_symbol=_opt_cell(r, "localSymbol"),
                    symbol=r["symbol"],
                    sec_type=r["secType"],
                    exchange=_opt_cell(r, "exchange"),
                    expiry=expiry,
                    strike=_opt_cell(r, "strike", cast=float),
                    right=_opt_cell(r, "right"),
                    multiplier=_opt_cell(r, "multiplier", cast=float),
                    window_end_date=int(d),
                    quote_type=qt,
                    status="pending",
                    attempt_count=0,
                    last_error=None,
                ))
    return out


def plan(stock):
    market_days = pd.read_csv(olc.market_days, index_col=None)
    market_days = market_days.astype({"working_date": int, "working_hour": float})
    in_range = market_days.loc[
        (market_days["working_date"] > olc.STOCK_PULL_START_DATE)
        & (market_days["working_date"] <= olc.STOCK_PULL_END_DATE)
    ]
    if in_range.empty:
        print("NO CURRENT WORKING DATE. fix market-days.csv file!")
        sys.exit(1)

    window_end_dates = pick_window_end_dates(in_range["working_date"].tolist())
    print(olu.tn() + f"Window end dates: {window_end_dates}")

    print(olu.tn() + "Pulling stock windows for trading-range lookup...")
    pull_stock_windows(stock, window_end_dates)

    print(olu.tn() + f"Scanning {len(in_range)} trading days for option candidates...")
    options_by_conid: dict[int, pd.Series] = {}
    for d in tqdm(sorted(in_range["working_date"].tolist()),
                  desc="Trading days", unit="day", ncols=100):
        sDate = str(int(d))
        opt = build_option_list_for_day(stock, sDate)
        if opt.empty:
            continue
        for _, r in opt.iterrows():
            options_by_conid[int(r["conId"])] = r

    print(olu.tn() + f"Discovered {len(options_by_conid)} unique option contracts")

    # Include the stock and VIX as tasks so the executor handles them uniformly.
    options_by_conid[int(stock.conId)] = pd.Series({
        "conId": int(stock.conId), "symbol": stock.symbol,
        "exchange": stock.exchange, "secType": stock.secType,
    })
    options_by_conid[VIX_CONID] = pd.Series({
        "conId": VIX_CONID, "symbol": "VIX",
        "exchange": "CBOE", "secType": "IND",
    })

    tasks = rows_to_task_dicts(options_by_conid, window_end_dates)
    print(olu.tn() + f"Candidate task rows: {len(tasks)}")

    with db.connect() as conn:
        inserted = db.insert_tasks(conn, tasks)
        summary = db.status_summary(conn)

    print(olu.tn() + f"Inserted {inserted} new task rows (rest already existed).")
    print(olu.tn() + f"Status summary: {summary}")


if __name__ == "__main__":
    print(olu.tn() + "3-plan-tasks Starting!")

    config = olu.getConfig(olc.stock_list_json)
    stock = oli.getContract(config.get("stocks")[0]["contract"])
    plan(stock)

    print(olu.tn() + "3-plan-tasks done!")
