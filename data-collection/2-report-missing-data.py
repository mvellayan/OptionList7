import datetime
import numpy as np
import pandas as pd
import timeit
from common import data_prep_common as dc

FILE_GROUPS=["../data/raw/AAPL/?q-BID_ASK-*csv", "../data/raw/AAPL/?q-TRADES-*csv"]


def main():

    print("_____________________________________________________")
    print("  PATH:", FILE_GROUPS)
    df = dc.load_data(FILE_GROUPS)
    df = dc.dedup(df, 390)
    print("_____________________________________________________")


start_time = datetime.datetime.now()
main()
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())