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
DATA_DIR = "../data/quotes/"
TODO_FILE = "../data/status/todo.csv"
config_json = "../data/reference/stock-list.json"
FILE_GROUPS=["../data/raw/AAPL/?q-BID_ASK-*csv", "../data/raw/AAPL/?q-TRADES-*csv"]

StrikeRange = 2
ExpiryOut = 3

def tn():
    return datetime.datetime.now().strftime("%H:%M:%S") + ": "

global_ib = IB()
def getIB():
    global global_ib
    if not global_ib.isConnected():
        global_ib.connect('127.0.0.1', 7496, clientId=1)
    return global_ib


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
    df['secType'] = 'OPT'
    return df


def getYear(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[0:4]


def getMonth(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[4:6]


def getDay(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[6:8]

"""
Creates contract object from parameter dictionary 
"""
def getContract(data: dict):

    return Contract(symbol=data["symbol"], secType=data["secType"],
                    currency=data["currency"], exchange=data["exchange"],
                    conId=data["conId"], includeExpired=False)


def check_pull_historical_quote_to_file(pDate, contract):
    for sq_type in ['BID_ASK', 'TRADES']:
        if contract.secType == "STK":
            sym = contract.symbol.replace(" ", "")
        else:
            sym = contract.localSymbol.replace(" ", "")
        fn = DATA_DIR + getYear(pDate) + "/" + getMonth(pDate) + "/" + getDay(pDate) + "/sq-" + sq_type + "-" + sym + ".csv"
        if os.path.exists(fn):
            df = pd.read_csv(fn, index_col=None)
        else:
            ib = getIB()
            bars = ib.reqHistoricalData(contract, endDateTime=pDate + " 16:00:00",
                                        durationStr='5 D', barSizeSetting='1 min',
                                        whatToShow=sq_type, useRTH=True)
            if len(bars) > 0:
                df = util.df(bars)
                df['symbol'] = contract.symbol
                df['localSymbol'] = contract.localSymbol
                df['conId'] = contract.conId
                # get unique dates in df

                dates = df['date'][::].astype(str).str.slice(stop=10).unique()
                # for each date, filter rows & save
                for date_ in dates:
                    fn2 = DATA_DIR + getYear(date_) + "/" + getMonth(date_) + "/" + getDay(date_) + "/sq-" + sq_type + "-" + sym + ".csv"
                    Path(fn2).parent.mkdir(parents=True, exist_ok=True)
                    df_ = df.loc[df['date'][::].astype(str).str.slice(stop=10) == date_]
                    df_.to_csv(fn2, index=False)
            else:
                df = pd.DataFrame()
                break
    return df


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
