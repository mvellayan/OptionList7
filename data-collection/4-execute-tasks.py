import datetime
import os
import time
from pprint import pprint
from ib_insync import *
import common.data_prep_common as dc
import pandas as pd
import pathlib

"""
   4-execute-tasks
   1. Read todo.csv
    loop over todo.csv
        call pull-history
    update todo.csv
"""

def execute_todos(todo_file):

    # 1. Read to "status/todo.csv" file
    if not os.path.exists(todo_file):
        print(dc.tn(), "no todo file: ", todo_file)
        exit(1)

    todo_csv = pd.read_csv(todo_file, index_col=None)
    todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)

    ind = 0
    while ind < todo_csv.shape[0]:
        if todo_csv.iloc[ind]['status'] > '4':
            ind += 1
            continue
        print(dc.tn() + f"  processing: {ind}/{todo_csv.shape[0]}: {todo_csv.iloc[ind]['localSymbol']}")
        c = Contract(conId=todo_csv.iloc[ind]['conId'],
                     secType=todo_csv.iloc[ind]['secType'],
                     exchange=todo_csv.iloc[ind]['exchange'],
                     symbol=todo_csv.iloc[ind]['symbol'],
                     localSymbol=todo_csv.iloc[ind]['localSymbol'],
                     currency='USD')
        df = dc.check_pull_historical_quote_to_file(str(todo_csv.iloc[ind]['pull_date']), c)
        if df.shape[0] == 0:
            todo_csv.at[ind, 'status'] = '9-error'
        else:
            todo_csv.at[ind, 'status'] = '5-done'
        todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
        # Saves back to todo.csv file
        todo_csv.to_csv(todo_file, index=False)
        ind += 1


if __name__ == "__main__":
    execute_todos(dc.TODO_FILE)
    print(dc.tn() + "4-execute-tasks done!")
