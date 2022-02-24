""" This example sends a simple workflow request to the ARAX API.
"""

# Import minimal requirements
import requests
import json
import re
import argparse
import os
import sys

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code','ARAX','ARAXQuery']))
from ARAX_query import ARAXQuery

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--local", action='store_true')
arguments = parser.parse_args()

def _do_arax_query(query: dict):
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, response.envelope.message]

# Set the base URL for the ARAX reasonaer TRAPI 1.1 base
endpoint_url = 'https://arax.ncats.io/beta/api/arax/v1.2'

# Get an existing message to work on
# One of our own results
#response_content = requests.get(endpoint_url + '/response/35965', headers={'accept': 'application/json'})
# Try a BTE result from a recent standup
#response_content = requests.get(endpoint_url + '/response/843990fb-4cd0-46c0-95cb-644990b226e5', headers={'accept': 'application/json'})
# Try reranking a Chris example
# clinical DCP
# results: https://arax.ncats.io/beta/?r=36704
# rerank_endpoint_url = 'https://raw.githubusercontent.com/TranslatorSRI/RankingComparison/main/inputs/clinical_DCP/result.json'
# genes_genetically_associated_to_asthma
# Results: https://arax.ncats.io/beta/?r=36703
# rerank_endpoint_url = 'https://raw.githubusercontent.com/TranslatorSRI/RankingComparison/main/inputs/genes_genetically_associated_to_asthma/result.json'
# treats_hyperlipidemia
# Results: https://arax.ncats.io/beta/?r=36702
# rerank_endpoint_url = 'https://raw.githubusercontent.com/TranslatorSRI/RankingComparison/main/inputs/treats_hyperlipidemia/result.json'
# two_hop_acromegaly
# Results: https://arax.ncats.io/beta/?r=36742
rerank_endpoint_url = 'https://raw.githubusercontent.com/TranslatorSRI/RankingComparison/main/inputs/two_hop_acromegaly/result.json'
# two_hop_hypothyroidism (not up yet)
# Results: 
# rerank_endpoint_url = ''
response_content = requests.get(rerank_endpoint_url, headers={'accept': 'application/json'})
# Error test
# response_content = requests.get(endpoint_url + '/response/99adc6b5-0803-4c52-972e-fe587744a7aa', headers={'accept': 'application/json'})

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
        if score is None:
            score = str(score)
        else:
            score = '{:6.3f}'.format(score)
        result['score'] = None
    else:
        score = '???'
    essence = '?'
    if 'essence' in result:
        essence = result['essence']
    print("  -" + score + f"\t{essence}")

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
        "id": "score"
        },
  ]
 }

if arguments.local:
    [response_dict, message_dict] = _do_arax_query(request)
    message_dict = message_dict.to_dict()
    response_dict = {"message":message_dict}
else:
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


if not arguments.local:
    # These URLs provide direct access to resulting data and GUI
    print(f"Data: {response_dict['id']}")
    if response_dict['id'] is not None:
        match = re.search(r'(\d+)$', response_dict['id'])
        if match:
            print(f"GUI: https://arax.ncats.io/beta/?r={match.group(1)}")
