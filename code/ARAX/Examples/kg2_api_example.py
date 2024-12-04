#!/usr/bin/env python3

import json
import pprint
import requests

with open("kg2_api_example.json", "r") as input_file:
    trapi_message = json.load(input_file)
    result = requests.post("https://kg2cploverdb.transltr.io/query",
                           json=trapi_message,
                           headers={"Content-Type": "application/json"})
    pprint.pprint(result.json())
