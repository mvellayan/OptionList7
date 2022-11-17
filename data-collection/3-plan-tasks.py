import datetime
import os
import time
from pprint import pprint
from ib_insync import *
import common.data_prep_common as dc
import pandas as pd
import pathlib

DATA_DIR = "../data/quotes/"
config_json = "../data/reference/stock-list.json"
todo_file = "../data/status/todo.csv"
StrikeRange = 2
ExpiryOut = 3

"""
    3-plan-tasks 
        1. Input Parameter: Date, stockContract
        2. Pull stock quotes to file (if it doesn't exist) 
        3. Find trading range
        4. Build optionlist 
                +/- 15% of trading range
                +3 weeks
                find how many days history to pull
        5. Output to status/todo.csv file
"""

def check_pull_stock(pDate, contract):

    if contract.secType != "STK":
        print ("unexpected stock type:", contract)
        exit(1)

    symbol = contract.symbol.replace(" ", "")[0:4]
    file_trades = DATA_DIR + pDate[0:4] + "/" + pDate[4:6] + "/sq-TRADES-" + contract.symbol.replace(" ", "") + ".csv"

    # 2. Pull stock quotes to file (if it doesn't exist)
    if os.path.exists(file_trades):
        df = pd.read_csv(file_trades, index_col=None)
        print(dc.tn() + f"OptionList file exists. {file_trades}  Loaded shape:", df.shape)
    else:
        ib = dc.getIB()
        for sq_type in ['BID_ASK', 'TRADES']:
            fn = DATA_DIR + pDate[0:4] + "/" + pDate[4:6] + "/sq-" + sq_type + "-" + \
                 contract.symbol.replace(" ", "") + ".csv"
            bars = ib.reqHistoricalData(contract, endDateTime="",
                                        durationStr='1 D', barSizeSetting='1 min',
                                        whatToShow=sq_type, useRTH=True, formatDate=1)

            df = util.df(bars)
            pathlib.Path(fn).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(fn, index=False)
    return df


if __name__ == "__main__":
    pDate= "20221116"
    configStocks = dc.getConfig(config_json)
    stock = dc.getContract(configStocks.get("stocks")[0]['contract'])
    df2 = check_pull_stock(pDate, stock)
    min_, max_ = df2['open'].agg(['min', 'max'])

    optionList = dc.getOptionlist(stock, pDate, min_, max_, StrikeRange, ExpiryOut)
    print(optionList)
    # 5. Output to "status/todo.csv" file
    if os.path.exists(todo_file):
        todo_csv = pd.read_csv(todo_file, index_col=None)
    else:
        todo_csv = pd.DataFrame()

    optionList["pull_date"] = pDate
    todo_csv = pd.concat([optionList, todo_csv], axis=0, ignore_index=True)
    print(todo_csv.tn() + f"Superset shape:", todo_csv.shape)
    todo_csv.drop_duplicates(subset=['conId'], keep='first', inplace=True)
    #  Saves back to todo.csv file
    todo_csv.to_csv(todo_file, index=False)
    print(dc.tn() + f"No dup shape:", todo_csv.shape)

os.system("say app done")
