import glob
import datetime

import pandas as pd
from pprint import pprint
import json
from os.path import exists
from ib_insync import *
from pathlib import Path
import os

import common.ol_const as olc
import common.ol_util as olu
from ib_insync import *


global_ib = IB()
def getIB():
    #util.logToConsole('DEBUG')
    global global_ib
    if not global_ib.isConnected():
        global_ib.connect("127.0.0.1", 7496, clientId=1)
    return global_ib

"""
Creates contract object from parameter dictionary 
"""
def getContract(data: dict):

    return Contract(symbol=data["symbol"], secType=data["secType"],
                    currency=data["currency"], exchange=data["exchange"],
                    conId=data["conId"], includeExpired=False)


def check_pull_historical_quote_to_file(sDate:str, contract):
    if type(sDate) != str: 1/0
    for sq_type in ['BID_ASK', 'TRADES']:

        # Vix does not have BID_ASK, only TRADES
        if contract.symbol == 'VIX' and sq_type == 'BID_ASK':
            continue

        if contract.secType == "STK" or contract.secType == "IND":
            sym = contract.symbol.replace(" ", "")
        else:
            sym = contract.localSymbol.replace(" ", "")

        fn = olc.DATA_DIR + olu.getYear(sDate) + "/" + olu.getMonth(sDate) + "/" + olu.getDay(sDate) + "/sq-" + sq_type + "-" + sym + ".csv"
        if os.path.exists(fn):
            df = pd.read_csv(fn, index_col=None)
            if df.shape[0] > 300:
                print("...skipping.  file exists. ", fn)
                continue
        ib = getIB()
        bars = ib.reqHistoricalData(contract, endDateTime=sDate + " 16:00:00",
                                    durationStr='8 D', barSizeSetting='1 min',
                                    whatToShow=sq_type, useRTH=True)
        if len(bars) > 0:
            df = util.df(bars)
            df['symbol'] = contract.symbol
            df['localSymbol'] = contract.localSymbol
            df['conId'] = contract.conId
            # get unique dates in df

            dates = df['date'][::].astype(str).str.slice(stop=10).unique()
            # for each date, filter rows & save
            for date_ in dates:
                fn2 = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(date_) + "/sq-" + sq_type + "-" + sym + ".csv"
                Path(fn2).parent.mkdir(parents=True, exist_ok=True)
                df_ = df.loc[df['date'][::].astype(str).str.slice(stop=10) == date_]
                df_.to_csv(fn2, index=False)
        else:
            df = pd.DataFrame()
            break
    return df
