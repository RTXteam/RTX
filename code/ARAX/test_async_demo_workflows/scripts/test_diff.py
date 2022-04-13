#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Based on the workflow runner by priyash


Read all the JSON files for all the workflows and submit them to two endpoints.
Save out the status codes, numbers of results, and time information

Currently only handles synchronous queries.

"""

from datetime import datetime
import json
import requests
import os
from collections import defaultdict
from os import path
import time


def collect_queries(workflows=['A','C','D','B']):
    '''
    Here the codes start calling the above functions and submits the queries to ARS

    The below code reads each JSON files from the Workflows A through D (subdirectories).
    The queries are submitted to ARAX and output is saved in a dictionary, where the key is the file name of
    the JSON to denote which query is being run and the values assigned to the key is the query id

    '''
    scriptpath = os.path.dirname(__file__)
    PATH = os.path.join(scriptpath,'../2021-12_demo')
    queries = []
    for workflow in workflows:
        dir = os.path.join(PATH,f'workflow{workflow}')
        files = os.listdir(dir)
        for name in files:
            if name.endswith((".json")):
                filename = path.join(dir, name)
                with open(filename,'r') as inf:
                    query = json.load(inf)
                    query['callback'] = "https://arax.ncats.io/devED/api/arax/v1.2/response"
                    query['submitter'] = f"test_{name.split("_")[0].replace(".json","")}"
                    queries.append( (name,query) )
    return queries

def run_query(sync_endpoint,query,qname):
    result = {}
    start = datetime.now()
    print(f'Submitting {qname} to {sync_endpoint}')
    response = requests.post(sync_endpoint,json=query)
    print('Response')
    result['endpoint'] = sync_endpoint
    result['query'] = qname
    result['status_code'] = response.status_code
    if response.status_code == 200:
        try:
            result['result_count'] = len(response.json()['message']['results'])
        except:
            result['result_count'] = 0
    else:
        result['result_count'] = 0
    end = datetime.now()
    result['timedelta'] = str(end-start)
    return result

def run_all(endpoints,workflows):
    queries = collect_queries(workflows)
    print(f'Collected {len(queries)} queries.')
    all_results = []
    for qname,q in queries:
        for endpoint in endpoints:
            result = run_query(endpoint,q,qname)
            all_results.append(result)
        time.sleep(60)
    with open('output_results.json','w') as outf:
        json.dump(all_results,outf,indent=4)

if __name__ == '__main__':
    run_all(['https://arax.ncats.io/api/arax/v1.2/asyncquery'],['D','A','C','B'])