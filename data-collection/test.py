import json
from pprint import pprint

dictionary = {
    "id": "04",
    "name": "sunil",
    "department": "HR"
}

with open("../config/sample.json", "w") as outfile:
    json.dump(dictionary, outfile)

# Opening JSON file
with open('../config/sample.json') as json_file:
    data = json.load(json_file)

pprint(data)