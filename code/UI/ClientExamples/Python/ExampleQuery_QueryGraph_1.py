""" This example sends a simple query to the ARAX API.

A one-line curl equivalent is:
curl -X POST "https://arax.ncats.io/api/arax/v1.1/query" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"bypass_cache\":false,\"enforce_edge_directionality\":false,\"log_level\":\"DEBUG\",\"max_results\":100,\"message\":{\"query_graph\":{\"edges\":{\"e00\":{\"object\":\"n01\",\"predicates\":[\"biolink:physically_interacts_with\"],\"subject\":\"n00\"}},\"nodes\":{\"n00\":{\"categories\":[\"biolink:ChemicalSubstance\"],\"ids\":[\"CHEMBL.COMPOUND:CHEMBL112\"]},\"n01\":{\"categories\":[\"biolink:Protein\"]}}}},\"operations\":null,\"page_number\":1,\"page_size\":100,\"return_minimal_metadata\":false,\"stream_progress\":false,\"workflow\":null}"

To trigger a streaming response of progress, try this:
curl -X POST "https://arax.ncats.io/api/arax/v1.1/query" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"bypass_cache\":false,\"enforce_edge_directionality\":false,\"log_level\":\"DEBUG\",\"max_results\":100,\"message\":{\"query_graph\":{\"edges\":{\"e00\":{\"object\":\"n01\",\"predicates\":[\"biolink:physically_interacts_with\"],\"subject\":\"n00\"}},\"nodes\":{\"n00\":{\"categories\":[\"biolink:ChemicalSubstance\"],\"ids\":[\"CHEMBL.COMPOUND:CHEMBL112\"]},\"n01\":{\"categories\":[\"biolink:Protein\"]}}}},\"operations\":null,\"page_number\":1,\"page_size\":100,\"return_minimal_metadata\":false,\"stream_progress\":true,\"workflow\":null}"

"""

#### Import some needed modules
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/api/arax/v1.1/query'

#### Create a dict of the request, specifying the query type and its parameters
#### Note that predicates and categories must have the biolink: prefix to be valid
query = { "message": {
    "query_graph": {
        "edges": {
            "e00": {
                "subject": "n00",
                "object": "n01",
                "predicates": [ "biolink:physically_interacts_with" ]
            }
        },
        "nodes": {
            "n00": {
                "ids": [ "CHEMBL.COMPOUND:CHEMBL112" ],
                "categories": [ "biolink:ChemicalSubstance" ]
            },
            "n01": {
                "categories": [ "biolink:Protein" ]
            }
        }
    }
}}

# Send the request to RTX and check the status
response_content = requests.post(endpoint_url, json=query, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content.json())
    exit()

#### Unpack the response content into a dict
response_dict = response_content.json()

#print(json.dumps(response_dict, indent=4, sort_keys=True))

# Display the information log
for message in response_dict['logs']:
    if message['level'] != 'DEBUG':
        print(f"{message['timestamp']}: {message['level']}: {message['message']}")

# Display the results
print("Results:")
for result in response_dict['message']['results']:
    confidence = result['confidence']
    if confidence is None:
        confidence = 0.0
    print("  -" + '{:6.3f}'.format(confidence) + f"\t{result['essence']}")

# These URLs provide direct access to resulting data and GUI
print(f"Data: {response_dict['id']}")
if response_dict['id'] is not None:
    match = re.search(r'(\d+)$', response_dict['id'])
    if match:
        print(f"GUI: https://arax.ncats.io/?r={match.group(1)}")

# Also print the operations actions
print(f"Executed operations:")
if 'operations' in response_dict and response_dict['operations'] is not None:
    if 'actions' in response_dict['operations'] and response_dict['operations']['actions'] is not None:
        for action in response_dict['operations']['actions']:
            print(f"  - {action}")
