# SQLite Task-State Queries

Quick diagnostics against `data/status/ol7.sqlite`. Run from repo root.

## Overall status counts

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT status, COUNT(*) FROM task GROUP BY status;
"
```

## Pending / error tasks, grouped by window

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT window_end_date, status, COUNT(*) FROM task
   WHERE status IN ('pending','error')
   GROUP BY window_end_date, status
   ORDER BY window_end_date DESC;
"
```

## What errors are hitting?

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT last_error, COUNT(*) FROM task
   WHERE status='error'
   GROUP BY last_error
   ORDER BY 2 DESC;
"
```

## Full breakdown for recent windows (all statuses)

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT window_end_date, status, COUNT(*) FROM task
   WHERE window_end_date >= 20260401
   GROUP BY window_end_date, status
   ORDER BY window_end_date DESC, status;
"
```

## One-day snapshot — substitute the date of interest

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT status, COUNT(*) FROM task
   WHERE window_end_date = 20260423
   GROUP BY status;
"
```

## Recently attempted tasks (last 100)

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT window_end_date, con_id, quote_type, status, attempt_count,
         last_attempt_at, substr(last_error, 1, 80) AS err
    FROM task
   WHERE last_attempt_at IS NOT NULL
   ORDER BY last_attempt_at DESC
   LIMIT 100;
"
```

## Rows migrated from the old todo.csv (for audit)

```bash
sqlite3 data/status/ol7.sqlite "
  SELECT last_error, COUNT(*) FROM task
   WHERE last_error LIKE 'migrated-from-%'
   GROUP BY last_error;
"
```

## Reset rows back to pending (manual recovery)

Use with care — forces the executor to re-attempt these on the next run.

```bash
# Example: re-try all 'error' rows
sqlite3 data/status/ol7.sqlite "
  UPDATE task SET status='pending', last_error='manual-reset'
   WHERE status='error';
"

# Example: re-try a specific contract × date
sqlite3 data/status/ol7.sqlite "
  UPDATE task SET status='pending', last_error='manual-reset'
   WHERE con_id=872868048 AND window_end_date=20260423;
"
```
