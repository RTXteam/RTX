#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast

import boto3
import timeit

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration


def main():

    rtx_config = RTXConfiguration()
    KEY_ID = rtx_config.config["Global"]['s3']['access']
    ACCESS_KEY = rtx_config.config["Global"]['s3']['secret']

    query_graph = {
        "edges": {
            "e01": {
            "constraints": [],
            "object": "n1",
            "predicates": [
                "biolink:expression_decreased_by",
                "biolink:activity_decreased_by"
            ],
            "subject": "n0"
            }
        }
    }

    s3 = boto3.resource(
        's3',
        region_name='us-west-2',
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=ACCESS_KEY
    )
    serialized_query_graph = json.dumps(query_graph,sort_keys=True,indent=2)
    print("INFO: Writing to bucket")
    t0 = timeit.default_timer()
    s3.Object('arax-response-storage', 'test1.txt').put(Body=serialized_query_graph)
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))

    print("INFO: Reading from bucket")
    t0 = timeit.default_timer()
    
    content = s3.Object('arax-response-storage', 'test1.txt').get()["Body"].read()
    read_query_graph = json.loads(content)
    print(json.dumps(read_query_graph,sort_keys=True,indent=2))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))




if __name__ == "__main__": main()
