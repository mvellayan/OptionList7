import glob
import datetime

import pandas as pd
from pprint import pprint
import json
from os.path import exists
from ib_insync import *
from pathlib import Path
import os

REFERENCE_DIR = "../data/reference/"

def tn():
    return datetime.datetime.now().strftime("%H:%M:%S") + ": "

ib = IB()
def getIB():
    global ib
    if not ib.isConnected():
        ib.connect('127.0.0.1', 7496, clientId=1)
    return ib


def getConfig(config_json: str):
    l_config = readJsonDict(config_json, debugOutput=False)
    return l_config


def load_data(file_str: str, max_files: int = 999):
    # Get CSV files list from a folder
    csv_files = []
    for path in file_str:
        csv_files.extend(glob.glob(path))
    csv_files = csv_files[0: max_files]
    if len(csv_files) == 0:
        print("No files in directory ", file_str, csv_files)
        exit(1)
    print("          loading ", file_str, " file count: " + str(len(csv_files)))
    # Read each CSV file into DataFrame
    # This creates a list of dataframes
    # df_list = (pd.read_csv(file) for file in csv_files)
    # df = pd.concat(df_list, ignore_index=True)
    df = pd.DataFrame()
    for file in csv_files:
        df2 = pd.read_csv(file)
        if "BID_ASK" in file:
            df2['quoteType'] = "BID_ASK"
        elif "TRADES" in file:
            df2['quoteType'] = "TRADES"

        df = pd.concat([df, df2], ignore_index=True)

    return df


def dedup(df, expected_rows_per_day: int):
    # 1.1 Drop duplicates & check for missing values
    dups = len(df['date']) - len(df[['date', 'conId', 'quoteType']].drop_duplicates())
    print("      # of duplicates", dups, ' out of ', len(df), ' or ', round(dups / len(df), 5), '%')
    # Drop duplicate entries
    df.drop_duplicates(subset=['date', 'conId', 'quoteType'], keep='first', inplace=True)

    # Need this col for reporting daily count
    df['date_only'] = df['date'][::].str.slice(stop=10)

    pd_group_cnt = df.groupby(['date_only', 'conId', 'quoteType']).count()
    print(f"      Days with {expected_rows_per_day} Qutoes:")
    print("      ------------------------")
    pd.set_option('display.max_rows', None)
    print(pd_group_cnt.loc[pd_group_cnt['date'] == expected_rows_per_day]['date'])

    print("      Days WRONG # Qutoes:")
    print("      --X--X--X--X--X--X--")
    todoList = pd_group_cnt.loc[pd_group_cnt['date'] != expected_rows_per_day]
    df2 = todoList.reset_index()
    print(todoList['date'])

    df.set_index('date')
    df = df.sort_index()
    pd.set_option('display.max_rows', 10)
    return df, df2


def readJsonDict(fn: str, debugOutput=True):

    data = {}
    if not exists(fn):
        print(f"file {fn} does not exists")
        return data

    with open(fn) as f1:
        data = json.load(f1)

    if debugOutput:
        pprint(data)

    return data


def writeJsonDict(fn: str, data: dict, overwrite=False, debugOutput=True):

    if not overwrite and exists(fn):
        print(f"ERROR: file {fn} exists")
        return

    with open(fn, "w") as outfile:
        json.dump(data, outfile, indent=4)

    if debugOutput:
        pprint(data)

    return data


def writeArrToFile(barsList: [], fn: str, p_conId: int, p_symbol: str):
    if len(barsList) == 0:
        return
    # allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(barsList)
    df["symbol"] = p_symbol
    df["conId"] = p_conId

    Path(fn).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fn, index=False)
    print(f'   Written to file {fn}.  RowCount = {len(barsList)}')


def getOptionlist(contract: Contract, pDate: str, min, max, StrikeRange: int = 2, ExpiryOut: int = 3):
    symbol = contract.symbol.replace(" ", "")[0:4]
    option_list_file = REFERENCE_DIR + "option-list-" + symbol + ".csv"
    # read whole file
    df = pd.read_csv(option_list_file)
    # fileter by base security
    df = df.loc[df['symbol'] == contract.symbol]
    #
    strikes = df['strike'].unique()
    strikes.sort()
    min_idx = -1
    max_idx = -1
    for x in range(len(strikes)):
        if min_idx == -1 and strikes[x] > min:
            min_idx = x - 3
        if max_idx == -1 and strikes[x] > max:
            max_idx = x + 2

    if min_idx < 0: min_idx = 0
    if max_idx > len(strikes): max_idx = len(strikes)
    df = df.loc[df['strike'] >= strikes[min_idx]]
    df = df.loc[df['strike'] <= strikes[max_idx]]

    expiry = df['lastTradeDateOrContractMonth'].unique()
    expiry.sort()
    idx = -1
    dn = datetime.datetime.strptime(pDate, '%Y%m%d')
    friday = dn + datetime.timedelta( (4-dn.weekday()) % 7 )
    for x in range(len(expiry)):
        if idx == -1 and expiry[x] == friday.strftime('%Y%m%d'):
            idx = x
            break
    exp1 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx]]
    exp2 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx+1]]
    exp3 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx+2]]
    df = pd.concat([exp1, exp2, exp3], axis=0, ignore_index=True)
    return df

"""
Creates contract object from parameter dictionary 
"""
def getContract(data: dict):

    return Contract(symbol=data["symbol"], secType=data["secType"],
                    currency=data["currency"], exchange=data["exchange"],
                    conId=data["conId"], includeExpired=False)


t930 = datetime.time(9, 30, 0)
t1600 = datetime.time(16, 0, 0)
t1630 = datetime.time(16, 30, 0)

def pull_historical_data(ib, contract, endDateTime = "", durationStr: str = "1 D",
                         barSizeSetting: str = "1 M", whatToShow: str = "TRADES"):
    barsList=[]
    bars = None
    print(tn(), "      pull_and_save_data:", whatToShow, contract, durationStr, barSizeSetting, endDateTime)

    try:
        bars = ib.reqHistoricalData(contract, endDateTime=endDateTime, durationStr=durationStr,
                                    barSizeSetting=barSizeSetting, whatToShow=whatToShow, useRTH=True, formatDate=1)
    except Exception as e:
        print(e)
        exit(1)

    if not bars:
        print(tn(), "empty data returned for endDateTime", endDateTime)
        print(tn(), "exiting.")
        return

    for x in bars:
        if t930 <= x.date.time() <= t1600:
            barsList.append(x)

    return barsList


def getDateObj(p1):
    if p1 == None:
        return datetime.datetime.now()
    elif isinstance(p1, datetime.datetime):
        return p1
    elif isinstance(p1, str):
        p1 = p1.replace(" ", "")
        if len(p1) == 0:
            return datetime.datetime.now()
        elif len(p1) == 8:
            return datetime.datetime(int(p1[0:4]), int(p1[4:6]), int(p1[6:8]))
        else:
            return datetime.datetime(int(p1[0:4]), int(p1[4:6]), int(p1[6:8]), int(p1[8:10]), int(p1[10:12]), int(p1[12:14]))
    else:
        print(f"unexpected object type {type(p1)}.  Cant convert to date object", p1)
        exit(1)


def getStrFromDate(p1: datetime.datetime):
    return p1.strftime("%Y%m%d %H%M%S")
