#### Import some needed modules
import requests
import json
import sys

#### Workflow 1

#### Set the input disease
input_disease = "DOID:9352"
num_robocop_results = 10

#### Set the base URL for the reasoner and its endpoint
XRAY_API_BASE_URL = 'https://rtx.ncats.io/api/rtx/v1'
xray_url_str = XRAY_API_BASE_URL + "/query"

ROBOCOP_API_BASE_URL = 'http://robokop.renci.org/api/'
robocop_mod3_url_str = ROBOCOP_API_BASE_URL + "wf1mod3/%s/?max_results=%d" % (input_disease, num_robocop_results)
robocop_mod3a_url_str = ROBOCOP_API_BASE_URL + "wf1mod3a/%s/?max_results=%d" % (input_disease, num_robocop_results)


################################################################
# X-ray module 1: given a disease, find genetic conditions that share "representative phenotypes" in common

#### Create a dict of the request, specifying the query type and its parameters
request = {"query_type_id": "Q10001", "terms": {"disease": input_disease}}

#### Send the request to RTX and check the status
response_content = requests.post(xray_url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module1_xray_results_json = response_content.json()

################################################################
# X-ray module 2: gene-centric approach
request = {"query_type_id": "Q55", "terms": {"disease": input_disease}}

#### Send the request to RTX and check the status
response_content = requests.post(xray_url_str, json=request, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module2_xray_results_json = response_content.json()

################################################################
# Orange team module 3: agent-centric


################################################################
# Gamma team module 3: agent-centric
# Mod 3 un-lettered approach
response_content = requests.get(robocop_mod3_url_str, json={}, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module3_robocop_results_json = response_content.json()

# Mod3a approach
response_content = requests.get(robocop_mod3a_url_str, json={}, headers={'accept': 'application/json'})
status_code = response_content.status_code
assert status_code == 200
module3a_robocop_results_json = response_content.json()

################################################################
# Orange team module 4+5: annotation and scoring



