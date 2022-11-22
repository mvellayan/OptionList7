import datetime
import glob

import pandas as pd
from ib_insync import *

import common.ol_const as olc


def load_data(file_str: str,  recursive=False):
    # Get CSV files list from a folder
    """
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
    """
    df = pd.DataFrame()
    for file in glob.glob(file_str, recursive=recursive):
        df2 = pd.read_csv(file)
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


def getOptionlist(contract: Contract, pDate: str, min_, max_, strikeRange: int = 2, expiryOut: int = 3):
    symbol = contract.symbol.replace(" ", "")[0:4]
    option_list_file = olc.REFERENCE_DIR + "option-list-" + symbol + ".csv"
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
        if min_idx == -1 and strikes[x] > min_:
            min_idx = x - strikeRange
        if max_idx == -1 and strikes[x] > max_:
            max_idx = x + (strikeRange - 1)

    if min_idx < 0: min_idx = 0
    if max_idx > len(strikes): max_idx = len(strikes)
    df = df.loc[df['strike'] >= strikes[min_idx]]
    df = df.loc[df['strike'] <= strikes[max_idx]]

    expiry = df['lastTradeDateOrContractMonth'].unique()
    expiry.sort()
    idx = -1
    dn = datetime.datetime.strptime(pDate, '%Y%m%d')
    friday = dn + datetime.timedelta((4 - dn.weekday()) % 7)
    for x in range(len(expiry)):
        if idx == -1 and expiry[x] == friday.strftime('%Y%m%d'):
            idx = x
            break
    # TODO loop around expiryOut instead of hard coded 3
    exp1 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx]]
    exp2 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx + 1]]
    exp3 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx + 2]]
    df = pd.concat([exp1, exp2, exp3], axis=0, ignore_index=True)
    df['secType'] = 'OPT'
    return df
