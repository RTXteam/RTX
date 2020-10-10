#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server")
from RTXQuery import RTXQuery


def main():

    #### Create an RTXQuery object
    rtxq = RTXQuery()
 
    #### Fill out a simple what is query
    query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" } }
    #query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" }, "bypass_cache": "true" }  # Use bypass_cache if the cache if bad for this question

    #### Run the query and print the result
    message = rtxq.query(query)
    print(json.dumps(message.to_dict(),sort_keys=True,indent=2))


if __name__ == "__main__": main()
