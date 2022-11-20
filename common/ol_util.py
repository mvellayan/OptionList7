import glob
import datetime

import pandas as pd
from pprint import pprint
import json
from os.path import exists
from ib_insync import *
from pathlib import Path
import os
import common.ol_const as olc
import common.ol_data as old
import common.ol_ib as oli

def tn():
    return datetime.datetime.now().strftime("%H:%M:%S") + ": "


def getConfig(config_json: str):
    l_config = readJsonDict(config_json, debugOutput=False)
    return l_config


def readJsonDict(fn: str, debugOutput=True):

    data = {}
    if not exists(fn):
        print(f"file {fn} does not exists")
        return data

    with open(fn) as f1:
        data = json.load(f1)

    if debugOutput:
        pprint(data)

    return data


def writeJsonDict(fn: str, data: dict, overwrite=False, debugOutput=True):

    if not overwrite and exists(fn):
        print(f"ERROR: file {fn} exists")
        return

    with open(fn, "w") as outfile:
        json.dump(data, outfile, indent=4)

    if debugOutput:
        pprint(data)

    return data


def writeArrToFile(barsList: [], fn: str, p_conId: int, p_symbol: str):
    if len(barsList) == 0:
        return
    # allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(barsList)
    df["symbol"] = p_symbol
    df["conId"] = p_conId

    Path(fn).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fn, index=False)
    print(f'   Written to file {fn}.  RowCount = {len(barsList)}')


def getDateObj(p1):
    if p1 == None:
        return datetime.datetime.now()
    elif isinstance(p1, datetime.datetime):
        return p1
    elif isinstance(p1, str):
        p1 = p1.replace(" ", "")
        if len(p1) == 0:
            return datetime.datetime.now()
        elif len(p1) == 8:
            return datetime.datetime(int(p1[0:4]), int(p1[4:6]), int(p1[6:8]))
        else:
            return datetime.datetime(int(p1[0:4]), int(p1[4:6]), int(p1[6:8]), int(p1[8:10]), int(p1[10:12]), int(p1[12:14]))
    else:
        print(f"unexpected object type {type(p1)}.  Cant convert to date object", p1)
        exit(1)


def getStrFromDate(p1: datetime.datetime):
    return p1.strftime("%Y%m%d %H%M%S")


def getYear(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[0:4]


def getMonth(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[4:6]


def getDay(p1):
    if type(p1) == datetime.datetime:
        p1 = p1.strftime("%Y%m%d")
    d = p1.replace(" ", "").replace("-", "")
    return d[6:8]
