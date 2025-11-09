import sys
import os
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))

from datetime import datetime, timedelta
from ib_insync import *
import pandas as pd
import common.ol_const as olc
import common.ol_ib as oli
import common.ol_util as olu
import common.ol_pd as olpd

"""
   4-execute-tasks
   1. Read todo.csv
    loop over todo.csv
        call pull-history
    update todo.csv
"""


def execute_todos(todo_file, save_interval=10):
    """
    Execute todo tasks from CSV file.

    Args:
        todo_file: Path to the todo CSV file
        save_interval: Save progress every N tasks (default: 10)
    """
    todo_csv = pd.read_csv(todo_file, index_col=None)
    todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)

    todo_csv.sort_values(by=['pull_date', 'localSymbol', 'symbol'], ascending=False, inplace=True)
    todo_csv.reset_index(inplace=True, drop=True)

    # Pre-convert pull_date to string for all rows to avoid repeated conversions
    todo_csv['pull_date_str'] = todo_csv['pull_date'].astype(str)

    # Calculate today_date once outside the loop
    xdate = datetime.now()
    today_date = xdate.strftime("%Y%m%d")

    total_rows = todo_csv.shape[0]
    tasks_since_save = 0

    for ind in range(total_rows):
        row = todo_csv.iloc[ind]

        # Skip if status is done or error (> '4')
        if row['status'] > '4':
            continue

        # Skip future dates
        if row['pull_date_str'] > today_date:
            continue

        print(olu.tn() + f"  processing: {ind}/{total_rows}: {row['pull_date']} {row['localSymbol']}/{row['symbol']}")

        c = Contract(
            conId=row['conId'],
            secType=row['secType'],
            exchange=row['exchange'],
            symbol=row['symbol'],
            localSymbol=row['localSymbol'],
            currency='USD'
        )

        df = oli.check_pull_historical_quote_to_file(row['pull_date_str'], c)

        # Update status based on result
        current_status = row['status']
        if df.shape[0] == 0:
            if current_status == '1-todo':
                todo_csv.at[ind, 'status'] = '2-todo'
            elif current_status == '2-todo':
                todo_csv.at[ind, 'status'] = '3-todo'
            elif current_status == '3-todo':
                todo_csv.at[ind, 'status'] = '9-error, after 3 tries'
        else:
            todo_csv.at[ind, 'status'] = '5-done'

        tasks_since_save += 1

        # Save periodically instead of after every task
        if tasks_since_save >= save_interval:
            todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
            olpd.save_todo_csv(todo_csv)
            tasks_since_save = 0

    # Final save for any remaining changes
    if tasks_since_save > 0:
        todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
        olpd.save_todo_csv(todo_csv)


if __name__ == "__main__":
    execute_todos(olc.todo_file)
    print(olu.tn() + "4-execute-tasks done!")

