#!/usr/bin/python3
# Some example test code for the RTX feedback system

import os
import sys
import json
import ast

from RTXFeedback import RTXFeedback
import requests
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server")
from swagger_server.models.response import Response

url = "http://arax.ncats.io/api/rtx/v1/query"

query = {
  "known_query_type_id": "Q3",
  "original_question": "what proteins does acetaminophen target",
  "restated_question": "Which proteins are the target of acetaminophen?",
  "terms": {
    "chemical_substance": "CHEMBL112",
    "rel_type": "directly_interacts_with",
    "target_label": "protein"
    }
  }

query = {
  "known_query_type_id": "Q0",
  "original_question": "what is malaria",
  "restated_question": "What is malaria",
  "terms": {
    "term": "malaria"
  }
}


#### Create an RTX Feedback management object
rtxFeedback = RTXFeedback()

#### Purge and re-create the database if desired
#rtxFeedback.createDatabase()
#rtxFeedback.prepopulateDatabase()

#### Connect to the database
rtxFeedback.connect()

#### Fetch a cached response based on this query if there is one
cachedResponse = rtxFeedback.getCachedResponse(query)
#cachedResponse = None

#### If there was one, then return it
if ( cachedResponse is not None ):
  apiResponse = Response().from_dict(cachedResponse)

#### Otherwise, send the query to the web service (which creates an entry in the cache)  
else:
  httpResponse = requests.post(url,json=query)
  assert(httpResponse.status_code == 200)
  apiResponse = Response.from_dict(httpResponse.json())
  rtxFeedback.addNewResponse(apiResponse,query)

#### Print out the result as JSON
dumpString = json.dumps(ast.literal_eval(repr(apiResponse)),sort_keys=True,indent=2)
print(dumpString[0:1000]+"\n...")
