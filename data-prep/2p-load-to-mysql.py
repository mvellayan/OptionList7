import os
import sys

up_path = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(up_path(f, 2))

import common.ol_const as olc
import common.ol_pd as olpd
import common.ol_mysql as olsql
import common.ol_util as olu
from sqlalchemy.sql import text as text

def load_task():
    todo_csv = olpd.load_data(olc.todo_file)
    todo_csv[["conId", "pull_date"]] = todo_csv[["conId", "pull_date"]].fillna(0.0).astype(int)
    todo_csv.to_sql(name="task_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQL = """
        INSERT IGNORE INTO `ol7`.`task`(`con_id`, `symbol`, `expiry`, `strike`, `right`, 
        `multiplier`, `exchange`,`secType`, `status`, `pull_date`)
            SELECT `conId`, ifnull(`localSymbol`,`symbol`) symbol, `lastTradeDateOrContractMonth`, `strike`, `right`, 
            `multiplier`, `exchange`, `secType`, `status`, `pull_date` FROM `ol7`.`task_tmp`;
    """
    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(insertSQL))
        d = conn.execute(text("DROP TABLE `ol7`.`task_tmp`;"))

    print(olu.tn() + "Inserted TASK Rows =", r.rowcount)


def load_option_list():
    ol = olpd.load_data(olc.option_list_csv)
    ol.to_sql(name="option_list_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQL = """
        INSERT IGNORE INTO ol7.option_list(con_id, symbol, expiry, strike, option_type,
        multiplier, exchange,local_symbol)
            SELECT `conId`, `symbol`, `lastTradeDateOrContractMonth`, `strike`, `right`, 
            `multiplier`, `exchange`, `localSymbol` FROM `ol7`.`option_list_tmp`;
    """
    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(insertSQL))
        d = conn.execute(text("DROP TABLE `ol7`.`option_list_tmp`;"))

    print(olu.tn() + "Inserted OPTION_LIST Rows =", r.rowcount)


def load_projected_quotes():
    ol = olpd.load_data(olc.PROJECTION_DIR + "/**/*.csv",  recursive=True)
    ol.to_sql(name="option_quote_tmp", con=olsql.getEngine(), if_exists='replace', index=False)
    insertSQLOptions = """
    INSERT IGNORE INTO ol7.option_quote(quote_date, con_id, trade_low, trade_average, trade_high, trade_volume,
                     trade_barcount, bid_min, bid_avg, ask_avg, ask_max)
    SELECT date, `conId`, trade_low, trade_average, trade_high, trade_volume, 
                    `trade_barCount`, bid_min, bid_avg, ask_avg, ask_max
    FROM ol7.option_quote_tmp where `localSymbol` is not null;
    """

    insertSQLStocks = """
    INSERT IGNORE INTO ol7.stock_quote (quote_date, con_id, trade_low, trade_average, trade_average_delta_30, trade_average_delta_60, trade_high, trade_volume, 
                trade_barcount, bid_min, bid_avg, ask_avg, ask_max, vix)
    SELECT date, `conId`, trade_low, trade_average, trade_average_delta_30, trade_average_delta_60, trade_high, trade_volume, 
                `trade_barCount`, bid_min, bid_avg, ask_avg, ask_max, vix
    FROM ol7.option_quote_tmp  where symbol='AAPL'  and `localSymbol` is null;
    """

    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        s = conn.execute(text(insertSQLStocks))
        o = conn.execute(text(insertSQLOptions))
        d = conn.execute(text("DROP TABLE `ol7`.`option_quote_tmp`;"))

    print(olu.tn() + "Inserted STOCK_QUTOE Rows =", s.rowcount)
    print(olu.tn() + "Inserted OPTION_QUOTE Rows =", o.rowcount)


def cleanup():
    updateSQL = """
        update `ol7`.`option_quote` oq, `ol7`.`stock_quote` sq, `ol7`.`option_list` ol
         set oq.iv = get_iv(sq.trade_average, ol.strike, ol.option_type),
              oq.open_tv = get_tv(sq.trade_average, ol.strike, oq.bid_avg, oq.ask_avg, ol.option_type, 'OPEN'),
             oq.close_tv = get_tv(sq.trade_average, ol.strike, oq.bid_avg, oq.ask_avg, ol.option_type, 'CLOSE')
        where sq.quote_date = oq.quote_date
        and ol.con_id = oq.con_id;
    """
    with olsql.getEngine().connect().execution_options(autocommit=True) as conn:
        r = conn.execute(text(updateSQL))
        d = conn.execute(text("delete from `ol7`.`option_quote` where close_tv is null or open_tv is null;"))

    print(olu.tn() + "Inserted TASK Rows =", r.rowcount)



if __name__ == "__main__":
    print(olu.tn() + "2p-load-to-mysql Starting")

    load_task()
    load_option_list()
    load_projected_quotes()
    cleanup()

    print(olu.tn() + "2p-load-to-mysql done!")
