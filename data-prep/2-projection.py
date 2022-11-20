import datetime
import numpy as np
import pandas as pd
import common.ol_const as olc
import common.ol_data as old
import common.ol_ib as oli
import common.ol_util as olu


def main(param):

    #
    # load TRADES
    print(dc.tn() + "Starting main()")
    dirSp = param.p_in_directory + param.p_symbol + "/" + param.p_symbol + "-" + "TRADES"
    dfTrades = dc.load_data(dirSp)
    dfTrades.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(dc.tn() + "Loaded TRADES.", dfTrades.shape)


    #
    # load BID_ASK
    dirSp = param.p_in_directory + param.p_symbol + "/" + param.p_symbol + "-" + "BID_ASK"
    dfBA = dc.load_data(dirSp)
    dfBA.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(dc.tn() + "Loaded BID_ASK", dfBA.shape)

    #
    # load VIX
    dirSp = param.p_in_directory + "VIX/VIX-TRADES"
    dfVIX = dc.load_data(dirSp)
    dfVIX.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(dc.tn() + "Loaded VIX", dfVIX.shape)

    #
    # filter by month, if specified.
    if 1 <= param.p_month_no <= 12:
        dfTrades = dfTrades[pd.to_datetime(dfTrades['date']).dt.month == param.p_month_no]
        dfBA = dfBA[pd.to_datetime(dfBA['date']).dt.month == param.p_month_no]
        dfVIX = dfVIX[pd.to_datetime(dfVIX['date']).dt.month == param.p_month_no]
        print(dc.tn() + " Filtered by month", dfTrades.shape, dfBA.shape, dfVIX.shape)

    #
    # Process TRADES
    dfTrades['average'] = dfTrades['average'].round(decimals=3)
    # need this column to compute average of averages
    dfTrades = dfTrades[['date', 'low', 'average', 'high',  'volume', 'barCount']]
    dfTrades.rename(columns={'low': 'trade_low', 'average': 'trade_average', 'high': 'trade_high',
                             'volume': 'trade_volume', 'barCount': 'trade_barCount', }, inplace=True)
    dfTrades['trade_weighted_vol_avg'] = dfTrades['trade_volume'] * dfTrades['trade_average']

    print(dc.tn() + " Processed TRADES data", dfTrades.shape)

    #
    # Process BID_ASK
    dfBA.drop(columns=['average', 'volume', 'barCount'], inplace=True)
    dfBA = dfBA[['date', 'low', 'open', 'close', 'high']]
    dfBA.rename(columns={'low': 'bid_min', 'open': 'bid_avg', 'close': 'ask_avg', 'high': 'ask_max', }, inplace=True)
    print(dc.tn() + " Processed BID_ASK data")

    #
    # Process VIX
    dfVIX = dfVIX[['date', 'open']].copy()
    dfVIX.rename(columns={'open': 'vix'}, inplace=True)
    print(dc.tn() + " Processed VIX data")

    #
    # merge vix with bid_ask
    dfBA = pd.merge(left=dfBA, right=dfVIX, how="left", on="date", validate="one_to_one")
    print(dc.tn() + " Merged VIX data with BID_ASK", dfBA.shape)

    #
    # Merge bid_ask with TRADES
    dfTrades = pd.merge(left=dfTrades, right=dfBA, how="left", on="date", validate="one_to_one")
    print(dc.tn() + " Merged all data", dfTrades.shape)

    #
    # write projected data w/o normalization
    print(dc.tn() + " Writing projected file to csv")
    fn = param.p_out_directory + param.p_symbol + "-" + str(param.p_month_no) + ".csv"
    dfTrades.to_csv(fn, index=False)
    print(dc.tn() + " Wrote projected file to csv", fn, dfTrades.shape)

if __name__ == "__main__":
    print(dc.tn() + " Starting 1-projection")
    main()
    print(dc.tn() + " Starting 1-projection")