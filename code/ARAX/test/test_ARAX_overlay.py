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
    jaccard_edges = [x for x in message.knowledge_graph.edges if x.relation == "J1"]
    for edge in jaccard_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'jaccard_index'
        assert edge.edge_attributes[0].value >= 0


def test_add_node_pmids():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:384, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "overlay(action=add_node_pmids, max_num=15)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    # check response status
    assert response.status == 'OK'
    # check if there are nodes with attributes
    nodes_with_attributes = [x for x in message.knowledge_graph.nodes if hasattr(x, 'node_attributes')]
    assert len(nodes_with_attributes) > 0
    # check if pmids were added
    nodes_with_pmids = []
    for node in nodes_with_attributes:
        for attr in node.node_attributes:
            if attr.name == 'pubmed_ids':
                nodes_with_pmids.append(node)
    assert len(nodes_with_pmids) > 0
    # check types
    for node in nodes_with_pmids:
        for attr in node.node_attributes:
            if attr.name == "pubmed_ids":
                assert attr.type == 'data:0971'
                assert attr.value.__class__ == list


def test_compute_ngd_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:384, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "overlay(action=compute_ngd, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=N1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_normalized_google_distance_with' in edge_types_in_kg
    ngd_edges = [x for x in message.knowledge_graph.edges if x.relation == "N1"]
    assert len(ngd_edges) > 0
    for edge in ngd_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'normalized_google_distance'
        assert float(edge.edge_attributes[0].value) >= 0


def test_compute_ngd_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:384, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    ngd_edges = []
    for edge in message.knowledge_graph.edges:
        if hasattr(edge, 'edge_attributes'):
            for attr in edge.edge_attributes:
                if attr.name == 'normalized_google_distance':
                    ngd_edges.append(edge)
                    assert float(attr.value) >= 0
                    assert attr.type == 'data:2526'
    assert len(ngd_edges) > 0


def test_FET():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521)",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "add_qnode(id=n02, type=biological_process)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET, target_qnode_id=n02, cutoff=0.05)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation == "FET"]
    assert len(FET_edges) > 0
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        assert float(edge.edge_attributes[0].value) >= 0
        assert edge.edge_attributes[0].type == 'data:1669'


def test_paired_concept_frequency_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'has_paired_concept_frequency_with', 'CP1', 'paired_concept_frequency', 'data:0951', 2)


def test_paired_concept_frequency_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'data:0951', 2)


def test_observed_expected_ratio_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info,observed_expected_ratio=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'has_observed_expected_ratio_with', 'CP1', 'observed_expected_ratio', 'data:0951', 2)


def test_observed_expected_ratio_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'observed_expected_ratio', 'data:0951', 2)


def test_chi_square_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, chi_square=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'has_chi_square_with', 'CP1', 'chi_square', 'data:0951', 2)


def test_chi_square_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'chi_square', 'data:0951', 2)


def test_predict_drug_treats_disease_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n1, target_qnode_id=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'data:0951', 2)


def test_predict_drug_treats_disease_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=predict_drug_treats_disease)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'probability_treats', 'data:0951', 2)


if __name__ == "__main__":
    pytest.main(['-v'])
