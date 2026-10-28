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
            "add_qnode(name=UMLS:C0040250, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=3)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results == len(message.results) == 3

def test_no_results():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=MONDO:0002967, key=n00)",
            "add_qnode(ids=CHEBI:83766, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
            "overlay(action=add_node_pmids, max_num=15)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert 'WARNING: [] filter_results called with no results.' in response.show(level=ARAXResponse.WARNING)
    assert response.status == 'OK'

@pytest.mark.slow
def test_prune():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:4337, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
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
        for analysis in result.analyses:
            for edge_binding_list in analysis.edge_bindings.values():
                for edge_binding in edge_binding_list:
                    result_edges.add(edge_binding.id)
    # The KG may also hold support-graph nodes/edges, which results reach via support graphs rather than bindings
    kg_edges = message.knowledge_graph.edges
    aux_graph_keys_to_visit = {aux_graph_key for result in message.results for analysis in result.analyses
                               for aux_graph_key in analysis.support_graphs or []}
    visited_aux_graph_keys = set()
    edge_keys_to_check = set(result_edges)
    while edge_keys_to_check or aux_graph_keys_to_visit:
        for edge_key in edge_keys_to_check:
            for attribute in kg_edges[edge_key].attributes or []:
                if attribute.attribute_type_id == "biolink:support_graphs":
                    aux_graph_keys_to_visit.update(attribute.value)
        edge_keys_to_check = set()
        for aux_graph_key in aux_graph_keys_to_visit - visited_aux_graph_keys:
            visited_aux_graph_keys.add(aux_graph_key)
            for edge_key in message.auxiliary_graphs[aux_graph_key].edges:
                if edge_key not in result_edges:
                    result_edges.add(edge_key)
                    edge_keys_to_check.add(edge_key)
                result_nodes.update({kg_edges[edge_key].subject, kg_edges[edge_key].object})
        aux_graph_keys_to_visit = set()
    for key, node in message.knowledge_graph.nodes.items():
        assert key in result_nodes
    for key, edge in message.knowledge_graph.edges.items():
        assert key in result_edges

def test_warning():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UMLS:C0040250, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=3)",
            "filter_results(action=sort_by_node_attribute, node_attribute=asdfghjkl, direction=a, max_results=3)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 3

@pytest.mark.slow
def test_sort_by_edge_attribute():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:14221, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_key=[e00,e01], kp=infores:retriever)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=20, qedge_keys=[J2])",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    #return response, message
    assert response.status == 'OK'
    assert len(message.results) == 20

def test_sort_by_node_attribute():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UMLS:C0040250, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=3, qnode_keys=[n01])",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 3
    # add something to test if the results are assending and the correct numbers

def test_sort_by_score():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UMLS:C0040250, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:retriever)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_score, direction=a, max_results=3)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 3
    result_scores = [x.analyses[0].score for x in message.results]
    assert result_scores == sorted(result_scores)
    assert max(result_scores) <= 1

if __name__ == "__main__":
    pytest.main(['-v'])
