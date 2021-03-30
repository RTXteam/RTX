#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery

#### For debugging purposes, you can send all messages as they are logged to STDERR
from response import Response
Response.output = 'STDERR'


def main():

    #### Create an RTXQuery object
    araxq = ARAXQuery()
 
    #### Fill out a one hop query acetaminophen to proteins
    query = {
        "previous_message_processing_plan": {
            "previous_message_uris": [ "https://arax.ncats.io/api/rtx/v1/message/2" ],
            "processing_actions": [
                "filter(maximum_results=10)",
                "return(message=false,store=false)"
            ]
        }
    }

    #### Run the query and print the result
    message = araxq.query_return_message(query)
    print(json.dumps(message.to_dict(),sort_keys=True,indent=2))


if __name__ == "__main__": main()
