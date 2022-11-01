import glob
import numpy as np
import pandas as pd
import timeit

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
    dups = len(df['date'])-len(df['date'].drop_duplicates())
    print("      # of duplicates", dups, ' out of ', len(df), ' or ', round(dups/len(df), 5), '%')
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
