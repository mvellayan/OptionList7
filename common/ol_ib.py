"""
Interactive Brokers historical-data pull.

Async-first, with pacing, structured error handling, and per-day overwrite
guards. The old sync `check_pull_historical_quote_to_file` remains for the
planner's trading-range lookup.
"""
import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Contract, util

import common.ol_const as olc


_ET = ZoneInfo("US/Eastern")
_UTC = ZoneInfo("UTC")


def _format_end_datetime(end_date: str) -> str:
    """
    Convert 'YYYYMMDD' to the UTC dash form IB's reqHistoricalData expects:
    'YYYYMMDD-HH:MM:SS' at 16:00 US/Eastern (market close), converted to UTC.

    We use the UTC form because the space-separated 'YYYYMMDD HH:MM:SS TZ'
    form is accepted inconsistently by recent TWS builds (error 10314).
    """
    dt_et = datetime.strptime(end_date, "%Y%m%d").replace(
        hour=16, minute=0, second=0, tzinfo=_ET,
    )
    return dt_et.astimezone(_UTC).strftime("%Y%m%d-%H:%M:%S")


# --- Connection --------------------------------------------------------------

_ib: Optional[IB] = None
# Per-reqId error capture. Populated by our errorEvent handler; consumed after
# each reqHistoricalDataAsync resolves.
_req_errors: dict[int, tuple[int, str]] = {}


def _on_error(reqId, errorCode, errorString, contract):
    # reqId == -1 is a system/info message (connection status, farm up/down).
    if reqId and reqId > 0:
        _req_errors[reqId] = (errorCode, errorString)


def get_ib() -> IB:
    global _ib
    if _ib is None or not _ib.isConnected():
        _ib = IB()
        _ib.errorEvent += _on_error
        _ib.connect(olc.IB_HOST, olc.IB_PORT, clientId=olc.IB_CLIENT_ID)
    return _ib


# Back-compat alias used by existing callers.
getIB = get_ib


def getContract(data: dict) -> Contract:
    return Contract(
        symbol=data["symbol"], secType=data["secType"],
        currency=data["currency"], exchange=data["exchange"],
        conId=data["conId"], includeExpired=False,
    )


# --- Pacing ------------------------------------------------------------------

_sem: Optional[asyncio.Semaphore] = None
_pacing_lock: Optional[asyncio.Lock] = None
_request_times: list[float] = []


def _ensure_pacing_primitives() -> None:
    global _sem, _pacing_lock
    if _sem is None:
        _sem = asyncio.Semaphore(olc.IB_CONCURRENCY)
        _pacing_lock = asyncio.Lock()


async def _await_pacing_slot() -> None:
    """Rolling-window limiter: ≤ IB_MAX_PER_10MIN requests in the last 600s."""
    async with _pacing_lock:
        now = time.monotonic()
        cutoff = now - 600
        while _request_times and _request_times[0] < cutoff:
            _request_times.pop(0)
        if len(_request_times) >= olc.IB_MAX_PER_10MIN:
            wait = (_request_times[0] + 600) - now + 0.5
            print(f"[pacing] sleeping {wait:.1f}s to stay under "
                  f"{olc.IB_MAX_PER_10MIN}/10min")
            await asyncio.sleep(wait)
        _request_times.append(time.monotonic())


# --- Result types ------------------------------------------------------------

@dataclass
class PullResult:
    status: str                         # 'done' | 'no_data' | 'error'
    error_code: Optional[int] = None
    error_msg: Optional[str] = None
    bars_written: int = 0


# --- Filename helpers --------------------------------------------------------

def _symbol_for_file(contract: Contract) -> str:
    if contract.secType in ("STK", "IND"):
        return contract.symbol.replace(" ", "")
    return contract.localSymbol.replace(" ", "")


def _quote_file(date_str: str, quote_type: str, symbol: str) -> str:
    d = date_str.replace("-", "").replace(" ", "")
    return (olc.DATA_DIR + d[0:4] + "/" + d[4:6] + "/" + d[6:8]
            + "/sq-" + quote_type + "-" + symbol + ".csv")


# A regular trading day has 390 one-minute RTH bars; half-days have ~210.
# Anything > 300 is presumed a complete regular session.
FULL_DAY_ROWS = 300


def _row_count(path: str) -> int:
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
        return max(0, n - 1)  # subtract header
    except OSError:
        return 0


# --- IB error classification -------------------------------------------------

# Codes that mean "there will never be data for this query; stop asking."
#  162  Historical Market Data Service error message: HMDS query returned no data
#  200  No security definition for the request
# 10225 Bust event — contract no longer reports
# 10227 Request rejected (e.g., unsupported parameter combo)
NO_DATA_ERROR_CODES = {162, 200, 10225, 10227}

# Codes that are transient — retrying later is reasonable.
#  165  Historical data pacing violation
# 1100  Connectivity lost
# 1102  Connectivity restored
# 2103/2105/2157  Farm down/broken (usually self-resolves)
TRANSIENT_ERROR_CODES = {165, 1100, 1102, 2103, 2105, 2157}

# Informational / warning codes (2100-range). These fire alongside successful
# responses; we ignore them when bars are present, log them when bars are empty.
#  2100-2169  connection/farm status messages
#  2174       deprecated date-time format warning
WARNING_CODES_IGNORE = set(range(2100, 2200)) | {2174}


# --- Core pull ---------------------------------------------------------------

async def pull_historical_async(contract: Contract, end_date: str,
                                quote_type: str) -> PullResult:
    """
    Pull one window (8 calendar days, 1-min RTH bars) ending on `end_date`,
    write per-day CSVs under data/quotes/YYYY/MM/DD/, and return a PullResult.

    `end_date` is YYYYMMDD. `quote_type` is 'BID_ASK' or 'TRADES'.
    """
    if contract.symbol == "VIX" and quote_type == "BID_ASK":
        return PullResult(status="no_data", error_msg="VIX has no BID_ASK series")

    symbol = _symbol_for_file(contract)
    target_fn = _quote_file(end_date, quote_type, symbol)

    # If the target end-date file is already complete, the whole window is
    # probably already on disk (prior runs of the 8-day pull covered it).
    if _row_count(target_fn) > FULL_DAY_ROWS:
        return PullResult(status="done", bars_written=0)

    _ensure_pacing_primitives()
    ib = get_ib()

    async with _sem:
        await _await_pacing_slot()
        try:
            bars = await ib.reqHistoricalDataAsync(
                contract,
                # UTC dash form — avoids both the deprecation warning on the
                # unqualified "YYYYMMDD HH:MM:SS" form and error 10314 that
                # some TWS builds emit for "YYYYMMDD HH:MM:SS US/Eastern".
                endDateTime=_format_end_datetime(end_date),
                durationStr=olc.WINDOW_DURATION,
                barSizeSetting="1 min",
                whatToShow=quote_type,
                useRTH=True,
                formatDate=1,
                timeout=olc.IB_HIST_TIMEOUT,
            )
        except Exception as e:
            return PullResult(status="error", error_msg=f"{type(e).__name__}: {e}")

    # After the call, see whether any per-reqId error fired.
    req_id = getattr(bars, "reqId", None)
    err = _req_errors.pop(req_id, None) if req_id is not None else None

    # Bars won — a non-empty response means the request succeeded, regardless of
    # any warning (2100-range) that fired alongside it.
    if len(bars) > 0:
        # Fall through to write bars; any warning was informational.
        pass
    elif err is not None:
        code, msg = err
        # Error 162 is overloaded: "returned no data" means genuinely empty,
        # but "query cancelled" means the ib_insync client-side timeout fired
        # before IB answered — the request never actually ran. Retry those.
        if code == 162 and "cancelled" in msg.lower():
            return PullResult(status="error", error_code=code, error_msg=msg)
        if code in WARNING_CODES_IGNORE:
            return PullResult(status="no_data", error_code=code, error_msg=msg)
        if code in NO_DATA_ERROR_CODES:
            return PullResult(status="no_data", error_code=code, error_msg=msg)
        if code in TRANSIENT_ERROR_CODES:
            return PullResult(status="error", error_code=code, error_msg=msg)
        # Unknown — treat as transient so it gets another look next run.
        return PullResult(status="error", error_code=code, error_msg=msg)
    else:
        # Bars empty and no error fired. Most likely an ib_insync timeout that
        # didn't surface through errorEvent. Treat as transient.
        return PullResult(status="error",
                          error_msg="empty bars, likely client-side timeout")

    df = util.df(bars)
    df["symbol"] = contract.symbol
    df["localSymbol"] = contract.localSymbol
    df["conId"] = contract.conId

    days = df["date"].astype(str).str.slice(stop=10).unique()
    written = 0
    for d in days:
        out_fn = _quote_file(d, quote_type, symbol)
        # Don't overwrite a previously complete file with partial re-pull data.
        if _row_count(out_fn) > FULL_DAY_ROWS:
            continue
        df_day = df.loc[df["date"].astype(str).str.slice(stop=10) == d]
        Path(out_fn).parent.mkdir(parents=True, exist_ok=True)
        df_day.to_csv(out_fn, index=False)
        written += df_day.shape[0]

    return PullResult(status="done", bars_written=written)


# --- Back-compat sync wrapper ------------------------------------------------

def check_pull_historical_quote_to_file(sDate: str, contract):
    """
    Sync wrapper: pull both BID_ASK and TRADES for the given end date.
    Preserved for the planner, which derives trading range from the TRADES file.

    Note: unlike the previous version, this does NOT break on the first empty
    quote type — so an empty BID_ASK no longer silently skips the TRADES pull.
    """
    assert isinstance(sDate, str), "sDate should be string"
    ib = get_ib()

    async def _pull_both():
        for qt in ("BID_ASK", "TRADES"):
            res = await pull_historical_async(contract, sDate, qt)
            if res.status == "error":
                print(f"[pull] {sDate} {contract.localSymbol or contract.symbol} "
                      f"{qt} error {res.error_code}: {res.error_msg}")

    ib.run(_pull_both())

    symbol = _symbol_for_file(contract)
    fn = _quote_file(sDate, "TRADES", symbol)
    if os.path.exists(fn):
        return pd.read_csv(fn, index_col=None)
    return pd.DataFrame()
