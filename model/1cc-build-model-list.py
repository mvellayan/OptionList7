import os
import pandas as pd
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


# 	loads/replace model_name into mysql table
# 	reads ref-data and creates pouplates
# 		model-list.csv
# 		model_list mysql table

def build_model_list():
    arr = [2.50, 2.00, 1.50, 1.00, 0.75, 0.50, -0.50, -1.00, -1.5, -2.0]
    id = 1
    models = []
    for entry_tv in arr:
        for exit_tv in arr:
            if entry_tv > exit_tv:
                models.append({'id': id, 'open_tv': entry_tv, 'close_tv': exit_tv })
                models.append({'id': id, 'open_iv': entry_tv, 'close_iv': exit_tv})
                id += 1

    df = pd.json_normalize(data=models)
    return df

def load_model_names():
    model_name = olpd.load_data(olc.model_name_csv)
    model_name.to_sql(name="model_name", con=olsql.getEngine(), if_exists='replace', index=False)
    print(olu.tn() + "Inserted model_name Rows.")

def load_models(df):
    df.to_sql(name="model", con=olsql.getEngine(), if_exists='fail', index=False)
    print(olu.tn() + "Inserted model.model.")


if __name__ == "__main__":
    print('initial setup only.  Dont run this again.')
    1/0
    load_model_names()
    model = build_model_list()
    load_models(model)
    print(olu.tn() + "build-model-list-list done!")
