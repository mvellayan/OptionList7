import sys
import os
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))
import pandas as pd

import common.ol_const as olc
import common.ol_ib as oli
import common.ol_util as olu

'''
        1. for a list of stocks in the stock-list.json
        2. pull current list of options
        3. loads data/reference/option-list-AAPL.csv
        4. add new options 
        5. dedups based on conid
        6. saves back to data/reference/option-list-AAPL.csv
'''


def pull_option_list():
    stocks = olu.getConfig(olc.stock_list_json).get("stocks")
    # 1. for a list of stocks in the stock-list.json
    for stock in stocks:
        contract = oli.getContract(stock['contract'])
        symbol = contract.symbol.replace(" ", "")[0:4]
        option_list_file = olc.REFERENCE_DIR + "option-list-" + symbol + ".csv"
        if os.path.exists(option_list_file):
            #get file creation date
            import time
            c_time = os.path.getctime(option_list_file)
            age = (time.time() - c_time) / (60 * 60 * 24)
            #check if file is older than 1 day
            if age > 1:
                # get julian date from ctime
                file_date = time.strftime("%Y%m%d%H%M%S", time.localtime(c_time))
                os.rename(option_list_file, option_list_file + "." + file_date)

        if contract.secType == "STK":
            df = pd.DataFrame()

            # 3. loads data/reference/option-list-{symbol}.csv
            if os.path.exists(option_list_file):
                df = pd.read_csv(option_list_file, index_col=None)
                print(olu.tn() + f"OptionList file exists. {option_list_file}  Loaded shape:", df.shape)

            # 2. pull current list of options
            contract.secType = "OPT"
            contract.conId = 0
            ib = oli.getIB()
            res = ib.reqContractDetails(contract)

            # 4. add new options
            for row in res:
                new_df = pd.DataFrame([row.contract.__dict__])
                new_df.drop(['secType', 'primaryExchange', 'currency', 'tradingClass',
                             'includeExpired', 'secIdType', 'secId',
                             'comboLegsDescrip', 'comboLegs', 'deltaNeutralContract'], axis=1, inplace=True)
                df = pd.concat([df, new_df], axis=0, ignore_index=True)

            # 5. dedups based on conid
            print(olu.tn() + f"Superset shape:", df.shape)
            df.drop_duplicates(subset=['conId'], keep='first', inplace=True)

            #  6. saves back to data/reference/option-list-AAPL.csv
            df.to_csv(option_list_file, index=False)
            print(olu.tn() + f"No dup shape:", df.shape)


if __name__ == "__main__":
    pull_option_list()
    print(olu.tn() + "1-pull-option-list done!")
