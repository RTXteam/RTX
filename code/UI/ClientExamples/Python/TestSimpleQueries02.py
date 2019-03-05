""" This example sends a simple query to the RTX API.
"""

#### Import some needed modules
import requests
import json

#### Set the base URL for the reasoner and its endpoint
API_BASE_URL = 'https://rtx.ncats.io/devED/api/rtx/v1'
url_str = API_BASE_URL + "/query"

#### Create a dict of the request, specifying the query type and its parameters
request = {
  "previous_message_processing_plan": {
    "previous_message_uris": [ "https://rtx.ncats.io/devED/api/rtx/v1/message/81" ],
    "options": { "AnnotateDrugs": 1, "Store": 1, "ReturnMessageId": 1 }
  }
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

#### If there is just a message_id in the response, display that
if "message_id" in response_dict:
  print("Returned message_id = %s" % response_dict["message_id"])

#### Or if there is a summary table of the results, display that
elif "table_column_namesxx" in response_dict:
  print("\t".join(response_dict["table_column_names"]))
  for result in response_dict["results"]:
    print("\t".join(result["row_data"]))

#### Or dump the whole detailed JSON response_content data structure
else:
  print(json.dumps(response_dict, indent=4, sort_keys=True))

