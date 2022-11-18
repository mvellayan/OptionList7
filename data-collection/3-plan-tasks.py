import datetime
import os
import time
from pprint import pprint
from ib_insync import *
import common.data_prep_common as dc
import pandas as pd
import pathlib

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

def plan_tasks(pDate):
    configStocks = dc.getConfig(dc.config_json)
    stock = dc.getContract(configStocks.get("stocks")[0]['contract'])
    df2 = dc.check_pull_historical_quote_to_file(pDate, stock)
    min_, max_ = df2['open'].agg(['min', 'max'])

    optionList = dc.getOptionlist(stock, pDate, min_, max_, dc.StrikeRange, dc.ExpiryOut)
    optionList['status'] = '1-todo'
    # print(optionList)
    # 5. Output to "status/todo.csv" file
    if os.path.exists(dc.TODO_FILE):
        todo_csv = pd.read_csv(dc.TODO_FILE, index_col=None)
    else:
        todo_csv = pd.DataFrame()

    optionList["pull_date"] = pDate
    todo_csv = pd.concat([optionList, todo_csv], axis=0, ignore_index=True)
    print(dc.tn() + f"Superset shape:", todo_csv.shape)

    #todo_csv.drop_duplicates(subset=['conId'], keep='first', inplace=True)
    todo_csv = todo_csv.sort_values('status', ascending=False).drop_duplicates('conId').sort_index()

    #  Saves back to todo.csv file
    todo_csv.to_csv(dc.TODO_FILE, index=False)
    print(dc.tn() + f"No dup shape:", todo_csv.shape)


if __name__ == "__main__":
    pDate = "20221115"
    plan_tasks(pDate)
    print(dc.tn() + "3-plan-tasks done!")

