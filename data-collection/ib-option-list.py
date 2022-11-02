import datetime
import os
import time
from pprint import pprint
from ib_insync import *
import common.data_prep_common as dc
import pandas as pd

def pull_and_save_data(ib, contract, endDateTime, durationStr: str,
                       barSizeSetting: str, whatToShow: str, outFileName: str):
    barsList = []
    bars = None
    print(dc.tn(), "      pull_and_save_data:", whatToShow, contract, durationStr, barSizeSetting, endDateTime)

    try:
        bars = ib.reqHistoricalData(contract, endDateTime=endDateTime, durationStr=durationStr,
                                barSizeSetting=barSizeSetting, whatToShow=whatToShow, useRTH=True, formatDate=1)
    except Exception as e:
        print(e)
        exit(1)

    if not bars:
        print(dc.tn(), "empty data returned for endDateTime", endDateTime)
        print(dc.tn(), "exiting.")
        return

    for x in bars:
        barsList.append(x)


    dc.writeArrToFile(barsList, outFileName)
    return endDateTime


def main():
    ib = IB()
    ib.connect('127.0.0.1', 7496, clientId=1)
    DATA_DIR = "../data/raw/"
    PARAM_DIR = "../config/"

    configFile = dc.getConfig(DATA_DIR, PARAM_DIR)
    configs = configFile.get("contracts")
    for contract_idx in range(len(configs)):
        pull_spec = configs[contract_idx]
        contract = dc.getContract(pull_spec['contract'])
        if contract.secType == "STK":
            pprint(contract)
            contract.secType = "OPT"
            contract.conId = 0
            res = ib.reqContractDetails(contract)
            df = pd.DataFrame()
            for row in res:
                new_df = pd.DataFrame([ row.contract.__dict__ ])
                df = pd.concat([df, new_df], axis=0, ignore_index=True)

            df.drop(['secType', 'multiplier','exchange','primaryExchange','currency',
                     'tradingClass', 'includeExpired', 'secIdType', 'secId',
                     'comboLegsDescrip', 'comboLegs', 'deltaNeutralContract'], axis=1, inplace=True)

            df.to_csv("test.csv", index=False)

            print("done.")

    pprint("Place holder. Done.")

if __name__ == "__main__":
    main()

os.system("say app done")
