# OptionList7 — Code Review Findings

Weekly pipeline that pulls 1-minute bars from Interactive Brokers for AAPL + ~27 option contracts, stored as per-day CSVs and loaded into MySQL. Historically ~4 hours per run.

## 2026-04-23 — Items 1–4 from the "order of attack" landed

- **IB retry logic fixed.** `common/ol_ib.py` now registers an `errorEvent` handler and classifies IB error codes: 162/200/10225/10227 → `no_data` (never retry), 165/1100/1102/2103/2105/2157 → `error` (retryable). Empty bars with no IB error are also marked `no_data`. Per-output-day overwrite guard added so partial re-pulls can't clobber complete day files. Fixed the `break`-on-empty bug that skipped TRADES when BID_ASK was empty.
- **Async batching landed.** `pull_historical_async` uses `ib_insync.reqHistoricalDataAsync` behind a `Semaphore(IB_CONCURRENCY=10)` and a rolling-window rate limiter capped at `IB_MAX_PER_10MIN=55`. `4dc-execute-tasks.py` dispatches all pending tasks via `asyncio.gather`.
- **Task state moved to SQLite.** `data/status/ol7.sqlite` with one row per `(con_id, window_end_date, quote_type)`. Schema + helpers in `common/ol_db.py`. Statuses: `pending` / `done` / `no_data` / `error`.
- **Planning re-granulated by window.** `3dc-plan-tasks.py` picks `NUM_WINDOWS=5` end-dates (every 5th trading day), which with `durationStr="8 D"` covers ~30 trading days with slight overlap. Option discovery still walks every trading day in the range so strike-drift options aren't missed.
- **Migration script.** `2dc-migrate-todo-to-sqlite.py` is idempotent. Maps old statuses: `5-done → done`, `9-error → no_data`, `1-todo → pending`, and `2-todo / 3-todo → no_data` (already tried, empirically empty — this is what unblocks the fast first run). VIX rows get TRADES only, matching the IB reality.
- **MySQL loader updated.** `load_task()` in `2p-load-to-mysql.py` now reads from SQLite; it dedups to one row per `(con_id, pull_date)` before the INSERT IGNORE so the MySQL schema doesn't need changes.
- **Dead code removed.** `5dc-report-missing-data.py` (broken imports) and `1p-project-join.py` (no-op) deleted. `save_todo_csv` removed from `common/ol_pd.py`. `pull_option_data.sh` refactored into a `run_step` function and the dead step dropped.
- **Secrets pushed to env vars.** DB host/user/password/schema and IB host/port/client-id in `common/ol_const.py` now read `OL7_DB_*` / `IB_*` env vars, with the previous hardcoded values as fallback so nothing breaks in-place. Rotate the DB password and remove the fallback when convenient.

**First-run migration state (observed on real `todo.csv`):** 17,922 source rows → 35,755 SQLite rows (`done=17007, no_data=18132, pending=616`). The 2,382 known-empty rows that used to burn IB pacing every run are now `no_data` and will never be re-tried.

### What to do next

- Run the pipeline once. Expect the first `4dc-execute-tasks.py` to be dramatically shorter than 4 hours (the pending 616 + this week's newly-planned windows will short-circuit via file-existence check for anything already on disk). Watch for any IB error codes in `last_error` that aren't in the known-code sets and extend `NO_DATA_ERROR_CODES` / `TRANSIENT_ERROR_CODES` accordingly.
- If something looks off after the first run, the old CSV is still at `data/status/todo.csv` and the SQLite DB can be deleted to force re-migration.
- Remaining items from the review that weren't in this batch: DB password rotation (now trivial — just unset the env var fallback in `ol_const.py`), dep modernization, `6dc-row-count-report.py` minor perf, `pandas_market_calendars` migration.

## Where the 4 hours is going (the one thing to fix first)

The retry logic in `4dc-execute-tasks.py` is the dominant cost. Current state of `data/status/todo.csv`:

- `5-done`: 8,548
- `9-error, after 3 tries`: 6,992 (permanently failed)
- `1-todo`: 308
- `2-todo`: 845 (already failed once, will be retried every run)
- `3-todo`: 1,229 (already failed twice, will be retried every run)

**Every weekly run re-issues ~2,382 historical-data requests for rows that have already returned no data at least once.** At IB's typical 1–3 second response time per request plus pacing throttles (60 requests per 10 minutes), that alone accounts for most of the wall-clock time.

The root cause: `check_pull_historical_quote_to_file` treats an empty result the same as a failure. Many of these aren't failures — they're options that simply didn't trade that minute/day or contracts with no BID_ASK series (VIX-style). IB returns "HMDS query returned no data" (error 162) which is a definitive answer, not a transient condition.

**Recommended fix (biggest ROI):**
1. Attach an error handler to `ib.errorEvent` in `common/ol_ib.py` so you can distinguish IB error codes: 162 "no data" vs 165 "pacing" vs 1100 "connection lost" vs 10197 "no market data" etc.
2. On definitive no-data responses, write a `.empty` sentinel (or a row in a "known empty" table) and never retry.
3. Retry only on transient errors (pacing, disconnect).
4. Consider dropping the 3-strike retry system entirely and just doing 1 try + explicit transient-retry-with-backoff.

Expect this alone to cut runtime by **60–80%**.

## Next biggest lever: concurrency

`ib_insync` supports `reqHistoricalDataAsync` and IB allows up to ~50 concurrent pending historical data requests. Your current loop is strictly synchronous — one request at a time, blocking on each.

A small `asyncio.gather`-based batch (e.g. 10 requests in flight at once, respecting the 60-per-10-min pacing) would cut wall-clock dramatically without any protocol changes. `ib_insync`'s event loop is already there; the code just isn't using it.

## Structural issues

### 1. Per-day todo granularity doesn't match per-request granularity

`check_pull_historical_quote_to_file` already pulls `durationStr='8 D'` in one API call and writes 8 per-day CSVs. But `todo.csv` tracks one row per `(conId, pull_date)`, so when the planner creates 22 days × 28 contracts × 2 types of todo rows, the execution layer relies on the "file exists with >300 rows" check to dedupe. That check short-circuits redundant calls for fresh data, but it doesn't help for known-empty days — those get retried every week.

Recommendation: plan by "8-day window ending on date X", not by day. Track (contract, window_end_date) as the unit of work. Drops the todo-row count by ~8×.

### 2. `check_pull_historical_quote_to_file` can overwrite good data with partial data

When an 8-day block is pulled, all 8 per-day CSVs are written unconditionally. A partial trading day in the window can overwrite a previously complete file for that date. The existence check happens *before* the call (based on the target `sDate`) but not per-output-date. Add a per-output-date existence/row-count guard in the write loop.

### 3. `break` on first empty result skips the other quote type

In `check_pull_historical_quote_to_file`, the loop iterates `['BID_ASK', 'TRADES']` and breaks on the first empty response. For contracts where BID_ASK is empty but TRADES has data (or vice versa), this silently drops one side. Use `continue` instead of `break`, or handle the two series independently.

### 4. CSV todo file is a poor fit for 18k rows of state

`todo.csv` is read, sorted, deduped, and rewritten on every save (every 10 tasks in `4dc-execute-tasks.py`). The file has 17,923 rows. SQLite would be a drop-in replacement with indexed lookups, atomic updates, and no rewrite-the-whole-file pattern. Also lets you run `SELECT` queries for status reports instead of pandas groupby.

### 5. Status state machine is ambiguous and string-sorted

Status is compared with `row['status'] > '4'` — lexical string comparison. `'1-todo' < '2-todo' < ... < '5-done' < '9-error, after 3 tries'`. This works today but breaks silently the moment someone adds `'4-retrying'` or `'10-something'`. Use an enum or integer column.

### 6. Single global `IB` connection with hardcoded `clientId=1`

`common/ol_ib.py` holds `global_ib = IB()` with `clientId=1` — prevents any second process from connecting, and precludes multiprocessing parallelism. Take `clientId` from config and pick a unique one per process.

### 7. Import-time side effects

`common/ol_const.py` computes `STOCK_PULL_START_DATE`/`STOCK_PULL_END_DATE` at module import, branching on wall-clock time. Subtle bugs arise if a script runs across midnight or the Python process is long-lived. Move to a function.

## Bugs I noticed while reading

- **`5dc-report-missing-data.py` is broken.** It references `olu.FILE_GROUPS` (lives in `olc`) and `olu.dedup` (lives in `olpd`). Script would raise `AttributeError` if anyone ran it. Not called from the main pipeline, so it's dead code.
- **`data-prep/1p-project-join.py` is a no-op.** `__main__` is commented out with the note "this is no longer required, I think" — but `pull_option_data.sh` still runs it as Step 4 and includes its timing in the email report. Either wire it back up or remove the step.
- **`3dc-plan-tasks.py::write_todo_to_file` uses `todo_dates` as an implicit global** — only works because it's called from `__main__`. Move it to a parameter.
- **`pull_option_data.sh`** has `PROG1..PROG5` blocks that are 90% copy-paste. Trivially refactorable to a bash function or a small Python driver.

## Security / hygiene

- **Hardcoded DB credentials** in `common/ol_const.py` (`database_password = 'rk2admin!'`). Move to env vars or a `.env` file that isn't committed. Check `git log -p common/ol_const.py` — if this was ever committed, rotate the password.
- **IB port `7496` hardcoded** (live TWS). Paper trading uses 7497; IB Gateway uses 4001/4002. Should be configurable.
- **`include/`, `share/`, `etc/`** at the repo root look like virtualenv artifacts that got committed — verify and add to `.gitignore` if so.
- **Two `todo` files** (`todo.csv`, `todo-02-19.csv`) suggest manual archiving. Formalize with a rotation script or move to SQLite.

## Dependency rot

- `ib-insync==0.9.71` — the library is in community-maintained mode since the original maintainer Ewald de Wit passed away. Consider migrating to the maintained fork `ib-async` (drop-in) or the official `ibapi`.
- `requirements.txt` pins Flask, gunicorn, mlflow, xgboost, sklearn, jupyter — none of which appear in the data-collection or data-prep code paths. Trim to just what's imported and let pip resolve minor versions.
- Docker base is `python:3.9.4` (3.9 is EOL Oct 2025). Upgrade to 3.11+ when you touch this next.
- `pandas~=1.5.1` is pinned; pandas 2.x has notable perf improvements for the concat-heavy patterns you use.

## Minor performance cleanups

- `6dc-row-count-report.py` uses `pd.read_csv` just to count rows — the code comment even acknowledges `wc -l` would be faster. For 1000s of files, this matters. Use `sum(1 for _ in open(path)) - 1` or shell out to `wc -l`.
- `common/ol_pd.py::load_data` reads all CSVs into a single DataFrame in memory. For the projection step that's touching 1000s of files, consider `pyarrow.csv` or converting the archive to Parquet once (read speed ~10–100× faster, size ~5× smaller).
- `market_days` CSV is brittle. `pandas_market_calendars` gives you NYSE/NASDAQ/CBOE calendars out of the box, including half-days.

## Summary: suggested order of attack

1. **Fix the retry logic** (handle IB error 162 as definitive, stop retrying known-empty rows). Biggest single win, probably a day's work. Should cut runtime to ~1 hour.
2. **Add async batching** in `check_pull_historical_quote_to_file`. Expect another 2–4× speedup.
3. **Move todo state from CSV to SQLite**, and re-granulate to (contract, 8-day-window). Easier to reason about and faster.
4. **Clean up dead code** (`5dc`, `1p-project-join`) and the duplicated shell-script blocks.
5. **Move credentials to env vars**, rotate the DB password.
6. **Dependency modernization** — separate PR; don't mix with behavior changes.
