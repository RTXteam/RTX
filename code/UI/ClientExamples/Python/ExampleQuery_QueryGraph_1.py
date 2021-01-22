""" This example sends a simple query to the ARAX API.

A one-line curl equivalent is:
curl -X POST "https://arax.ncats.io/devED/api/arax/v1.0/query?bypass_cache=false" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"asynchronous\":\"stream\",\"message\":{\"query_graph\":{\"edges\":{\"e00\":{\"subject\":\"n00\",\"object\":\"n01\",\"predicate\":\"biolink:physically_interacts_with\"}},\"nodes\":{\"n00\":{\"id\":\"CHEMBL.COMPOUND:CHEMBL112\",\"category\":\"biolink:ChemicalSubstance\"},\"n01\":{\"category\":\"biolink:Protein\"}}}}}"

To trigger a streaming response of progress, try this:
curl -X POST "https://arax.ncats.io/devED/api/arax/v1.0/query?bypass_cache=false" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"asynchronous\"\"stream\",\"message\":{\"query_graph\":{\"edges\":{\"e00\":{\"subject\":\"n00\",\"object\":\"n01\",\"predicate\":\"biolink:physically_interacts_with\"}},\"nodes\":{\"n00\":{\"id\":\"CHEMBL.COMPOUND:CHEMBL112\",\"category\":\"biolink:ChemicalSubstance\"},\"n01\":{\"category\":\"biolink:Protein\"}}}}}"

"""

#### Import some needed modules
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/devED/api/arax/v1.0/query'

#### Create a dict of the request, specifying the query type and its parameters
#### Note that predicates and categories must have the biolink: prefix to be valid
query = { "message": {
    "query_graph": {
        "edges": {
            "e00": {
                "subject": "n00",
                "object": "n01",
                "predicate": "biolink:physically_interacts_with"
            }
        },
        "nodes": {
            "n00": {
                "id": "CHEMBL.COMPOUND:CHEMBL112",
                "category": "biolink:ChemicalSubstance"
            },
            "n01": {
                "category": "biolink:Protein"
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
