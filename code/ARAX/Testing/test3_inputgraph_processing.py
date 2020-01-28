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
 
    #### Fill out a one hop query acetaminophen to proteins
    query = {
        "previous_message_processing_plan": {
            "previous_message_uris": [ "https://rtx.ncats.io/api/rtx/v1/message/2" ],
            "processing_actions": [
                "filter(maximum_results=10)",
                "return(message=false,store=false)"
            ]
        }
    }

    #### Run the query and print the result
    message = rtxq.query(query)
    print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
