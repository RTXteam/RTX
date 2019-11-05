""" This example sends a simple query to the RTX API.
"""

#### Import some needed modules
import requests
import json

#### Set the base URL for the reasoner and its endpoint
API_BASE_URL = 'https://rtx.ncats.io/devED/api/rtx/v1'
url_str = API_BASE_URL + "/query"

#### Create a dict of the request, specifying the query type and its parameters
request = { "query_message": {
  "query_graph": {
    "edges": [],
    "nodes": [
      {
        "curie": "CHEMBL.COMPOUND:CHEMBL503",
        "node_id": "n00"
      }
    ]
  }  }
}

#### Send the request to RTX and check the status
response_content = requests.post(url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code == 302:
  print(response_content)
elif status_code != 200:
  print("ERROR returned with status "+str(status_code))
  print(response_content.json())
  exit()

#### Unpack the response content into a dict
response_dict = response_content.json()

print(json.dumps(response_dict, indent=4, sort_keys=True))

