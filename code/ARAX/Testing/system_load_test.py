#!/usr/bin/env python3

# script for testing the concurrent load that ARAX can handle
# set N to be the number of queries that will be posted to ARAX,
# with a 10 second interval between each query posting

# Stephen Ramsey, Oregon State University

import pprint
import requests
import asyncio
import time

url = "https://arax.ncats.io/test/api/arax/v1.4/query",
# url = "https://arax.ncats.io/kg2/api/rtxkg2/v1.4/query"

N = 10

trapi = {"message":
         {"query_graph":
          {"nodes":
           {"n1":
            {"categories": ["biolink:ChemicalEntity"]},
            "n2":
            {"ids": ["MONDO:0005148"]}},
           "edges":
           {"e1":
            {"subject": "n1",
             "object": "n2",
             "predicates": ["biolink:treats"]}}}}}


def fetch():
    return requests.post(url,
                         json=trapi)

async def main():
    loop = asyncio.get_event_loop()
    res = [None]*N
    for i in range(N):
        res[i] = loop.run_in_executor(None, fetch)
        time.sleep(10)
    for i in range(N):
        with open(f"output{i}.json", "w") as fo:
            pprint.pprint((await res[i]).json(), fo)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    


         
