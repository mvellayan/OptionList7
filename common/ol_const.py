from datetime import datetime, timedelta, time

REFERENCE_DIR = "../data/reference/"
DATA_DIR = "../data/quotes/"
PROJECTION_DIR = "../data/projection/"
todo_file = "../data/status/todo.csv"
stock_list_json = "../data/reference/stock-list.json"
option_list_csv = "../data/reference/option-list-*.csv"

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


database_host = 'localhost'
database_user = 'rk_admin'
database_password = 'rk2admin!'
database_schema = 'ol7'
database_schema_model = 'model'
