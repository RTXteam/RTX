#!/usr/bin/env python3

# Intended to test ARAX connect

import sys
import os
import pytest
import copy
import json
import ast
from typing import List, Union

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
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


# TODO add DSL tests for new schema
# def test_connect_ulcerative_colitis_to_adalimumab():
#     query = {"operations": {"actions": [
#         "create_message",
#         "add_qnode(ids=MONDO:0005101, key=n_src)",
#         "add_qnode(ids=UNII:FYS6T7F842, key=n_dst)",
#         "add_qnode(categories=biolink:Disease, key=n_cns)",
#         "add_qpath(key=p0,subject=n_src,object=n_dst,predicates=biolink:related_to,intermediate_nodes=n_cns)",
#         "connect(action=connect_nodes, max_path_length=3)",
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     assert len(response.envelope.message.results) > 0
#     assert len(response.envelope.message.results[0].node_bindings) == 3
#     assert len(response.envelope.message.auxiliary_graphs) > 0
#     assert len(response.envelope.message.query_graph.nodes) == 3
#     assert len(response.envelope.message.query_graph.paths) == 1
#
#
# def test_connect_resveratrol_glyoxalase():
#     query = {"operations": {"actions": [
#         "create_message",
#         "add_qnode(ids=PUBCHEM.COMPOUND:445154, key=n_src)",
#         "add_qnode(ids=NCBIGene:2739, key=n_dst)",
#         "add_qpath(key=p0,subject=n_src,object=n_dst,predicates=biolink:related_to)",
#         "connect(action=connect_nodes, max_path_length=4)",
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     assert len(response.envelope.message.results) > 0
#     assert len(response.envelope.message.results[0].node_bindings) == 2
#     assert len(response.envelope.message.auxiliary_graphs) > 0
#     assert len(response.envelope.message.query_graph.nodes) == 2
#     assert len(response.envelope.message.query_graph.paths) == 1
#
#
# def test_connect_pde5i_alzheimer():
#     query = {"operations": {"actions": [
#         "create_message",
#         "add_qnode(ids=MONDO:0004975, key=n_src)",
#         "add_qnode(ids=UMLS:C1318700, key=n_dst)",
#         "add_qpath(key=p0,subject=n_src,object=n_dst,predicates=biolink:related_to)",
#         "connect(action=connect_nodes, max_path_length=4)",
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     assert len(response.envelope.message.results) > 0
#     assert len(response.envelope.message.results[0].node_bindings) == 2
#     assert len(response.envelope.message.auxiliary_graphs) > 0
#     assert len(response.envelope.message.query_graph.nodes) == 2
#     assert len(response.envelope.message.query_graph.paths) == 1
#
#
# def test_glucose_diabetes():
#     query = {"operations": {"actions": [
#         "create_message",
#         "add_qnode(name=CHEBI:37626, key=n_src)",
#         "add_qnode(name=MONDO:0005015, key=n_dst)",
#         "add_qpath(key=p0,subject=n_src,object=n_dst,predicates=biolink:related_to)",
#         "connect(action=connect_nodes, max_path_length=3)"
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     assert len(response.envelope.message.results) > 0
#     assert len(response.envelope.message.results[0].node_bindings) == 2
#     assert len(response.envelope.message.auxiliary_graphs) > 0
#     assert len(response.envelope.message.query_graph.nodes) == 2
#     assert len(response.envelope.message.query_graph.paths) == 1


def test_TRAPI_unconstrained_query():
    query = {"operations": {"actions": [
        "add_qnode(ids=MONDO:0005011, key=n0)",
        "add_qnode(ids=MONDO:0005180, key=n1)",
        "add_qpath(subject=n0, object=n1)",
        "connect(action=connect_nodes, max_path_length=2)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(response.envelope.message.results) == 1
    assert len(response.envelope.message.results[0].node_bindings) == 2
    response.debug(f"analyses length: {len(response.envelope.message.results[0].analyses)}")
    assert len(response.envelope.message.results[0].analyses) > 0
    response.debug(f"auxiliary_graphs length: {len(response.envelope.message.auxiliary_graphs)}")
    assert len(response.envelope.message.auxiliary_graphs) > 0
    assert len(response.envelope.message.query_graph.nodes) == 2
    assert len(response.envelope.message.query_graph.paths) == 1

@pytest.mark.slow
def test_TRAPI_constrained_query():
    query = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": ["CHEBI:37626"]
                    },
                    "n1": {
                        "ids": ["MONDO:0005015"]
                    },
                },
                "paths": {
                    "p0": {
                        "subject": "n0",
                        "object": "n1",
                        "constraints": [
                            {
                                "intermediate_categories": ["biolink:Gene"]
                            }
                        ]
                    }
                }
            }
        }
    }

    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    assert len(response.envelope.message.results) == 1
    assert len(response.envelope.message.results[0].node_bindings) == 2
    response.debug(f"analyses length: {len(response.envelope.message.results[0].analyses)}")
    assert len(response.envelope.message.results[0].analyses) > 0
    response.debug(f"auxiliary_graphs length: {len(response.envelope.message.auxiliary_graphs)}")
    assert len(response.envelope.message.auxiliary_graphs) > 0
    assert len(response.envelope.message.query_graph.nodes) == 2
    assert len(response.envelope.message.query_graph.paths) == 1


if __name__ == "__main__":
    pytest.main(['-v'])
