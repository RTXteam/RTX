#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

import requests

arax_url = "https://arax.ncats.io/api/arax/v1.2/query"


def test_non_json():
    content = '{'
    response_content = requests.post(arax_url, data=content, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 415
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'title' in response_json
    assert response_json['title'] == "Invalid Content-type (), expected JSON data"


def test_non_trapi():
    query = { "bananas": "giraffes"  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    #print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'detail' in response_json
    assert response_json['detail'] == "'message' is a required property"


def test_missing_message():
    query = {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"] }
       }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    #print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'detail' in response_json
    assert response_json['detail'] == "'message' is a required property"


def test_missing_nodes():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          }
      }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    #print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'detail' in response_json
    assert response_json['detail'] == "'nodes' is a required property - 'message.query_graph'"


def test_empty_nodes():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'QueryGraphZeroNodes'


def test_edge_invalid_subject():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n99", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"] }
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'QEdgeInvalidSubject'


def test_edge_invalid_object():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n99", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"] }
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'QEdgeInvalidObject'


def test_no_curie():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"] },
            "n01": { "categories": ["biolink:Protein"] }
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'QueryGraphNoIds'


def test_edge_extraneous_property():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"], "reversable": True }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"] }
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'UnknownQEdgeProperty'


def test_node_extraneous_property():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"], "set": True }             # Correct is "is_set" instead of "set"
    }  }  }  }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'UnknownQNodeProperty'


def test_workflow_bad_id():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"], "is_set": True }
      }  }  },
      "workflow": [
        { "id": "filter_results_top_N", "parameters": { "max_results": 10 } }   # should be top_n
        ]
    }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'detail' in response_json
    assert 'not valid' in response_json['detail']


def test_workflow_bad_parameter():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": ["biolink:physically_interacts_with"] }
          },
          "nodes": {
            "n00": { "categories": ["biolink:ChemicalSubstance"], "ids": ["CHEMBL.COMPOUND:CHEMBL112"] },
            "n01": { "categories": ["biolink:Protein"], "is_set": True }
      }  }  },
      "workflow": [
        { "id": "filter_results_top_n", "parameters": { "max_results": "banana" } }   # should be an integer
        ]
    }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 400
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'detail' in response_json
    assert 'not valid' in response_json['detail']


def test_workflow_no_message():
    query = {
      "message": { },
      "workflow": [
        { "id": "filter_results_top_n", "parameters": { "max_results": 10 } }
        ]
    }

    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 200
    response_json = response_content.json()
    print(json.dumps(response_json,sort_keys=True,indent=2))
    assert 'status' in response_json
    assert response_json['status'] == 'OK'


if __name__ == "__main__": pytest.main(['-v'])
