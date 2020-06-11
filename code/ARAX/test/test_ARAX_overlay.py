#!/usr/bin/env python3

# Usage:
# run all: pytest -v test_ARAX_overlay.py
# run just certain tests: pytest -v test_ARAX_overlay.py -k test_jaccard

import sys
import os
import pytest
from collections import Counter
import copy
import json
import ast
from typing import List, Union

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
    return [response, araxq.message]

def test_jaccard():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_jaccard_index_with' in edge_types_in_kg
    jaccard_edges = [x for x in message.knowledge_graph.edges if x.id == "J1"]
    for edge in jaccard_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'jaccard_index'
        assert edge.edge_attributes[0].value >= 0






if __name__ == "__main__":
    pytest.main(['-v'])
