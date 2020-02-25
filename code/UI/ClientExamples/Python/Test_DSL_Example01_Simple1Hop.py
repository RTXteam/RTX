""" This example sends a simple query to the RTX API.
"""

# Import minimal requirements
import requests
import json

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.rtx.ai/devED/api/rtx/v1/query'

# Create a dict of the request, specifying the list of DSL commands
request = { "previous_message_processing_plan": { "processing_actions": [
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, is_set=True, id=n01)",
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

# Open a new browser tab and point it to the UI with the message number found here
print(response_dict['id'])
# https://arax.rtx.ai/devED/?m=nnn

