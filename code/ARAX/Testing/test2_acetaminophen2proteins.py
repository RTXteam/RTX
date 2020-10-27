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
        "message": {
            "query_graph": {
                "edges": [
                    {
                    "id": "qg2",
                    "source_id": "qg1",
                    "target_id": "qg0",
                    "type": "physically_interacts_with"
                    }
                ],
                "nodes": [
                    {
                    "id": "qg0",
                    "name": "acetaminophen",
                    "desc": "A member of the class of phenols that is 4-aminophenol in which one of the hydrogens attached to the amino group has been replaced by an acetyl group.",
                    "curie": "CHEMBL.COMPOUND:CHEMBL112",
                    "type": "chemical_substance"
                    },
                    {
                    "id": "qg1",
                    "name": None,
                    "desc": "Generic protein",
                    "curie": None,
                    "type": "protein"
                    }
                ]
            }
        }
    }

    #### Run the query and print the result
    message = rtxq.query(query)
    print(json.dumps(message.to_dict(),sort_keys=True,indent=2))


if __name__ == "__main__": main()
