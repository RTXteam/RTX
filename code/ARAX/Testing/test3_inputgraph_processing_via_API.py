#!/usr/bin/python3
""" This example sends a simple request to the ARAX API.
"""

import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import requests
import json
import ast


def main():

    #### Set the base URL for the reasoner and its endpoint
    #API_BASE_URL = 'https://arax.ncats.io/devED/api/rtx/v1'
    API_BASE_URL = 'http://localhost:5001/devED/api/rtx/v1'
    url_str = API_BASE_URL + "/query"
 
    #### Create a simple query to send to ARAX via the API
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:731, id=n00, type=disease, is_set=false)",
        "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        'resultify(ignore_edge_direction=true)',
        "return(message=true, store=false)"]}}

    #### Send the request to ARAX and check the status
    response_content = requests.post(url_str, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    if status_code == 302:
        print(response_content)
    elif status_code != 200:
        print("ERROR returned with status "+str(status_code))
        print(response_content.json())
        exit()

    #### Unpack the response content into a dict and dump
    response_dict = response_content.json()
    print(json.dumps(response_dict, indent=2, sort_keys=True))


if __name__ == "__main__": main()




