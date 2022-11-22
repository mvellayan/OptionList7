import datetime
import glob
import sqlalchemy
import pymysql
from sqlalchemy.sql import text as text
import pandas as pd
from ib_insync import *
import common.ol_const as olc

# https://towardsdatascience.com/work-with-sql-in-python-using-sqlalchemy-and-pandas-cd7693def708
connect_string = "mysql+pymysql://" + olc.database_user + ":" + olc.database_password \
                 + "@" + olc.database_host + "/" + olc.database_schema + "?charset=utf8mb4"

engine = ""
def getEngine():
    global engine
    if engine == "":
        engine = sqlalchemy.create_engine(connect_string, echo=False)
    return engine


