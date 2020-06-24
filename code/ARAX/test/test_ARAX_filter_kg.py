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

def test_default_std_dev():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=probability_treats, type=std, remove_connected_nodes=f)",
            "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges for y in x.edge_attributes if y.name == 'probability_treats']
    assert len(vals) == 21
    assert np.min(vals) > 0.3381782537885432

def test_default_std_top_n():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=probability_treats, type=n, remove_connected_nodes=f)",
            "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges for y in x.edge_attributes if y.name == 'probability_treats']
    assert len(vals) == 50
    assert np.min(vals) > 0.2587258724407653

if __name__ == "__main__":
    pytest.main(['-v'])