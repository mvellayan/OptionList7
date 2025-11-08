import sys
import os
import time
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))
import pandas as pd

import common.ol_const as olc
import common.ol_ib as oli
import common.ol_util as olu
from tqdm import tqdm

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

    # Columns to exclude from contract data
    EXCLUDE_COLUMNS = [
        'secType', 'primaryExchange', 'currency', 'tradingClass',
        'includeExpired', 'secIdType', 'secId',
        'comboLegsDescrip', 'comboLegs', 'deltaNeutralContract'
    ]

    # 1. for a list of stocks in the stock-list.json
    for stock in tqdm(stocks, desc="Stock"):
        try:
            contract = oli.getContract(stock['contract'])
            symbol = contract.symbol.replace(" ", "")[0:4]
            option_list_file = olc.REFERENCE_DIR + "option-list-" + symbol + ".csv"

            # Archive old file if it exists and is older than 1 day
            if os.path.exists(option_list_file):
                c_time = os.path.getctime(option_list_file)
                current_time = time.time()
                age = (current_time - c_time) / (60 * 60 * 24)

                if age > 1:
                    file_date = time.strftime("%Y%m%d%H%M%S", time.localtime(c_time))
                    os.rename(option_list_file, option_list_file + "." + file_date)

            if contract.secType != "STK":
                continue

            df = pd.DataFrame()
            existing_conids = set()

            # 3. loads data/reference/option-list-{symbol}.csv
            if os.path.exists(option_list_file):
                df = pd.read_csv(option_list_file, index_col=None)
                existing_conids = set(df['conId'].values)
                print(olu.tn() + f"OptionList file exists. {option_list_file}  Loaded shape:", df.shape)

            # 2. pull current list of options
            contract.secType = "OPT"
            contract.conId = 0
            ib = oli.getIB()
            res = ib.reqContractDetails(contract)

            # 4. add new options - collect all data first, then create DataFrame
            option_data = []
            for row in res:
                conid = row.contract.conId
                # Skip if already exists
                if conid in existing_conids:
                    continue

                contract_dict = row.contract.__dict__.copy()
                # Remove unwanted columns
                for key in EXCLUDE_COLUMNS:
                    contract_dict.pop(key, None)
                option_data.append(contract_dict)

            # Only concatenate if we have new data
            if option_data:
                new_df = pd.DataFrame(option_data)
                df = pd.concat([df, new_df], axis=0, ignore_index=True)
                print(olu.tn() + f"Added {len(option_data)} new options. Total shape:", df.shape)
            else:
                print(olu.tn() + f"No new options to add. Shape:", df.shape)

            #  6. saves back to data/reference/option-list-{symbol}.csv
            if option_data:  # Only save if we added new data
                df.to_csv(option_list_file, index=False)
                print(olu.tn() + f"Saved to {option_list_file}")

        except Exception as e:
            print(olu.tn() + f"Error processing {stock.get('contract', 'unknown')}: {str(e)}")
            continue


if __name__ == "__main__":
    pull_option_list()
    print(olu.tn() + "1-pull-option-list done!")
