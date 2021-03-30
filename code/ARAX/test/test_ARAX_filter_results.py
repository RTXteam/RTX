#!/usr/bin/env python3

# Usage:
# run all: pytest -v test_ARAX_filter_results.py
# run just certain tests: pytest -v test_ARAX_filter_results.py -k test_sort

import sys
import os
import pytest
from collections import Counter
import copy
import json
import ast
from typing import List, Union

sys.path.append(os.getcwd()+"/../ARAXQuery")
#sys.path.append(os.getcwd()+"/../ARAXQuery")
from ARAX_filter_results import ARAXFilterResults
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


def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    #return [response, araxq.message]
    return [response, response.envelope.message]

def test_command_definitions():
    fr = ARAXFilterResults()
    assert fr.allowable_actions == set(fr.command_definitions.keys())

def test_n_results():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results == len(message.results)

def test_no_results():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert 'WARNING: [] filter_results called with no results.' in response.show(level=ARAXResponse.WARNING)
    assert response.status == 'OK'

def test_prune():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20, prune_kg=f)",
            "return(message=true, store=false)"
        ]}}
    [no_prune_response, no_prune_message] = _do_arax_query(query)
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    result_nodes = set()
    result_edges = set()
    for result in message.results:
        for node_binding_list in result.node_bindings.values():
            for node_binding in node_binding_list:
                result_nodes.add(node_binding.id)
        for edge_binding_list in result.edge_bindings.values():
            for edge_binding in edge_binding_list:
                result_edges.add(edge_binding.id)
    for key, node in message.knowledge_graph.nodes.items():
        assert key in result_nodes
    for key, edge in message.knowledge_graph.edges.items():
        assert key in result_edges
    assert len(message.knowledge_graph.nodes) < len(no_prune_message.knowledge_graph.nodes)
    assert len(message.knowledge_graph.edges) < len(no_prune_message.knowledge_graph.edges)

def test_warning():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "filter_results(action=sort_by_node_attribute, node_attribute=asdfghjkl, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20

def test_sort():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20
    # add something to test if the results are assending and the correct numbers


if __name__ == "__main__":
    pytest.main(['-v'])
