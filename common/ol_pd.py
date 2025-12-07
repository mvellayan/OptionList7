import datetime
import glob

import pandas as pd
from ib_insync import *

import common.ol_const as olc


def load_data(file_str: str, recursive=False, batch_size=None):
    """
    Load CSV files matching pattern into a single DataFrame.

    Args:
        file_str: Glob pattern for files to load
        recursive: Enable recursive directory search
        batch_size: If specified, process files in batches to reduce memory usage

    Returns:
        Combined DataFrame from all matching files
    """
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

    # Collect all files first
    files = list(glob.glob(file_str, recursive=recursive))

    if len(files) == 0:
        return pd.DataFrame()

    print(f"          Found {len(files)} files to load")

    # Optimized: collect all DataFrames first, then concatenate once
    df_list = []
    for idx, file in enumerate(files, 1):
        df2 = pd.read_csv(file)
        df_list.append(df2)

        # Print progress every 1000 files
        if idx % 1000 == 0:
            print(f"          Loaded {idx}/{len(files)} files...")

    print(f"          Concatenating {len(df_list)} DataFrames...")
    df = pd.concat(df_list, ignore_index=True)
    print(f"          Total rows: {len(df):,}")

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


def getOptionlist(contract: Contract, sDate: str, min_, max_, strikeRange: int = 2, expiryOut: int = 3):
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
    dDate = datetime.datetime.strptime(sDate, '%Y%m%d')
    friday = dDate + datetime.timedelta((4 - dDate.weekday()) % 7)
    for x in range(len(expiry)):
        if idx == -1 and str(expiry[x]) == friday.strftime('%Y%m%d'):
            idx = x
            break
    if idx == -1:  # expiry date found, return empty df
        return pd.DataFrame()
    # TODO loop around expiryOut instead of hard coded 3
    exp1 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx]]
    exp2 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx + 1]]
    exp3 = df.loc[df['lastTradeDateOrContractMonth'] == expiry[idx + 2]]
    df = pd.concat([exp1, exp2, exp3], axis=0, ignore_index=True)
    df['secType'] = 'OPT'
    return df

def save_todo_csv(todo_csv):
    todo_csv['conId'] = pd.to_numeric(todo_csv['conId'], downcast='integer')
    todo_csv['pull_date'] = pd.to_numeric(todo_csv['pull_date'], downcast='integer')
    todo_csv = todo_csv.sort_values(['conId', 'pull_date', 'status'], ascending=False)
    todo_csv.drop_duplicates(subset=['conId', 'pull_date'], keep='first', inplace=True)
    #todo_csv = todo_csv.sort_values(['pull_date', 'conId'], ascending=False)
    todo_csv = todo_csv.sort_values(['lastTradeDateOrContractMonth', 'pull_date', 'conId'], ascending=[True, False, True])

    # todo_csv = todo_csv.sort_values('status', ascending=False).drop_duplicates(['conId', 'pull_date']).sort_index()
    #  Saves back to todo.csv file
    todo_csv.to_csv(olc.todo_file, index=False)
