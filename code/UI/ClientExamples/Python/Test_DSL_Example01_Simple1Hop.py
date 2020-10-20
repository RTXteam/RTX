""" This example sends a simple set of DSL commands to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/devED/api/rtx/v1/query'

# Create a dict of the request, specifying the list of DSL commands
request = { "previous_message_processing_plan": { "processing_actions": [
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, id=n01)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "expand(edge_id=e00)",
            "filter(maximum_results=2)",
            ] } }

# Send the request to RTX and check the status
response_content = requests.post(endpoint_url, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content.json())

# Unpack the response content into a dict
response_dict = response_content.json()
print(json.dumps(response_dict, indent=2, sort_keys=True))

# Display the information log
for message in response_dict['log']:
    if message['level'] >= 20:
        print(message['prefix']+message['message'])


# These URLs provide direct access to resulting data and GUI
print(f"Data: {response_dict['id']}")
if response_dict['id'] is not None:
    match = re.search(r'(\d+)$', response_dict['id'])
    if match:
        print(f"GUI: https://arax.ncats.io/?m={match.group(1)}")

