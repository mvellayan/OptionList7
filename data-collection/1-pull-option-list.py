import datetime
import os
import time
from pprint import pprint
from ib_insync import *
import common.data_prep_common as dc
import pandas as pd

REFERENCE_DIR = "../data/reference/"
config_json = REFERENCE_DIR + "stock-list.json"

'''
        1. for a list of stocks in the stock-list.json
        2. pull current list of options
        3. loads data/reference/option-list-AAPL.csv
        4. add new options 
        5. dedups based on conid
        6. saves back to data/reference/option-list-AAPL.csv
'''

def pull_option_list():
    ib = dc.getIB()
    configStocks = dc.getConfig(config_json)
    stocks = configStocks.get("stocks")
    # 1. for a list of stocks in the stock-list.json
    for stock in stocks:
        contract = dc.getContract(stock['contract'])
        symbol = contract.symbol.replace(" ", "")[0:4]
        option_list_file = REFERENCE_DIR + "option-list-"+symbol+".csv"
        if contract.secType == "STK":
            df = pd.DataFrame()

            # 3. loads data/reference/option-list-{symbol}.csv
            if os.path.exists(option_list_file):
                df = pd.read_csv(option_list_file, index_col=None)
                print(dc.tn() + f"OptionList file exists. {option_list_file}  Loaded shape:", df.shape)

            # 2. pull current list of options
            contract.secType = "OPT"
            contract.conId = 0
            res = ib.reqContractDetails(contract)

            # 4. add new options
            for row in res:
                new_df = pd.DataFrame([row.contract.__dict__ ])
                new_df.drop(['secType', 'primaryExchange', 'currency','tradingClass',
                             'includeExpired', 'secIdType', 'secId',
                             'comboLegsDescrip', 'comboLegs', 'deltaNeutralContract'], axis=1, inplace=True)
                df = pd.concat([df, new_df], axis=0, ignore_index=True)

            # 5. dedups based on conid
            print(dc.tn() + f"Superset shape:", df.shape)
            df.drop_duplicates(subset=['conId'], keep='first', inplace=True)

            #  6. saves back to data/reference/option-list-AAPL.csv
            df.to_csv(option_list_file, index=False)
            print(dc.tn() + f"No dup shape:", df.shape)

if __name__ == "__main__":
    pull_option_list()

os.system("say 1 pull option list done")
