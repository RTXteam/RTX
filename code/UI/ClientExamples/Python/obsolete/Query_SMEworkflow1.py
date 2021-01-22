""" This example demonstrates fetching the results for SME Workflow #1 from RTX
using the Translator Reasoning Tool Standardized API.
"""

#### Import some needed modules
import requests
import json

#### Set the base URL for the reasoner and its endpoint
API_BASE_URL = 'https://rtx.ncats.io/api/rtx/v1'
url_str = API_BASE_URL + "/query"

#### Create a dict of the request, specifying the query type and its parameters
request = { "query_type_id": "Q55", "terms": { "disease": "DOID:9352" } }

#### Send the request to RTX and check the status
response_content = requests.post(url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
  print("ERROR returned with status "+str(status_code))
  exit()

#### Unpack the response content into a dict
response_dict = response_content.json()

#### Display the summary table of the results
if response_dict["table_column_names"]:
  print("\t".join(response_dict["table_column_names"]))
  for result in response_dict["result_list"]:
    print("\t".join(result["row_data"]))

#### Or dump the whole detailed JSON response_content data structure
print(json.dumps(response_dict, indent=4, sort_keys=True))

