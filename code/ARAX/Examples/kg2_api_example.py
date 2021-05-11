#!/usr/bin/env python3

import json
import pprint
import requests

with open("kg2_api_example.json", "r") as input_file:
    trapi_message = json.load(input_file)
    result = requests.post("https://arax.ncats.io/api/rtxkg2/v1.0/query?bypass_cache=false",
                           json=trapi_message)
    pprint.pprint(result.json())
