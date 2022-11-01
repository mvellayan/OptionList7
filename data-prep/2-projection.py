import datetime
import numpy as np
import pandas as pd
import data_prep_common as dc

# Simple time now function
def tn():
    return datetime.datetime.now().strftime("%H:%M:%S") + ": "

# lambda functions
# return 1st value in series
def firstValue(rows):
    return rows.iloc[0]

# return last value in series
def lastValue(rows):
    return rows.iloc[-1]

# return arrow indicator for boxed in values;
#   -1 below lower bound
#    0 inside the box
#   +1 above the max value
def arrow(new_amt, old_amt, box):
    if old_amt == np.nan:
        return np.nan
    if new_amt == np.nan:
        return np.nan
    if (new_amt - old_amt) <= (box * -1):
        return '-1'
    if (new_amt - old_amt) >= box:
        return '1'
    else:
        return '0'

#  lambda function to adds up the last 5 values, excluding the very last value
def sum_last_5(rows):
    # print ("[" , rows[-6:-1], rows[-6:-1].sum(), "]")
    return rows[-6:-1].sum()

#  lambda function returns lowest of the last 5 values, excluding the very last value
def min_last_5(rows):
    return rows.iloc[-6:-1].min()

#  lambda function returns higest of  the last 5 values, excluding the very last value
def max_last_5(rows):
    return rows.iloc[-6:-1].max()


# Store/Save 1 second windows for h1, h2, h3, h4, h5
def one_second_window(df, prefix: str, window: int, quote_type: str):
    if quote_type == "TRADES":
        df[prefix + '_low'] = df['h0s_low'].rolling(window=window).agg({'minLast': firstValue})
        df[prefix + '_average'] = df['h0s_average'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_high'] = df['h0s_high'].rolling(window=window).agg({'maxLast': firstValue})
        df[prefix + '_volume'] = df['h0s_volume'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_barCount'] = df['h0s_barCount'].rolling(window=window).agg({'sumLast': firstValue})
    elif quote_type == "BID_ASK":
        df[prefix + '_bid_min'] = df['h0s_bid_min'].rolling(window=window).agg({'minLast': firstValue})
        df[prefix + '_bid_avg'] = df['h0s_bid_avg'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_ask_avg'] = df['h0s_ask_avg'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_ask_max'] = df['h0s_ask_max'].rolling(window=window).agg({'maxLast': firstValue})
    else:
        print(f"unexpected type {quote_type}")
        exit(1)

# Store/Save 5 second windows for h1, h2, h3, h4, h5
# def five_second_window(df, prefix: str, window: int):
#     df[prefix + '_high_max'] = df['high'].rolling(window=window).agg({'maxLast5': max_last_5})
#     df[prefix + '_low_min'] = df['low'].rolling(window=window).agg({'minLast5': min_last_5})
#
#     df[prefix + '_barCount_sum'] = df['barCount'].rolling(window=window).agg({'sumLast5': sum_last_5})
#     df[prefix + '_volume_sum'] = df['volume'].rolling(window=window).agg({'sumLast5': sum_last_5})
#     df[prefix + '_weighted_vol_avg_sum'] = df['_weighted_vol_avg'].rolling(window=6).agg({'SumLast5': sum_last_5})
#     df[prefix + '_average_avg'] = df[prefix + '_weighted_vol_avg_sum'] / df[prefix + '_volume_sum']
#     df[prefix + '_average_avg'] = df[prefix + '_average_avg'].round(decimals=3)
#     df.drop(columns=[prefix + '_weighted_vol_avg_sum'])


# Compute Future 5-second window summary
def future_avg(df, prefix: str, window: int):
    df.set_index('date')
    df = df.sort_index(ascending=False)
    df.reset_index()
    df[prefix + '_average'] = df['h0s_average'].rolling(window=window).agg({'firstValue': firstValue})
    df = df.sort_index(ascending=True)
    df.reset_index()
    return df


def future_arrow(df, prefix: str, field: str, window: float):
    df[prefix + "_arrow"] = df.apply(lambda x: arrow(x[field], x['h0s_average'], window), axis=1)
    return df


def rebase(low,
           c1, c2, c3, c4, c5, c6, c7, c8, c9, c10,
           c11, c12, c13, c14, c15, c16, c17, c18, c19, c20,
           c21, c22, c23, c24, c25, c26, c27, c28, c29, c30,
           c31, c32, c33, c34, c35):
   return pd.Series([
       c1 - low, c2 - low, c3 - low, c4 - low, c5 - low,
       c6 - low, c7 - low, c8 - low, c9 - low, c10 - low,
       c11 - low, c12 - low, c13 - low, c14 - low, c15 - low,
       c16 - low, c17 - low, c18 - low, c19 - low, c20 - low,
       c21 - low, c22 - low, c23 - low, c24 - low, c25 - low,
       c26 - low, c27 - low, c28 - low, c29 - low, c30 - low,
       c31 - low, c32 - low, c33 - low, c34 - low, c35 - low])

def main(param):

    #
    # load TRADES
    print(tn() + "Starting main()")
    dirSp = param.p_in_directory + param.p_symbol + "/" + param.p_symbol + "-" + "TRADES"
    dfTrades = dc.load_data(dirSp)
    dfTrades.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(tn() + "Loaded TRADES.", dfTrades.shape)


    #
    # load BID_ASK
    dirSp = param.p_in_directory + param.p_symbol + "/" + param.p_symbol + "-" + "BID_ASK"
    dfBA = dc.load_data(dirSp)
    dfBA.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(tn() + "Loaded BID_ASK", dfBA.shape)

    #
    # load VIX
    dirSp = param.p_in_directory + "VIX/VIX-TRADES"
    dfVIX = dc.load_data(dirSp)
    dfVIX.drop_duplicates(subset=['date'], keep='first', inplace=True)
    print(tn() + "Loaded VIX", dfVIX.shape)

    #
    # filter by month, if specified.
    if 1 <= param.p_month_no <= 12:
        dfTrades = dfTrades[pd.to_datetime(dfTrades['date']).dt.month == param.p_month_no]
        dfBA = dfBA[pd.to_datetime(dfBA['date']).dt.month == param.p_month_no]
        dfVIX = dfVIX[pd.to_datetime(dfVIX['date']).dt.month == param.p_month_no]
        print(tn() + " Filtered by month", dfTrades.shape, dfBA.shape, dfVIX.shape)

    #
    # Process TRADES
    dfTrades['average'] = dfTrades['average'].round(decimals=3)
    # need this column to compute average of averages
    dfTrades = dfTrades[['date', 'low', 'average', 'high',  'volume', 'barCount']]
    dfTrades.rename(columns={'low': 'h0s_low', 'average': 'h0s_average', 'high': 'h0s_high',
                             'volume': 'h0s_volume', 'barCount': 'h0s_barCount', }, inplace=True)
    dfTrades['_weighted_vol_avg'] = dfTrades['h0s_volume'] * dfTrades['h0s_average']

    print(tn() + " Processed TRADES data", dfTrades.shape)

    for ctr in range(1, 5):
        prefix = "h"+str(ctr)+"s"
        one_second_window(dfTrades, prefix, ctr+1, "TRADES")
        print(tn() + " .Completed 1 second TRADES for " + str(ctr), dfTrades.shape)

    #
    # Process BID_ASK
    dfBA.drop(columns=['average', 'volume', 'barCount'], inplace=True)
    dfBA = dfBA[['date', 'low', 'open', 'close', 'high']]
    dfBA.rename(columns={'low': 'h0s_bid_min', 'open': 'h0s_bid_avg', 'close': 'h0s_ask_avg', 'high': 'h0s_ask_max', }, inplace=True)
    print(tn() + " Processed BID_ASK data")
    for ctr in range(1, 5):
        prefix = "h"+str(ctr)+"s"
        one_second_window(dfBA, prefix, ctr+1, "BID_ASK")
        print(tn() + " .Completed 1 second BID_ASK for " + str(ctr), dfTrades.shape)

    #
    # Process VIX
    dfVIX = dfVIX[['date', 'open']].copy()
    dfVIX.rename(columns={'open': 'vix'}, inplace=True)
    print(tn() + " Processed VIX data")

    #
    # merge vix with bid_ask
    dfBA = pd.merge(left=dfBA, right=dfVIX, how="left", on="date", validate="one_to_one")
    print(tn() + " Merged VIX data with BID_ASK", dfBA.shape)

    # prefix = ["h5s", "h10s", "h15s", "h20s"]
    # window = [ 6, 11, 16, 21]
    # for pre, win in zip(prefix, window):
    #    call = 'five_second_window("' + pre + '",' + str(win) + ')'
    #    result = timeit.timeit(stmt=call, globals=globals(), number=1)
    #    print(f"Computed 5 second window for [{call}]: {result.__round__(2)} seconds.", df.shape)

    #
    # Merge bid_ask with TRADES
    dfTrades = pd.merge(left=dfTrades, right=dfBA, how="left", on="date", validate="one_to_one")
    print(tn() + " Merged all data", dfTrades.shape)

    #
    # compute future values
    #
    dfTrades = future_avg(dfTrades, "f5s", 6)
    print(tn() + " Computed f5 average")

    #
    # Compute future arrows
    prefix = ["f5s_10c", "f5s_15c", "f5s_20c", "f5s_25c"]
    window = [0.10, 0.15, 0.20, 0.25]
    for pre, win in zip(prefix, window):
        # future_arrow(pre, "f5s_average", window=win)
        dfTrades = future_arrow(dfTrades, pre, "f5s_average", win)
        print(tn() + " .Computed future arrow for ", pre, " New shape: ", dfTrades.shape)

    dfTrades = dfTrades.drop(columns=['_weighted_vol_avg'])
    print(tn(), f"  Dropped computed col", dfTrades.shape)

    #
    #
    #


    #
    # write projected data w/o normalization
    print(tn() + " Writing projected file to csv")
    fn = param.p_out_directory + param.p_symbol + "-" + str(param.p_month_no) + ".csv"
    dfTrades.to_csv(fn, index=False)
    print(tn() + " Wrote projected file to csv", fn, dfTrades.shape)

    dfTrades[['h0s_high', 'h0s_average',
        'h1s_high', 'h1s_low', 'h1s_average',
        'h2s_high', 'h2s_low', 'h2s_average',
        'h3s_high', 'h3s_low', 'h3s_average',
        'h4s_high', 'h4s_low', 'h4s_average',
        'f5s_average',
        'h0s_bid_avg', 'h0s_ask_max', 'h0s_bid_min', 'h0s_ask_avg',
        'h1s_ask_max', 'h1s_bid_min', 'h1s_bid_avg', 'h1s_ask_avg',
        'h2s_ask_max', 'h2s_bid_min', 'h2s_bid_avg', 'h2s_ask_avg',
        'h3s_ask_max', 'h3s_bid_min', 'h3s_bid_avg', 'h3s_ask_avg',
        'h4s_ask_max', 'h4s_bid_min', 'h4s_bid_avg', 'h4s_ask_avg']] = dfTrades.apply(lambda x:
            rebase(x['h0s_low'], x['h0s_high'],  x['h0s_average'],
            x['h1s_high'], x['h1s_low'], x['h1s_average'],
            x['h2s_high'], x['h2s_low'], x['h2s_average'],
            x['h3s_high'], x['h3s_low'], x['h3s_average'],
            x['h4s_high'], x['h4s_low'], x['h4s_average'],
        x['f5s_average'],
        x['h0s_bid_avg'], x['h0s_ask_max'], x['h0s_bid_min'], x['h0s_ask_avg'],
        x['h1s_ask_max'], x['h1s_bid_min'], x['h1s_bid_avg'], x['h1s_ask_avg'],
        x['h2s_ask_max'], x['h2s_bid_min'], x['h2s_bid_avg'], x['h2s_ask_avg'],
        x['h3s_ask_max'], x['h3s_bid_min'], x['h3s_bid_avg'], x['h3s_ask_avg'],
        x['h4s_ask_max'], x['h4s_bid_min'], x['h4s_bid_avg'], x['h4s_ask_avg']), axis=1)

    print(tn() + " Rescaled data.  Removed low value!")

    #
    # write Normalized data w/o normalization
    print(tn() + " Writing file normalized data to csv")
    fn = param.p_out_directory + param.p_symbol + "-" + str(param.p_month_no) + "-low.csv"
    dfTrades.to_csv(fn, index=False)
    print(tn() + " Wrote file normalized data to csv", fn, dfTrades.shape)


class Param:
    def __init__(self, p_in_directory, p_out_directory, p_symbol, p_month_no=0):
        self.p_in_directory = p_in_directory
        self.p_out_directory = p_out_directory
        self.p_symbol = p_symbol
        self.p_month_no = p_month_no

    def __str__(self):
        return "[" + self.p_in_directory + ", " + self.p_out_directory \
               + ", " + self.p_symbol + ", " + str(self.p_month_no) + "]"

params = [
    Param("../data/raw/", "../data/projected/", "TSLA", 3)
    , Param("../data/raw/", "../data/projected/", "TSLA", 4)
    , Param("../data/raw/", "../data/projected/", "TSLA", 5)
    , Param("../data/raw/", "../data/projected/", "TSLA", 6)
    , Param("../data/raw/", "../data/projected/", "TSLA", 7)
    , Param("../data/raw/", "../data/projected/", "TSLA", 8)
    , Param("../data/raw/", "../data/projected/", "TSLA", 9)
    # , Param("../data/raw/", "AAPL")
]


start_time = datetime.datetime.now()
for pm in params:
    print(tn() + " Starting Execution for ", pm)
    main(pm)
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())