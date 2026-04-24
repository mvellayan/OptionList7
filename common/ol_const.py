from datetime import datetime, timedelta, time

REFERENCE_DIR = "../data/reference/"
DATA_DIR = "../data/quotes/"
PROJECTION_DIR = "../data/projection/"
todo_file = "../data/status/todo.csv"
task_db = "../data/status/ol7.sqlite"
stock_list_json = "../data/reference/stock-list.json"
option_list_csv = "../data/reference/option-list-*.csv"

# Window-planning knobs. Each window ends on a trading Friday and covers an 8-calendar-day
# IB reqHistoricalData call (whatToShow + 1-min bars + useRTH=True → ~6 trading days).
NUM_WINDOWS = 5  # 5 Fridays ≈ 30 trading days of coverage
WINDOW_DURATION = "8 D"

# IB pacing. Keep conservatively under the 60-per-10-min cap and the 50-concurrent cap.
IB_CONCURRENCY = 10
IB_MAX_PER_10MIN = 55
# Client-side timeout per reqHistoricalDataAsync. ib_insync defaults to 60s, which
# is tight when the semaphore has many requests queued. A cancelled request
# yields error 162 ("API historical data query cancelled") that we'd otherwise
# have to treat as a retry — larger timeout means fewer spurious cancellations.
IB_HIST_TIMEOUT = 180

# Connection settings. Override via IB_HOST / IB_PORT / IB_CLIENT_ID env vars if desired.
import os as _os
IB_HOST = _os.environ.get("IB_HOST", "127.0.0.1")
IB_PORT = int(_os.environ.get("IB_PORT", "7496"))
IB_CLIENT_ID = int(_os.environ.get("IB_CLIENT_ID", "1"))

model_generator_json = "../model/ref-data/model-generator.json"
model_list_csv = "../model/ref-data/model-list.csv"
model_name_csv = "../model/ref-data/model-name.csv"
market_days = "../data/reference/market-days.csv"

FILE_GROUPS = ["../data/raw/AAPL/?q-BID_ASK-*csv", "../data/raw/AAPL/?q-TRADES-*csv"]


today = datetime.now().today()
yesterday = today - timedelta(days=1)

STOCK_PULL_START_DATE: int = int((today - timedelta(days=30)).strftime('%Y%m%d'))

if datetime.now().time() > time(16, 0, 0):
    STOCK_PULL_END_DATE: int = int(today.strftime('%Y%m%d'))
else:
    STOCK_PULL_END_DATE: int = int(yesterday.strftime('%Y%m%d'))

# how many strike prices below and above to pull
StrikeRange = 2
# how many weeks of expiry to pull
ExpiryOut = 3


database_host = _os.environ.get("OL7_DB_HOST", "localhost")
database_user = _os.environ.get("OL7_DB_USER", "rk_admin")
database_password = _os.environ.get("OL7_DB_PASSWORD", "rk2admin!")
database_schema = _os.environ.get("OL7_DB_SCHEMA", "ol7")
database_schema_model = _os.environ.get("OL7_DB_SCHEMA_MODEL", "model")
