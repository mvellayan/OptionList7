import datetime
from os.path import exists
from pathlib import Path

import numpy as np
import pandas as pd
import common.ol_const as olc
import common.ol_pd as olpd
import common.ol_ib as oli
import common.ol_util as olu


def project_join(date_, stock):

    if type(date_) in [int]:
        date_ = str(round(date_))
    print(olu.tn() + "processing:", date_)

    if stock.secType == "STK" or stock.secType == "IND":
        sym = stock.symbol.replace(" ", "")
    else:
        sym = stock.localSymbol.replace(" ", "")

    #
    # load VIX
    dirSp = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(
        date_) + "/sq-TRADES-VIX.csv"
    if not exists(dirSp): return

    dfVIX = olpd.load_data(dirSp)
    dfVIX.drop_duplicates(subset=['date'], keep='first', inplace=True)

    #
    # load TRADES
    dirSp = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(date_) + "/sq-TRADES" + "-*.csv"
    dfTrades = olpd.load_data(dirSp)
    dfTrades.drop_duplicates(subset=['date', 'conId'], keep='first', inplace=True)

    #
    # load BID_ASK
    dirSp = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(date_) + "/sq-BID_ASK" + "-*.csv"
    dfBA = olpd.load_data(dirSp)
    dfBA.drop_duplicates(subset=['date', 'conId'], keep='first', inplace=True)

    #
    # Process TRADES
    dfTrades['average'] = dfTrades['average'].round(decimals=3)
    # need this column to compute average of averages
    dfTrades = dfTrades[['date', 'symbol', 'localSymbol', 'conId', 'low', 'average', 'high',  'volume', 'barCount']]

    # dfTrades['symbol'] = dfTrades.apply(lambda x: x.symbol if x.localSymbol == np.nan else x.localSymbol, axis=1)
    # dfTrades['symbol'] = dfTrades.apply(lambda x: findSymbol(x))
    # dfTrades.drop(columns=['localSymbol'])
    dfTrades.rename(columns={'low': 'trade_low', 'average': 'trade_average', 'high': 'trade_high',
                             'volume': 'trade_volume', 'barCount': 'trade_barCount', }, inplace=True)

    #
    # Process BID_ASK
    dfBA.drop(columns=['average', 'volume', 'barCount'], inplace=True)
    dfBA = dfBA[['date', 'conId', 'low', 'open', 'close', 'high']]
    dfBA.rename(columns={'low': 'bid_min', 'open': 'bid_avg', 'close': 'ask_avg', 'high': 'ask_max', }, inplace=True)

    #
    # Process VIX
    dfVIX = dfVIX[['date', 'open']].copy()
    dfVIX.rename(columns={'open': 'vix'}, inplace=True)

    #
    # merge vix with bid_ask
    dfBA = pd.merge(left=dfBA, right=dfVIX, how="left", on=["date"], validate="many_to_one")

    #
    # Merge bid_ask with TRADES
    dfTrades = pd.merge(left=dfTrades, right=dfBA, how="left", on=["date", 'conId'], validate="one_to_one")

    #
    # write projected data w/o normalization
    print(olu.tn() + " Writing projected file to csv")
    fn = olc.PROJECTION_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(
        date_) + "/" + sym + ".csv"
    Path(fn).parent.mkdir(parents=True, exist_ok=True)
    dfTrades.to_csv(fn, index=False)
    print(olu.tn() + " Wrote projected file to csv", fn, dfTrades.shape)

# diff between last and first row.
def find_delta(rows):
    x = rows.iloc[-1] - rows.iloc[0]
    return x

if __name__ == "__main__":
    print(olu.tn() + "1p-projection Starting")

    #get dates
    todo_dates = pd.read_csv(olc.working_days, index_col=None)
    lp = todo_dates.loc[(todo_dates['working_date'] > olc.STOCK_PULL_START_DATE) & (todo_dates['working_date'] < olc.STOCK_PULL_END_DATE)]
    lp = lp.sort_values('working_date', ascending=False)

    #get stock
    configStocks = olu.getConfig(olc.config_json)
    stock = oli.getContract(configStocks.get("stocks")[0]['contract'])

    #loop for each date
    lp['working_date'].apply(project_join, stock=stock)
    # project_join("20221116", stock)
    print(olu.tn() + "1p-projection done!")
