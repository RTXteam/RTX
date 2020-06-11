#!/usr/bin/env python3

# Intended to test our more complicated workflows

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


def _attribute_tester(message, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests attributes of a message
    message: returned from _do_arax_query
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'data:1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edges_of_interest = []
    values = set()
    for edge in message.knowledge_graph.edges:
        if hasattr(edge, 'edge_attributes'):
            for attr in edge.edge_attributes:
                if attr.name == attribute_name:
                    edges_of_interest.append(edge)
                    assert attr.type == attribute_type
                    values.add(attr.value)
    assert len(edges_of_interest) > 0
    assert len(values) >= num_different_values


def _virtual_tester(message: Message, edge_type: str, relation: str, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests overlay functions that add virtual edges
    message: returned from _do_arax_query
    edge_type: the name of the virtual edge (eg. has_jaccard_index_with)
    relation: the relation you picked for the virtual_edge_relation (eg. N1)
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'data:1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert edge_type in edge_types_in_kg
    edges_of_interest = [x for x in message.knowledge_graph.edges if x.relation == relation]
    values = set()
    assert len(edges_of_interest) > 0
    for edge in edges_of_interest:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == attribute_name
        values.add(edge.edge_attributes[0].value)
        assert edge.edge_attributes[0].type == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_example_2():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 15  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'data:0951', 2)
    _virtual_tester(message, 'has_jaccard_index_with', 'J1', 'jaccard_index', 'data:1772', 2)


def test_example_3():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(name=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01])",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)",
        "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None
    _virtual_tester(message, 'has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'data:0951', 2)
    _virtual_tester(message, 'has_normalized_google_distance_with', 'N1', 'normalized_google_distance', 'data:2526', 2)


if __name__ == "__main__":
    pytest.main(['-v'])

