import sys
import os
import datetime
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))

from datetime import datetime, timedelta

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
    # only look at last 30 days!
    cutoffDate = int(str((datetime.today() - timedelta(30)).date()).replace("-", ""))
    if int(sDate) < cutoffDate:
        return

    # read current quotes to figure out min/max trading range
    df2 = oli.check_pull_historical_quote_to_file(sDate, stock)
    min_, max_ = df2['open'].agg(['min', 'max'])

    # build list of options to pull
    optionList = olpd.getOptionlist(stock, sDate, min_, max_, olc.StrikeRange, olc.ExpiryOut)
    # if there are no rows, return!!
    if optionList.shape[0] == 0:
        print(f"No options defined for date: {sDate} trading range: {min_} - {max_}")
        return
    optionList = optionList.append(
        {'conId': stock.conId, 'symbol': stock.symbol, 'exchange': stock.exchange, 'secType': stock.secType},
        ignore_index=True)
    optionList = optionList.append({'conId': '13455763', 'symbol': 'VIX', 'exchange': 'CBOE', 'secType': 'IND'},
                                   ignore_index=True)
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

    # pull for past 15/22 days
    # for idx in range(15):
    for idx in range(22):
        current_list = optionList.copy()
        pDate = str(round(working_days.loc[idx]['working_date']))
        current_list["pull_date"] = pDate
        todo_csv = pd.concat([current_list, todo_csv], axis=0, ignore_index=True)

    todo_csv['conId'] = pd.to_numeric(todo_csv['conId'], downcast='integer')
    todo_csv['pull_date'] = pd.to_numeric(todo_csv['pull_date'], downcast='integer')
    todo_csv = todo_csv.sort_values(['conId', 'pull_date', 'status'], ascending=False)
    todo_csv.drop_duplicates(subset=['conId', 'pull_date'], keep='first', inplace=True)
    todo_csv = todo_csv.sort_values(['pull_date', 'conId', 'status'], ascending=False)

    #todo_csv = todo_csv.sort_values('status', ascending=False).drop_duplicates(['conId', 'pull_date']).sort_index()

    #  Saves back to todo.csv file
    todo_csv.to_csv(olc.todo_file, index=False)
    print(olu.tn() + f"  Creating tasks for {pDate}.  Adding {optionList.shape} new total {todo_csv.shape}")


def write_todo_to_file():
    if os.path.exists(olc.todo_file):
        todo_csv = pd.read_csv(olc.todo_file, index_col=None)
    else:
        print ("Unexpected")
        exit(1)

    for conid2 in todo_csv["conId"].unique():
        opt_type = str(todo_csv[todo_csv['conId'] == conid2]["secType"].min())
        if opt_type != "OPT":
            continue
        min = str(todo_csv[todo_csv['conId'] == conid2]["pull_date"].min())
        max = "20" + todo_csv[todo_csv['conId'] == conid2]["localSymbol"].iloc[0].strip()[6:12]
        min_date = datetime.strptime(min, "%Y%m%d")
        max_date = datetime.strptime(max, "%Y%m%d")
        oneday = timedelta(days=1)
        while min_date < max_date:
            min_date += oneday
            wrkday = todo_dates.loc[(todo_dates['working_date'] == int(min_date.strftime("%Y%m%d")))]
            if (wrkday.shape[0]==0):
                continue
            chkpd = todo_csv[(todo_csv['conId'] == conid2) & (todo_csv['pull_date'].astype(str) == min_date.strftime("%Y%m%d"))];
            if (chkpd.shape[0]==0):
                row1 = todo_csv[todo_csv['conId'] == conid2].iloc[[0]].copy()
                row1["pull_date"] = min_date.strftime("%Y%m%d")
                row1["status"] = "1-todo"
                todo_csv = pd.concat([todo_csv, row1])
        olpd.save_todo_csv(todo_csv)


if __name__ == "__main__":
    print(olu.tn() + "3-planed-tasks Starting!")

    # 1. build list of dates
    todo_dates = pd.read_csv(olc.market_days, index_col=None)
    todo_dates = todo_dates.astype({"working_date": int, "working_hour": float})

    lp = todo_dates.loc[(todo_dates['working_date'] > olc.STOCK_PULL_START_DATE) & (todo_dates['working_date'] <= olc.STOCK_PULL_END_DATE)]
#    lp = lp.sort_values('working_date', ascending=False)

    if todo_dates.loc[todo_dates['working_date'] > olc.STOCK_PULL_END_DATE].shape[0] == 0:
        print("NO CURRENT WORKING DATE.  fix market-days.csv file!!")
        exit(1)

    #2. get stock.
    # Hard coded for the 1st one -- AAPL
    # TODO loop around a list
    configStocks = olu.getConfig(olc.stock_list_json)
    stock = oli.getContract(configStocks.get("stocks")[0]['contract'])

    #Loop for each date
    lp['working_date'].apply(plan_tasks, stock=stock)

    print(olu.tn() + "Filling in missing quotes!")

    write_todo_to_file()

    print(olu.tn() + "3-plan-tasks done!")
