#!/usr/bin/env python3

# Intended to test ARAX connect

import sys
import os
import pytest
from collections import Counter
import copy
import json
import ast
from typing import List, Union

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

PACKAGE_PARENT = '../../UI/OpenAPI/openapi_server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.message import Message


def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, response.envelope.message]


def _attribute_tester(message, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests attributes of a message
    message: returned from _do_arax_query
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM-DATA:1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edges_of_interest = []
    values = set()
    for key, edge in message.knowledge_graph.edges.items():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        if hasattr(edge, 'edge_attributes'):
            for attr in edge.edge_attributes:
                if attr.original_attribute_name == attribute_name:
                    edges_of_interest.append(edge)
                    assert attr.attribute_type_id == attribute_type
                    values.add(attr.value)
    assert len(edges_of_interest) > 0
    assert len(values) >= num_different_values


def _virtual_tester(message: Message, edge_predicate: str, relation: str, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests overlay functions that add virtual edges
    message: returned from _do_arax_query
    edge_predicate: the name of the virtual edge (eg. biolink:has_jaccard_index_with)
    relation: the relation you picked for the virtual_edge_relation (eg. N1)
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM-DATA:1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert edge_predicate in edge_predicates_in_kg
    edges_of_interest = [x for x in message.knowledge_graph.edges.values() if x.relation == relation]
    values = set()
    assert len(edges_of_interest) > 0
    for edge in edges_of_interest:
        assert hasattr(edge, 'attributes')
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == attribute_name
        values.add(edge.attributes[0].value)
        assert edge.attributes[0].attribute_type_id == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_connect_acetaminophen_to_ptgs1():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, key=n00)",
            "add_qnode(ids=UniProtKB:P23219, key=n01)",
            "connect(action=connect_nodes)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) > 0
    assert len(message.results) > 0


@pytest.mark.slow
def test_connect_nodes_1_hop():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:3312, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "connect(action=connect_nodes)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) > 0
    assert len(message.results) > 0


@pytest.mark.slow
def test_connect_nodes_2_hop():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UniProtKB:P18509, key=n00)",
            "add_qnode(name=MESH:D004781, key=n01)",
            "connect(action=connect_nodes)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 2
    assert len(message.results) > 0


@pytest.mark.slow
def test_connect_nodes_subgraph_2_hop():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UniProtKB:P54105,key=n02)",
            "add_qnode(name=UniProtKB:P18509,key=n00)",
            "add_qedge(subject=n00,object=n02,key=e00)",
            "expand(kp=infores:rtx-kg2,edge_key=e00)",
            "add_qnode(name=MESH:D004781,key=n01)",
            "connect(action=connect_nodes,qnode_keys=[n00,n01])",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 3
    assert len(message.results) > 0

@pytest.mark.slow
def test_connect_nodes_3_disconnected_nodes():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UniProtKB:P54105,key=n02)",
            "add_qnode(name=UniProtKB:P18509,key=n00)",
            "add_qnode(name=MESH:D004781,key=n01)",
            "connect(action=connect_nodes)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 3
    assert len(message.results) > 0

@pytest.mark.slow
def test_1881():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=glucose, key=n0)",
            "add_qnode(name=diabetes, key=n1)",
            "connect(action=connect_nodes, max_path_length=3, shortest_path=false)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=30)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 3
    assert len(message.results) > 0

@pytest.mark.slow
def test_none_object():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=glucose, key=n0)",
            "add_qnode(name=diabetes, key=n1)",
            "connect(action=connect_nodes, shortest_path=false)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=30)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0


if __name__ == "__main__":
    pytest.main(['-v'])