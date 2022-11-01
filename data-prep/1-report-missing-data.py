import datetime
import numpy as np
import pandas as pd
import timeit
import data_prep_common as dc

FILE_GROUPS=["../data/raw/TSLA/TSLA-BID_ASK", "../data/raw/TSLA/TSLA-TRADES", "../data/raw/VIX/VIX-TRADES"]


def main():

    for fpath in FILE_GROUPS:
        print("_____________________________________________________")
        print("  PATH:", fpath)
        df = dc.load_data(fpath)
        df = dc.dedup(df)
        print("_____________________________________________________")


start_time = datetime.datetime.now()
main()
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())