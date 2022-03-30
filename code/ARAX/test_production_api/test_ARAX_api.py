#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

import requests

arax_url = "https://arax.ncats.io/api/arax/v1.2/query"

def test_api_status():
    query = {
      "submitter": 'ARAX_test',
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
              "categories": ["biolink:ChemicalEntity"],
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


@pytest.mark.slow
def test_kitchen_sink_api():
    query = {
  "submitter": 'ARAX_test',
  "bypass_cache": False,
  "enforce_edge_directionality": False,
  "max_results": 100,
  "message": {},
    "operations": {"actions": [
            "add_qnode(name=arthritis, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
            "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=probably_treats, direction=below, threshold=.8, remove_connected_nodes=t, qnode_keys=[n02])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=15)",
            "return(message=true, store=false)"
        ]},
  "page_number": 1,
  "page_size": 100,
  "return_minimal_metadata": False,
  "stream_progress": False
}
    response_content = requests.post(arax_url, json=query, headers={'accept': 'application/json'})
    status_code = response_content.status_code
    assert status_code == 200
    results_json = response_content.json()
    message = results_json['message']
    assert results_json['status'] == 'OK'
    assert len(message['results']) > 0
    assert message['results'][0]['essence'] is not None
    return results_json


if __name__ == "__main__": pytest.main(['-v'])
