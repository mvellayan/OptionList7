import sys
import os
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))

from datetime import datetime
from ib_insync import *
import pandas as pd
import common.ol_const as olc
import common.ol_ib as oli
import common.ol_util as olu
import common.ol_pd as olpd
from datetime import timedelta

"""
   4-execute-tasks
   1. Read todo.csv
    loop over todo.csv
        call pull-history
    update todo.csv
"""


def execute_todos(todo_file):
    todo_csv = pd.read_csv(todo_file, index_col=None)
    todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
    todo_csv.sort_values(by=['pull_date', 'localSymbol', 'symbol'], ascending=False, inplace=True)

    ind = 0
    while ind < todo_csv.shape[0]:
        pull_date_str = todo_csv.iloc[ind]['pull_date'].astype(str)

        # if todo_csv.iloc[ind]['lastTradeDateOrContractMonth'] != 20230421:
        #     print('Skipping Not today', todo_csv.iloc[ind]['lastTradeDateOrContractMonth'].astype(str),
        #           '20230421', todo_csv.iloc[ind]['lastTradeDateOrContractMonth'] != 20230421)
        #     ind += 1
        #     continue
        pullDateDate = datetime.strptime(pull_date_str, '%Y%m%d')

        if pullDateDate.weekday() > 4:
            # todo_csv.drop(ind, inplace=True)
            ind += 1
            print("Skipping weekend pull date: ", todo_csv.iloc[ind]['pull_date'].astype(str),
                  " weekday=", pullDateDate.weekday() )
            continue

        if todo_csv.iloc[ind]['status'] > '4':
            ind += 1
            print("Skipping status: " , todo_csv.iloc[ind]['status'])
            continue

        xdate = datetime.now()
        # if (xdate.hour < 16):
        #     xdate = xdate - timedelta(days = 1)
        today_date = xdate.strftime("%Y%m%d")
        if todo_csv.iloc[ind]['pull_date'].astype(str) > today_date:
            print("Skipping future pull date: ", todo_csv.iloc[ind]['pull_date'].astype(str))
            ind += 1
            continue

        print(olu.tn() + f"  processing: {ind}/{todo_csv.shape[0]}: {todo_csv.iloc[ind]['pull_date']} {todo_csv.iloc[ind]['localSymbol']}/{todo_csv.iloc[ind]['symbol']}")
        c = Contract(conId=todo_csv.iloc[ind]['conId'],
                     secType=todo_csv.iloc[ind]['secType'],
                     exchange=todo_csv.iloc[ind]['exchange'],
                     symbol=todo_csv.iloc[ind]['symbol'],
                     localSymbol=todo_csv.iloc[ind]['localSymbol'],
                     currency='USD')
        df = oli.check_pull_historical_quote_to_file(str(todo_csv.iloc[ind]['pull_date']), c)
        if df.shape[0] == 0 and todo_csv.at[ind, 'status'] == '1-todo':
            todo_csv.at[ind, 'status'] = '2-todo'
        elif df.shape[0] == 0 and todo_csv.at[ind, 'status'] == '2-todo':
            todo_csv.at[ind, 'status'] = '3-todo'
        elif df.shape[0] == 0 and todo_csv.at[ind, 'status'] == '3-todo':
            todo_csv.at[ind, 'status'] = '9-error, after 3 tries'
        else:
            todo_csv.at[ind, 'status'] = '5-done'
        todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
        # Saves back to todo.csv file
        olpd.save_todo_csv(todo_csv)
        ind += 1


if __name__ == "__main__":
    execute_todos(olc.todo_file)
    print(olu.tn() + "4-execute-tasks done!")

