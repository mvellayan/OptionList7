import datetime
import os
import time
from ib_insync import *
import common.data_prep_common as dc

# -- do not use, only 1 rec/day: whatToShow = 'HISTORICAL_VOLATILITY'
# https://interactivebrokers.github.io/tws-api/historical_bars.html
# Type        Open	         High	         Low	        Close	      Volume
# ----------  -------------- -------------   -------------  ------------  -----------
# TRADES	  First          Highest         Lowest         Last          Total
#             traded price                                                traded Vol
# BID_ASK	  Time average   Max Ask	     Min Bid	    Time average  N/A
#             Bid                                            ask
# HISTORICAL  Starting       Highest         Lowest          Last          N/A
# _VOLATILITY volatility	 volatility	     volatility	     volatility
#
# - Valid durationStr
#    Unit	Description
#    S	Seconds
#    D	Day
#    W	Week
#    M	Month
#    Y	Year
#
# - Valid Bar Sizes
#    1 secs	5 secs	10 secs	15 secs	30 secs
#    1 min	2 mins	3 mins	5 mins	10 mins	15 mins	20 mins	30 mins
#    1 hour	2 hours	3 hours	4 hours	8 hours
#    1 day
#    1 week
#    1 month

#
# os.system("say Starting!")

t930 = datetime.time(9, 30, 0)
t1600 = datetime.time(16, 0, 0)
t1630 = datetime.time(16, 30, 0)

def pull_and_save_data(ib, contract, endDateTime, durationStr: str,
                       barSizeSetting: str, whatToShow: str, outFileName: str):
    barsList = []
    bars = None
    print(dc.tn(), "      pull_and_save_data:", whatToShow, contract, durationStr, barSizeSetting, endDateTime)

    try:
        bars = ib.reqHistoricalData(contract, endDateTime=endDateTime, durationStr=durationStr,
                                barSizeSetting=barSizeSetting, whatToShow=whatToShow, useRTH=True, formatDate=1)
    except Exception as e:
        print(e)
        exit(1)

    if not bars:
        print(dc.tn(), "empty data returned for endDateTime", endDateTime)
        print(dc.tn(), "exiting.")
        return

    for x in bars:
        if t930 <= x.date.time() <= t1600:
            barsList.append(x)

    endDateTime = bars[0].date
    if endDateTime.time() <= t930:
        print(dc.tn(), "      endDateTime=", endDateTime)
        dt = datetime.timedelta(days=-1)
        endDateTime = endDateTime + dt
        endDateTime = endDateTime.replace(hour=16, minute=0, second=0)
        print(dc.tn(), "      Replaced with =", endDateTime)
    if endDateTime.time() >= t1630:
        print(dc.tn(), "      endDateTime=", endDateTime)
        endDateTime = endDateTime.replace(hour=16, minute=0, second=0)
        print(dc.tn(), "      Replaced with =", endDateTime)
        os.system("say data collection unexpectedly stopped")

    dc.writeArrToFile(barsList, outFileName)
    return endDateTime


def main():
    ib = IB()
    ib.connect('127.0.0.1', 7496, clientId=1)
    DATA_DIR = "../data/raw/"
    PARAM_DIR = "../config/"

    configFile = dc.getConfig(DATA_DIR, PARAM_DIR)
    configs = configFile.get("contracts")
    for contract_idx in range(len(configs)):
        pull_spec = configs[contract_idx]
        contract = dc.getContract(pull_spec['contract'])
        endDateTime = dc.getDateObj(pull_spec["endDateTime"])
        startDateTime = dc.getDateObj(pull_spec["startDate"])
        durationStr = pull_spec["durationStr"]
        barSizeSetting = pull_spec["barSizeSetting"]

        while endDateTime >= startDateTime:
            print(dc.tn(), "Pulling:", contract.conId, "(", contract.conId, ") from", startDateTime, ' -to-', endDateTime)

            whatToShow = 'TRADES'
            outFileName = DATA_DIR + contract.symbol + "/" + whatToShow + "-" + str(round(time.time())) + '.csv'
            newEndDateTime = pull_and_save_data(ib, contract, endDateTime, durationStr, barSizeSetting, whatToShow, outFileName)
            ib.sleep(20)

            whatToShow = 'BID_ASK'
            outFileName = DATA_DIR + contract.symbol + "/" + whatToShow + "-" + str(round(time.time())) + '.csv'
            newEndDateTime = pull_and_save_data(ib, contract, endDateTime, durationStr, barSizeSetting, whatToShow, outFileName)
            ib.sleep(20)

            endDateTime = newEndDateTime
            configFile.get("contracts")[contract_idx]["endDateTime"] = dc.getStrFromDate(newEndDateTime)
            dc.writeJsonDict("../config/workingConfig.json", configFile, overwrite=True, debugOutput=True)


if __name__ == "__main__":
    main()

os.system("say app done")
