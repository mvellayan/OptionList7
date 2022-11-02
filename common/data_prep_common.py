import glob
import datetime

import pandas as pd
from pprint import pprint
import json
from os.path import exists
from ib_insync import *
from pathlib import Path


def tn():
    return datetime.datetime.now().strftime("%H:%M:%S") + ": "


def load_data(data_dir: str, max_files: int = 999):
    # Get CSV files list from a folder
    file_str = data_dir + "-*.csv"
    csv_files = glob.glob(file_str)
    csv_files = csv_files[0:max_files]
    if len(csv_files) == 0:
        print("No files in directory ", file_str, csv_files)
        exit(1)
    print("          loading " + file_str + " file count: " + str(len(csv_files)))
    # Read each CSV file into DataFrame
    # This creates a list of dataframes
    df_list = (pd.read_csv(file) for file in csv_files)
    # Concatenate all DataFrames
    df = pd.concat(df_list, ignore_index=True)
    # Only want to track average to 3 decimal places.  Otherwise, end up with a lot of digits
    return df


def dedup(df):
    # 1.1 Drop duplicates & check for missing values
    dups = len(df['date']) - len(df['date'].drop_duplicates())
    print("      # of duplicates", dups, ' out of ', len(df), ' or ', round(dups / len(df), 5), '%')
    # Need this col for dedup
    df['date2_str'] = df['date'][::].str.slice(stop=10)
    # Drop duplicate entries
    df.drop_duplicates(subset=['date'], keep='first', inplace=True)

    pd_group_cnt = df.groupby(['date2_str'])['date2_str'].count().to_frame()
    print("      Days with 23,400 Qutoes:")
    print("      ------------------------")
    pd.set_option('display.max_rows', None)
    print(pd_group_cnt.loc[pd_group_cnt['date2_str'] == 23400])

    print("      Days WRONG # Qutoes:")
    print("      --------------------")
    print(pd_group_cnt.loc[pd_group_cnt['date2_str'] != 23400])
    # df = df.drop('date2_str', axis=1)
    df.set_index('date')
    df = df.sort_index()
    pd.set_option('display.max_rows', 10)
    return df


def getConfig(fn: str, debugOutput=True):

    data = {}

    if not exists(fn):
        print(f"file {fn} does not exists")
        return data

    with open(fn) as f1:
        data = json.load(f1)

    if debugOutput:
        pprint(data)

    return data

def writeConfigs(fn: str, data: dict, overwrite=False, debugOutput=True):

    if not overwrite and exists(fn):
        print(f"ERROR: file {fn} exists")
        return

    with open(fn, "w") as outfile:
        json.dump(data, outfile, indent=4)

    if debugOutput:
        pprint(data)

    return data


def writeArrToFile(barsList: [], fn: str):
    if len(barsList) == 0:
        return
    # allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(barsList)

    Path(fn).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fn, index=False)
    print(f'   Written to file {fn}.  RowCount = {len(barsList)}')


"""
Creates contract object from parameter dictionary 
"""
def getContract(data: dict):

    return Contract(symbol=data["symbol"], secType=data["secType"],
                    currency=data["currency"], exchange=data["exchange"],
                    conId=data["conId"], includeExpired=False)

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
