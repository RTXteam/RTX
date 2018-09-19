#### Import some needed modules
import requests
import json
import sys

#### Workflow 1

################################################################
# X-ray module 1: given a disease, find genetic conditions that share "representative phenotypes" in common

#### Set the input disease
input_disease = "DOID:9352"

#### Set the base URL for the reasoner and its endpoint
API_BASE_URL = 'https://rtx.ncats.io/api/rtx/v1'
url_str = API_BASE_URL + "/query"

#### Create a dict of the request, specifying the query type and its parameters
request = {"query_type_id": "Q10001", "terms": {"disease": input_disease}}

#### Send the request to RTX and check the status
response_content = requests.post(url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module1_results_json = response_content.json()

################################################################
# X-ray module 2: gene-centric approach
request = {"query_type_id": "Q55", "terms": {"disease": input_disease}}

#### Send the request to RTX and check the status
response_content = requests.post(url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module2_results_json = response_content.json()

################################################################
# Orange team module 3: agent-centric


################################################################
# Gamma team module 3: agent-centric


################################################################
# Orange team module 4+5: annotation and scoring



