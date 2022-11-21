import datetime
import numpy as np
import pandas as pd
import timeit
import common.ol_const as olc
import common.ol_data as old
import common.ol_ib as oli
import common.ol_util as olu


def main():

    print("_____________________________________________________")
    print("  PATH:", olu.FILE_GROUPS)
    df = old.load_data(olu.FILE_GROUPS)
    df = olu.dedup(df, 390)
    print("_____________________________________________________")


start_time = datetime.datetime.now()
main()
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())
print(olu.tn() + "2-report-missing-data done!")