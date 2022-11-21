from datetime import datetime

REFERENCE_DIR = "../data/reference/"
DATA_DIR = "../data/quotes/"
PROJECTION_DIR = "../data/projection/"
todo_file = "../data/status/todo.csv"
config_json = "../data/reference/stock-list.json"
working_days = "../data/reference/market-working.csv"
FILE_GROUPS=["../data/raw/AAPL/?q-BID_ASK-*csv", "../data/raw/AAPL/?q-TRADES-*csv"]

STOCK_PULL_START_DATE: int = 20220500
STOCK_PULL_END_DATE: int = int(datetime.now().strftime('%Y%m%d'))

# how many strike prices below and above to pull
StrikeRange = 2
# how many weeks of expiry to pull
ExpiryOut = 3


database_host = 'localhost'
database_user = 'rk_admin'
database_password = 'rk2admin!'
database_schema = 'ol7'
