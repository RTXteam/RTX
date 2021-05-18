""" This example sends a simple workflow request to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasonaer TRAPI 1.1 base
endpoint_url = 'https://arax.ncats.io/api/arax/v1.1'


# Create a new request, with a query graph and workflow steps
request = {
  "message": {
    "query_graph": {
      "edges": {
        "e00": {
          "object": "n01",
          "predicates": [
            "biolink:physically_interacts_with"
          ],
          "subject": "n00"
        }
      },
      "nodes": {
        "n00": {
          "categories": [
            "biolink:ChemicalSubstance"
          ],
          "ids": [
            "CHEMBL.COMPOUND:CHEMBL112"
          ]
        },
        "n01": {
          "categories": [
            "biolink:Protein"
          ]
        }
      }
    }
  },
  "workflow": [
      { "id": "fill" },
      { "id": "bind" },
      { "id": "filter_results_top_n", "parameters": { "max_results": 15 } }
    ]
}

# Send the request to ARAX and check the status
print(f"INFO: Sending QueryGraph + workflow combo program to {endpoint_url}")
response_content = requests.post(endpoint_url + '/query', json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content)
    exit()

# Unpack the JSON response content into a dict
response_dict = response_content.json()

# Display the information log
for message in response_dict['logs']:
    if True or message['level'] != 'DEBUG':
        print(f"{message['timestamp']}: {message['level']}: {message['message']}")

# Display a summary of the results
print(f"Results ({len(response_dict['message']['results'])}):")
for result in response_dict['message']['results']:
    confidence = 0.0
    if 'confidence' in result:
        confidence = result['confidence']
    if confidence is None:
        confidence = 0.0
    essence = '?'
    if 'essence' in result:
        essence = result['essence']
    print("  -" + '{:6.3f}'.format(confidence) + f"\t{essence}")

# These URLs provide direct access to resulting data and GUI
print(f"Data: {response_dict['id']}")
if response_dict['id'] is not None:
    match = re.search(r'(\d+)$', response_dict['id'])
    if match:
        print(f"GUI: https://arax.ncats.io/?r={match.group(1)}")
