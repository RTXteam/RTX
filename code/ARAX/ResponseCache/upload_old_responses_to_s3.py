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

    s3 = boto3.resource(
        's3',
        region_name='us-west-2',
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=ACCESS_KEY
    )

    files = os.listdir('/mnt/data/orangeboard/Cache/responses_1_0')

    test_mode = True

    for file in files:

        with open(file) as infile:

            serialized_query_graph = json.read(infile)

            response_filename = f"/responses/{file}"
            print(f"INFO: Writing {file} to bucket as {response_filename}")

            if not test_mode:
                s3.Object('arax-response-storage', response_filename).put(Body=serialized_query_graph)



if __name__ == "__main__": main()
