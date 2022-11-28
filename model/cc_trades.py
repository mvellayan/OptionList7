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

#
# 		loops through each minute stock quote
# 			loops through each option quote
# 				add entries to cc_trades (model_no, open_stock_id, open_option_id)

if __name__ == "__main__":
    print(olu.tn() + "2p-load-to-mysql Starting")


    loadOptionList()
    loadProjectedQuotes()

    print(olu.tn() + "2p-load-to-mysql done!")
