import datetime
from os.path import exists
from pathlib import Path

import numpy as np
import pandas as pd
import common.ol_const as olc
import common.ol_pd as olpd
import common.ol_mysql as olsql
import common.ol_ib as oli
import common.ol_util as olu
import sqlalchemy
import pymysql
from sqlalchemy.sql import text as text

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
    dirSp = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(
        date_) + "/sq-TRADES" + "-*.csv"
    dfTrades = olpd.load_data(dirSp)
    dfTrades.drop_duplicates(subset=['date', 'conId'], keep='first', inplace=True)

    #
    # load BID_ASK
    dirSp = olc.DATA_DIR + olu.getYear(date_) + "/" + olu.getMonth(date_) + "/" + olu.getDay(
        date_) + "/sq-BID_ASK" + "-*.csv"
    dfBA = olpd.load_data(dirSp)
    dfBA.drop_duplicates(subset=['date', 'conId'], keep='first', inplace=True)

    #
    # Process TRADES
    dfTrades['average'] = dfTrades['average'].round(decimals=3)
    # need this column to compute average of averages
    dfTrades = dfTrades[['date', 'symbol', 'localSymbol', 'conId', 'low', 'average', 'high', 'volume', 'barCount']]

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




def loadToDo():
    todo_csv = olpd.load_data(olc.todo_file)
    todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
    todo_csv.to_sql(name="task_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQL = """
        INSERT IGNORE INTO `ol7`.`task`(`con_id`, `symbol`, `last_trade_date`, `strike`, `right`, 
        `multiplier`, `exchange`,`secType`, `status`, `pull_date`)
            SELECT `conId`, ifnull(`localSymbol`,`symbol`) symbol, `lastTradeDateOrContractMonth`, `strike`, `right`, 
            `multiplier`, `exchange`, `secType`, `status`, `pull_date` FROM `ol7`.`tasks_tmp`;
    """
    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(insertSQL))
        d = conn.execute(text("DROP TABLE `ol7`.`tasks_tmp`;"))

    print(olu.tn() + "Inserted TASK Rows =", r.rowcount)


def loadOptionList():
    ol = olpd.load_data(olc.option_list_csv)
    ol.to_sql(name="option_list_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQL = """
        INSERT IGNORE INTO `ol7`.`option_list` (`con_id`, `symbol`, `last_trade_date`, `strike`, `right`,
        `multiplier`, `exchange`,	`localSymbol`)
            SELECT `conId`, `symbol`, `lastTradeDateOrContractMonth`, `strike`, `right`, 
            `multiplier`, `exchange`, `localSymbol` FROM `ol7`.`option_list_tmp`;
    """
    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(insertSQL))
        d = conn.execute(text("DROP TABLE `ol7`.`option_list_tmp`;"))

    print(olu.tn() + "Inserted OPTION_LIST Rows =", r.rowcount)


def loadProjectedQuotes():
    ol = olpd.load_data(olc.PROJECTION_DIR + "/**/*.csv",  recursive=True)
    ol.to_sql(name="option_quote_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQLOptions = """
    INSERT IGNORE INTO ol7.option_quote(date, con_id, trade_low, trade_average, trade_average_delta_30, trade_high, trade_volume,
                     trade_barcount, barcount_sum_30, bid_min, bid_avg, ask_avg, ask_max)
    SELECT date, `conId`, trade_low, trade_average, trade_average_delta_30, trade_high, trade_volume, 
                    `trade_barCount`, `barCount_sum_30`, bid_min, bid_avg, ask_avg, ask_max
    FROM ol7.option_quote_tmp where `localSymbol` is not null;
    """

    insertSQLStocks = """
    INSERT IGNORE INTO ol7.stock_quote (date, con_id, trade_low, trade_average, trade_average_delta_30, trade_high, trade_volume, 
                trade_barcount,barcount_sum_30, bid_min, bid_avg, ask_avg, ask_max)
    SELECT date, `conId`, trade_low, trade_average, trade_average_delta_30, trade_high, trade_volume, 
                `trade_barCount`, `barCount_sum_30`, bid_min, bid_avg, ask_avg, ask_max 
    FROM ol7.option_quote_tmp  where symbol='AAPL'  and `localSymbol` is null;
    """

    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(insertSQLOptions))
        r = conn.execute(text(insertSQLStocks))
        d = conn.execute(text("DROP TABLE `ol7`.`option_quote_tmp`;"))

    # print(olu.tn() + "Inserted OPTION_LIST Rows =", r.rowcount)



if __name__ == "__main__":
    print(olu.tn() + "2p-load-to-mysql Starting")

    #loadToDo()
    #loadOptionList()
    loadProjectedQuotes()

    print(olu.tn() + "2p-load-to-mysql done!")
