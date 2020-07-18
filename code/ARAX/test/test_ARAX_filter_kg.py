#!/usr/bin/env python3

# Usage:
# run all: pytest -v test_ARAX_filter_kg.py
# run just certain tests: pytest -v test_ARAX_filter_kg.py -k test_default_std_dev

import sys
import os
import pytest
from collections import Counter
import copy
import json
import ast
from typing import List, Union
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from response import Response

PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.node_binding import NodeBinding
from swagger_server.models.edge_binding import EdgeBinding
from swagger_server.models.biolink_entity import BiolinkEntity
from swagger_server.models.result import Result
from swagger_server.models.message import Message


def _do_arax_query(query: dict) -> List[Union[Response, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, araxq.message]

def test_warning():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=asdfghjkl, direction=below, threshold=.2)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20

def test_default_std_dev():
    # query = {"previous_message_processing_plan": {"processing_actions": [
    #         "create_message",
    #         "add_qnode(curie=DOID:1588, id=n00)",
    #         "add_qnode(type=chemical_substance, is_set=true, id=n01)",
    #         "add_qedge(source_id=n00, target_id=n01, id=e00)",
    #         "expand(edge_id=e00)",
    #         "overlay(action=predict_drug_treats_disease)",
    #         "return(message=true, store=false)",
    #     ]}}
    # [response, message] = _do_arax_query(query)
    # assert response.status == 'OK'
    # all_vals = [float(y.value) for x in message.knowledge_graph.edges for y in x.edge_attributes if y.name == 'probability_treats']
    # comp_val = np.mean(all_vals) + np.std(all_vals)
    # comp_len = len([x for x in all_vals if x >= comp_val])
    # query = {"previous_message_processing_plan": {"processing_actions": [
    #         "create_message",
    #         "add_qnode(curie=DOID:1588, id=n00)",
    #         "add_qnode(type=chemical_substance, is_set=true, id=n01)",
    #         "add_qedge(source_id=n00, target_id=n01, id=e00)",
    #         "expand(edge_id=e00)",
    #         "overlay(action=predict_drug_treats_disease)",
    #         "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=probability_treats, type=std, remove_connected_nodes=f)",
    #         "return(message=true, store=false)",
    #     ]}}
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:2089, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=compute_ngd, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=N1)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    all_vals = [float(y.value) for x in message.knowledge_graph.edges if x.edge_attributes is not None for y in x.edge_attributes if y.name == 'normalized_google_distance']
    comp_val = np.mean(all_vals) - np.std(all_vals)
    comp_len = len([x for x in all_vals if x < comp_val])
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:2089, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG1)",
            "overlay(action=compute_ngd, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=N1)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=normalized_google_distance, type=std, remove_connected_nodes=f)",
            "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges if x.edge_attributes is not None for y in x.edge_attributes if y.name == 'normalized_google_distance']
    assert len(vals) == comp_len
    assert np.max(vals) < comp_val

def test_default_std_top_n():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:2089, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG1)",
            "overlay(action=compute_ngd, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=N1)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=normalized_google_distance, type=n, remove_connected_nodes=f)",
            "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges if x.edge_attributes is not None for y in x.edge_attributes if y.name == 'normalized_google_distance']
    assert len(vals) == 50
    assert np.max(vals) < 0.87

if __name__ == "__main__":
    pytest.main(['-v'])