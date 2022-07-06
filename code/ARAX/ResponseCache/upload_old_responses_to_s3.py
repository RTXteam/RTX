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

    base_dir = '/mnt/data/orangeboard/Cache/responses_1_0'
    files = sorted(os.listdir(base_dir))
    #files = os.listdir(base_dir)

    test_mode = False
    counter = 0

    for file in files:

        with open(base_dir + '/' + file) as infile:

            content = ''
            for line in infile:
                content += line

            try:
                envelope = json.loads(content)
            except:
                print(f"ERROR: Unable to parse the JSON in {file}")
                continue

            response_filename = f"/responses/{file}"
            print(f"INFO: Writing {file} to bucket as {response_filename}")

            if not test_mode:
                s3.Object('arax-response-storage', response_filename).put(Body=content)

        counter += 1
        if counter > 999999:
            print("INFO: Ending early for testing")
            break


if __name__ == "__main__": main()
