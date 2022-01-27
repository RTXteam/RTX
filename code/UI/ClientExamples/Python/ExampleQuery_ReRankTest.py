""" This example sends a simple workflow request to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re

# Set the base URL for the ARAX reasonaer TRAPI 1.1 base
endpoint_url = 'https://arax.ncats.io/beta/api/arax/v1.2'

# Get an existing message to work on
response_content = requests.get(endpoint_url + '/response/35965', headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content)
    exit()

# Unpack the response content into a dict
response_dict = response_content.json()
print(f"Retrieved a message with {len(response_dict['message']['results'])} results:")

# Summarize the results
for result in response_dict['message']['results']:
    if 'score' in result:
        score = result['score']
        result['score'] = None
    else:
        score = '???'
    essence = '?'
    if 'essence' in result:
        essence = result['essence']
    print("  -" + '{:6.3f}'.format(score) + f"\t{essence}")

print(f"\nAfter score removal:")
for result in response_dict['message']['results']:
    if 'score' in result:
        score = result['score']
    else:
        score = '???'
    essence = '?'
    if 'essence' in result:
        essence = result['essence']
    print("  -" + str(score) + f"\t{essence}")


# Create a new request, including previous response message and a simple filter_results_top_n action
print("\nCreate a new request with the previous message and a workflow to rerank (overlay_connect_knodes,complete_results,score)")
request = {
    "message": response_dict['message'],
    "workflow": [
        {
        "id": "overlay_connect_knodes"
        },
        {
        "id": "complete_results"
        },
        {
        "id": "score"
        },
  ]
 }

# Send the request to ARAX and check the status
response_content = requests.post(endpoint_url + '/query', json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
if status_code != 200:
    print("ERROR returned with status "+str(status_code))
    print(response_content)
    exit()

# Unpack the JSON response content into a dict
response_dict = response_content.json()

# Display a summary of the results
print(f"Results ({len(response_dict['message']['results'])}):")
for result in response_dict['message']['results']:
    if 'score' in result:
        score = result['score']
    else:
        score = '???'
    essence = '?'
    if 'essence' in result:
        essence = result['essence']
    print("  -" + '{:6.3f}'.format(score) + f"\t{essence}")

# These URLs provide direct access to resulting data and GUI
print(f"Data: {response_dict['id']}")
if response_dict['id'] is not None:
    match = re.search(r'(\d+)$', response_dict['id'])
    if match:
        print(f"GUI: https://arax.ncats.io/beta/?r={match.group(1)}")
