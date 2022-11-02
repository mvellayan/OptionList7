import datetime
import json
from pprint import pprint
from common import data_prep_common as dc

d = datetime.datetime.now()
d2 = dc.getStrFromDate(d)
pprint(d2)
d3 = dc.getDateFromStr(d2)
pprint('x')
pprint (d3)
