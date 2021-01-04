#!/usr/bin/python3
import sys

# This is basically just a query graph that I know will generate results that COHD can handle

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


import os
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server")
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
          "negated": None,
          "relation": None,
          "source_id": "qg1",
          "target_id": "qg0",
          "type": "has_phenotype"
        }
      ],
      "nodes": [
        {
          "id": "qg1",
          "is_set": None,
          "name": "Atherosclerosis",
          "desc": "None",
          "curie": "DOID:1936",
          "type": "disease"
        },
        {
          "id": "qg0",
          "is_set": None,
          "name": None,
          "desc": "Generic phenotypic_feature",
          "curie": None,
          "type": "phenotypic_feature"
        }
      ]
    }
  },
  "max_results": 100
}

    #### Run the query and print the result
    message = rtxq.query(query)
    print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))


if __name__ == "__main__": main()
