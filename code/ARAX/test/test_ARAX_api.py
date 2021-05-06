#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

import requests

arax_url = "https://arax.ncats.io/api/arax/v1.1/query"

def test_api_status():
    query = {
      "bypass_cache": False,
      "enforce_edge_directionality": False,
      "max_results": 100,
      "message": {
        "query_graph": {
          "edges": {
            "e00": {
              "object": "n01",
              "predicates": ["biolink:physically_interacts_with"],
              "subject": "n00"
            }
          },
          "nodes": {
            "n00": {
              "categories": ["biolink:ChemicalSubstance"],
              "ids": ["CHEMBL.COMPOUND:CHEMBL112"]
            },
            "n01": {
              "categories": ["biolink:Protein"]
            }
          }
        }
      },
      "page_number": 1,
      "page_size": 100,
      "return_minimal_metadata": False,
      "stream_progress": False
    }
    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 200
    results_json = response_content.json()
    assert results_json['status'] == 'OK'
    assert len(results_json["message"]["results"]) > 0


if __name__ == "__main__": pytest.main(['-v'])
