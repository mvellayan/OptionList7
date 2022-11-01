import datetime
import os
import time

from ib_insync import *

DATA_DIR ="../data/raw/"
MAX_DAYS = 200
MAX_BATCH_PER_FILE = 13
#
endDateTime = ''
endDateTime: datetime = datetime.datetime(2022, 3, 15, 16, 00, 00)
#
# contract = Contract(symbol="AAPL", secType="STK", currency="USD", exchange="SMART", includeExpired=False)
contract = Contract(symbol="TSLA", secType="STK", currency="USD", exchange="SMART", includeExpired=False)
#contract = Contract(conId=13455763, symbol="VIX", secType="IND", exchange="CBOE", currency="USD", includeExpired=False)
#
whatToShow = 'BID_ASK'
#whatToShow = 'TRADES'


# -- do not use, only 1 rec/day: whatToShow = 'HISTORICAL_VOLATILITY'
# https://interactivebrokers.github.io/tws-api/historical_bars.html
# Type        Open	         High	         Low	        Close	      Volume
# ----------  -------------- -------------   -------------  ------------  -----------
# TRADES	  First          Highest         Lowest         Last          Total
#             traded price   traded price    traded price   traded price  traded Vol
# BID_ASK	  Time average   Max Ask	     Min Bid	    Time average  N/A
#             Bid                                            ask
# HISTORICAL  Starting       Highest         Lowest          Last          N/A
# _VOLATILITY volatility	 volatility	     volatility	     volatility

#
# os.system("say Starting!")

def writeToFile():
    global barsList
    if len(barsList) == 0:
        return
    # allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(barsList)
    fn = DATA_DIR + contract.symbol + "/" + contract.symbol + "-" + whatToShow + "-" + str(round(time.time())) + '.csv'
    df.to_csv(fn, index=False)
    barsList = []
    print(f'   Written to file {fn}.  Next dt = ', endDateTime)


ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)

t930 = datetime.time(9, 30, 0)
t1600 = datetime.time(16, 0, 0)
t1630 = datetime.time(16, 30, 0)
barsList = []
ctr_total = 0

while ctr_total < (MAX_BATCH_PER_FILE * MAX_DAYS):  # 7 30min dur * MAX_DAYS days
    ctr_total += 1
    print(datetime.datetime.now(), 'Starting Request: ctr_total', ctr_total,  'next timestamp', endDateTime)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=endDateTime,
        # durationStr='1800 S',
        durationStr='1800 S',
        barSizeSetting='1 secs',
        whatToShow=whatToShow,
        useRTH=True,
        formatDate=1)
    if not bars:
        print("empty data returned for endDateTime", endDateTime)
        print("exiting.")
        writeToFile()
        exit()
    for x in bars:
        if x.date.time() >= t930 and x.date.time() <= t1600:
            barsList.append(x)
    print("      Return count: ", len(bars), len(barsList),  " for endDateTime: ", endDateTime, ' Next endDateTime: ', bars[0].date)

    endDateTime = bars[0].date
    if endDateTime.time() <= t930:
        print("      endDateTime=",  endDateTime)
        dt = datetime.timedelta(days=-1)
        endDateTime = endDateTime + dt
        endDateTime = endDateTime.replace(hour=16, minute=0, second=0)
        print("      Replaced with =", endDateTime)
    if endDateTime.time() >= t1630:
        print("      endDateTime=", endDateTime)
        endDateTime = endDateTime.replace(hour=16, minute=0, second=0)
        print("      Replaced with =", endDateTime)
        os.system("say data collection unexpectedly stopped")

    ib.sleep(20)
    # flush to file every so often
    if (ctr_total % MAX_BATCH_PER_FILE) == 0:
        writeToFile()
# final write to file
writeToFile()
os.system("say app done")