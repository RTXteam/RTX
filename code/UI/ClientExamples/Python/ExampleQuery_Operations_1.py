""" This example sends a simple set of DSL commands to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/api/arax/v1.1/query'

# Create a dict of the request, specifying the list of DSL commands
request = { "message": {}, "operations": { 
          "message_uris": [ "https://arax.ncats.io/api/arax/v1.1/response/9852" ],
          "actions": [
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
            "resultify()",
            ] } }

# Send the request to RTX and check the status
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
