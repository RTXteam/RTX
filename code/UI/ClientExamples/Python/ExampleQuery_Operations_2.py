""" This example sends a simple set of DSL commands to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasoner and its endpoint
endpoint_url = 'https://arax.ncats.io/api/arax/v1.1'

# Create a dict of the request, includes a reference to a previous response and a filter action
request = { "message": {}, "operations": { 
          "message_uris": [ f"https://arax.ncats.io/api/arax/v1.1/response/9857" ],
          "actions": [
            "filter_results(action=limit_number_of_results, max_results=7)",
            ] } }

# Send the request to RTX and check the status
response_content = requests.post(endpoint_url + '/query', json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content)
    exit()

# Unpack the response content into a dict
response_dict = response_content.json()

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
        print(f"GUI: https://arax.ncats.io/?r={match.group(1)}")
