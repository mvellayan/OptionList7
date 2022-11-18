import datetime
import numpy as np
import pandas as pd
import timeit
from common import data_prep_common as dc

def main():

    print("_____________________________________________________")
    print("  PATH:", dc.FILE_GROUPS)
    df = dc.load_data(dc.FILE_GROUPS)
    df = dc.dedup(df, 390)
    print("_____________________________________________________")


start_time = datetime.datetime.now()
main()
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())
print(dc.tn() + "2-report-missing-data done!")