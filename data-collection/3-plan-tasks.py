import os
import pandas as pd
import common.ol_const as olc
import common.ol_data as old
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


def plan_tasks(pDate: str):
    if type(pDate) in [int]:
        pDateInt = pDate
        pDate = str(round(pDate))
    else:
        pDateInt = int(pDate)

    print(olu.tn() + f"  creating tasks for {pDate}")
    configStocks = olu.getConfig(olc.config_json)
    stock = oli.getContract(configStocks.get("stocks")[0]['contract'])
    df2 = oli.check_pull_historical_quote_to_file(pDate, stock)
    min_, max_ = df2['open'].agg(['min', 'max'])

    optionList = old.getOptionlist(stock, pDate, min_, max_, olc.StrikeRange, olc.ExpiryOut)
    optionList = optionList.append(
        {'conId': stock.conId, 'symbol': stock.symbol, 'exchange': stock.exchange, 'secType': stock.secType},
        ignore_index=True)
    optionList = optionList.append({'conId': '13455763', 'symbol': 'VIX', 'exchange': 'CBOE', 'secType': 'IND'},
                                   ignore_index=True)
    optionList['status'] = '1-todo'

    working_days = pd.read_csv(olc.working_days, index_col=None)
    working_days = working_days.loc[working_days['working_date'] <= pDateInt]
    working_days = working_days.sort_values(by=['working_date'], ascending=False)
    working_days = working_days.reset_index(drop=True)

    # 5. Output to "status/todo.csv" file
    if os.path.exists(olc.todo_file):
        todo_csv = pd.read_csv(olc.todo_file, index_col=None)
    else:
        todo_csv = pd.DataFrame()

    for idx in range(15):
        pDate = working_days.loc[idx]['working_date']
        pDate = str(round(pDate))
        current_list = optionList
        current_list["pull_date"] = pDate
        todo_csv = pd.concat([current_list, todo_csv], axis=0, ignore_index=True)

    # todo_csv.drop_duplicates(subset=['conId'], keep='first', inplace=True)
    todo_csv = todo_csv.sort_values('status', ascending=False).drop_duplicates(['conId', 'pull_date']).sort_index()

    #  Saves back to todo.csv file
    todo_csv.to_csv(olc.todo_file, index=False)
    print(olu.tn() + f"    adding tasks {optionList.shape} new total {todo_csv.shape}")


if __name__ == "__main__":
    todo_dates = pd.read_csv(olc.working_days, index_col=None)
    lp = todo_dates.loc[(todo_dates['working_date'] > 20220500) & (todo_dates['working_date'] < 20221119)]
    lp = lp.sort_values('working_date', ascending=False)
    lp['working_date'].apply(plan_tasks)
    print(olu.tn() + "3-plan-tasks done!")
