""" This example sends a simple set of DSL commands to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/api/arax/v1.1/query'

# Create a dict of the request, specifying the list of DSL commands
request = {
    "message": {},
        "operations": { "actions": [
            "add_qnode(name=acetaminophen, key=n00)",
            "add_qnode(categories=biolink:Protein, key=n01)",
            "add_qedge(subject=n01, object=n00, key=e00)",
            "expand()",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n00, object_qnode_key=n01)",
            "resultify()",
            ] },
        "workflow": [
            { "id": "filter_results_top_n", "parameters": { "max_results": 17 } }
            ]
}

# Send the request to RTX and check the status
print(f"INFO: Sending ARAXi + workflow combo program to {endpoint_url}")
response_content = requests.post(endpoint_url, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    response_dict = response_content.json()
    print(json.dumps(response_dict, indent=2, sort_keys=True))
    exit()

# Unpack the response content into a dict
response_dict = response_content.json()
#print(json.dumps(response_dict, indent=2, sort_keys=True))

# Display the information log
for message in response_dict['logs']:
    if True or message['level'] != 'DEBUG':
        print(f"{message['timestamp']}: {message['level']}: {message['message']}")

# Display the results
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
        print(f"GUI: https://arax.ncats.io/NewFmt/?r={match.group(1)}")
