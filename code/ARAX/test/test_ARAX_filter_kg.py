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
from ARAX_filter_kg import ARAXFilterKG
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.edge_binding import EdgeBinding
from openapi_server.models.result import Result
from openapi_server.models.message import Message


def _do_arax_query(query: dict, print_response: bool=True) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK' and print_response:
        print(response.show(level=response.DEBUG))
    #return [response, araxq.message]
    return [response, response.envelope.message]

def test_command_definitions():
    fkg = ARAXFilterKG()
    assert fkg.allowable_actions == set(fkg.command_definitions.keys())

def test_warning():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=asdfghjkl, direction=below, threshold=.2)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20

def test_error():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00, predicate=biolink:contraindicated_for)",
            "expand(edge_key=e00, kp=ARAX/KG2)",
            "filter_kg(action=remove_edges_by_predicate, edge_predicate=biolink:contraindicated_for, remove_connected_nodes=t)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query, False)
    assert response.status == 'ERROR'
    assert response.error_code == "RemovedQueryNode"

def test_default_std_dev():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:5199, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    all_vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.name == 'jaccard_index']
    comp_val = np.mean(all_vals) + np.std(all_vals)
    comp_len = len([x for x in all_vals if x > comp_val])
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:5199, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=std, remove_connected_nodes=f)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.name == 'jaccard_index']
    assert len(vals) == comp_len
    assert np.min(vals) > comp_val

def test_std_dev():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:5199, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    all_vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.name == 'jaccard_index']
    assert len(all_vals) > 0
    comp_val = np.mean(all_vals) - 0.25*np.std(all_vals)
    comp_len = len([x for x in all_vals if x < comp_val])
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:5199, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=std, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.name == 'jaccard_index']
    assert len(vals) == comp_len
    assert len([x for x in vals if x == 1]) == 0
    assert np.max(vals) < comp_val

def test_default_top_n():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:5199, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=n, remove_connected_nodes=f)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.name == 'jaccard_index']
    assert len(vals) == 50
    assert sum([x == 1 for x in vals]) == 8


if __name__ == "__main__":
    pytest.main(['-v'])
