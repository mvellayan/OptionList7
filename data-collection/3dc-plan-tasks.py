import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

from tqdm import tqdm

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))

import pandas as pd
import common.ol_const as olc
import common.ol_pd as olpd
import common.ol_ib as oli
import common.ol_util as olu
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

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

def plan_tasks(iDate: int, stock):
    sDate = str(iDate)
    # This check is not needed.  It has already been performed by the caller.
    # only look at last 30 days!
    # cutoffDate = int(str((datetime.today() - timedelta(30)).date()).replace("-", ""))
    # if int(sDate) < cutoffDate:
    #    return

    # read current quotes to figure out min/max trading range
    df2 = oli.check_pull_historical_quote_to_file(sDate, stock)
    if df2.shape[0] == 0:
        print(f"No options defined for date: {sDate} trading range")
        return

    min_, max_ = df2['open'].agg(['min', 'max'])

    # build list of options to pull
    optionList = olpd.getOptionlist(stock, sDate, min_, max_, olc.StrikeRange, olc.ExpiryOut)
    # if there are no rows, return!!
    if optionList.shape[0] == 0:
        print(f"No options defined for date: {sDate} trading range: {min_} - {max_}")
        return

    # Use pd.concat instead of deprecated append()
    additional_rows = pd.DataFrame([
        {'conId': stock.conId, 'symbol': stock.symbol, 'exchange': stock.exchange, 'secType': stock.secType},
        {'conId': '13455763', 'symbol': 'VIX', 'exchange': 'CBOE', 'secType': 'IND'}
    ])
    optionList = pd.concat([optionList, additional_rows], ignore_index=True)
    optionList['status'] = '1-todo'

    # build a list of working days to pull quotes
    # less than equal to parameter date
    working_days = pd.read_csv(olc.market_days, index_col=None)
    working_days = working_days.loc[working_days['working_date'] <= iDate]
    working_days = working_days.sort_values(by=['working_date'], ascending=False)
    working_days = working_days.head(28)  # pull only 3 weeks of data
    working_days = working_days.reset_index(drop=True)

    # read previous list of todo tasks
    if os.path.exists(olc.todo_file):
        todo_csv = pd.read_csv(olc.todo_file, index_col=None)
    else:
        todo_csv = pd.DataFrame()

    # pull for past 15/22 days - collect all in list first, then concatenate once
    task_lists = []
    for idx in range(22):
        current_list = optionList.copy()
        pDate = str(round(working_days.loc[idx]['working_date']))
        current_list["pull_date"] = pDate
        task_lists.append(current_list)

    # Single concatenation instead of 22 separate ones
    if task_lists:
        new_tasks = pd.concat(task_lists, axis=0, ignore_index=True)
        todo_csv = pd.concat([new_tasks, todo_csv], axis=0, ignore_index=True)

    todo_csv['conId'] = pd.to_numeric(todo_csv['conId'], downcast='integer')
    todo_csv['pull_date'] = pd.to_numeric(todo_csv['pull_date'], downcast='integer')

    # Combined sort and dedup in single operation
    todo_csv = todo_csv.sort_values(['conId', 'pull_date', 'status'], ascending=False)
    todo_csv.drop_duplicates(subset=['conId', 'pull_date'], keep='first', inplace=True)
    todo_csv = todo_csv.sort_values(['pull_date', 'conId', 'status'], ascending=False)

    #  Saves back to todo.csv file
    todo_csv.to_csv(olc.todo_file, index=False)
    print(olu.tn() + f"  Creating tasks for {sDate}.  Adding {optionList.shape} new total {todo_csv.shape}")


def write_todo_to_file():
    if os.path.exists(olc.todo_file):
        todo_csv = pd.read_csv(olc.todo_file, index_col=None)
    else:
        print("Unexpected")
        exit(1)

    # Create a set of working dates for faster lookup
    working_dates_set = set(todo_dates['working_date'].values)

    # Collect all new rows first, then concatenate once at the end
    new_rows = []

    for conid2 in todo_csv["conId"].unique():
        # Filter once for this conId
        conid_rows = todo_csv[todo_csv['conId'] == conid2]

        opt_type = str(conid_rows["secType"].min())
        if opt_type != "OPT":
            continue

        min_pull = str(conid_rows["pull_date"].min())
        max_symbol = "20" + conid_rows["localSymbol"].iloc[0].strip()[6:12]
        min_date = datetime.strptime(min_pull, "%Y%m%d")
        max_date = datetime.strptime(max_symbol, "%Y%m%d")

        # Get existing pull_dates for this conId for faster lookup
        existing_dates = set(conid_rows['pull_date'].astype(str).values)

        # Template row for this conId
        template_row = conid_rows.iloc[[0]].copy()

        oneday = timedelta(days=1)
        current_date = min_date
        while current_date < max_date:
            current_date += oneday
            date_str = current_date.strftime("%Y%m%d")
            date_int = int(date_str)

            # Fast set lookup instead of DataFrame filtering
            if date_int not in working_dates_set:
                continue

            if date_str in existing_dates:
                continue

            # Create new row
            new_row = template_row.copy()
            new_row["pull_date"] = date_str
            new_row["status"] = "1-todo"
            new_rows.append(new_row)

    # Single concatenation at the end
    if new_rows:
        todo_csv = pd.concat([todo_csv] + new_rows, ignore_index=True)

    olpd.save_todo_csv(todo_csv)


if __name__ == "__main__":
    print(olu.tn() + "3-planed-tasks Starting!")

    # 1. build list of dates
    todo_dates = pd.read_csv(olc.market_days, index_col=None)
    todo_dates = todo_dates.astype({"working_date": int, "working_hour": float})

    lp = todo_dates.loc[(todo_dates['working_date'] > olc.STOCK_PULL_START_DATE) & (todo_dates['working_date'] <= olc.STOCK_PULL_END_DATE)]
#    lp = lp.sort_values('working_date', ascending=False)

    if lp.shape[0] == 0:
        print("NO CURRENT WORKING DATE.  fix market-days.csv file!!")
        exit(1)

    #2. get stock.
    # Hard coded for the 1st one -- AAPL
    # TODO loop around a list
    configStocks = olu.getConfig(olc.stock_list_json)
    stock = oli.getContract(configStocks.get("stocks")[0]['contract'])

    tqdm.pandas(desc="Working Dates", unit="date", colour="green", ncols=100)
    #Loop for each date
    lp['working_date'].progress_apply(plan_tasks, stock=stock)

    print(olu.tn() + "Filling in missing quotes!")

    write_todo_to_file()

    print(olu.tn() + "3-plan-tasks done!")
