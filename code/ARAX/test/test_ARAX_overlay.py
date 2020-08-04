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
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, araxq.message]


def _attribute_tester(message, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests attributes of a message
    message: returned from _do_arax_query
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
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
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
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
        "add_qnode(curie=DOID:14717, id=n00)",
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
                assert attr.type == 'EDAM:data_0971'
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
                    assert attr.type == 'EDAM:data_2526'
    assert len(ngd_edges) > 0


def test_FET_ex1():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:12889, id=n00, type=disease)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01,id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1, rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n01)",
        "add_qnode(type=chemical_substance, is_set=true, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=e01, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2, rel_edge_id=e01, cutoff=0.05)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 2
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        if edge.relation == 'FET1':
            assert 0 <= float(edge.edge_attributes[0].value) < 0.001
        else:
            assert 0 <= float(edge.edge_attributes[0].value) < 0.05
        assert edge.edge_attributes[0].type == 'EDAM:data_1669'
        assert edge.is_defined_by == 'ARAX'
        assert edge.provided_by == 'ARAX'
    FET_query_edges = [edge for edge in message.query_graph.edges if edge.id.find("FET") != -1]
    assert len(FET_query_edges) == 2
    query_node_ids = [node.id for node in message.query_graph.nodes]
    assert len(query_node_ids) == 3
    for query_exge in FET_query_edges:
        assert hasattr(query_exge, 'type')
        assert query_exge.type == 'has_fisher_exact_test_p-value_with'
        assert query_exge.id == query_exge.relation
        assert query_exge.source_id in query_node_ids
        assert query_exge.target_id in query_node_ids


@pytest.mark.slow
def test_FET_ex2():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:12889, id=n00, type=disease)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, virtual_relation_label=FET, target_qnode_id=n01, rel_edge_id=e00, top_n=20)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
    assert len(FET_edges) >= 2
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 1
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        assert edge.edge_attributes[0].type == 'EDAM:data_1669'
        assert edge.is_defined_by == 'ARAX'
        assert edge.provided_by == 'ARAX'
    FET_query_edges = [edge for edge in message.query_graph.edges if edge.id.find("FET") != -1]
    assert len(FET_query_edges) == 1
    query_node_ids = [node.id for node in message.query_graph.nodes]
    assert len(query_node_ids) == 2
    for query_exge in FET_query_edges:
        assert hasattr(query_exge, 'type')
        assert query_exge.type == 'has_fisher_exact_test_p-value_with'
        assert query_exge.id == query_exge.relation
        assert query_exge.source_id in query_node_ids
        assert query_exge.target_id in query_node_ids


@pytest.mark.slow
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
    _virtual_tester(message, 'has_paired_concept_frequency_with', 'CP1', 'paired_concept_frequency', 'EDAM:data_0951', 2)


@pytest.mark.slow
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
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 2)


@pytest.mark.slow
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
    _virtual_tester(message, 'has_observed_expected_ratio_with', 'CP1', 'observed_expected_ratio', 'EDAM:data_0951', 2)


@pytest.mark.slow
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
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 2)


@pytest.mark.slow
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
    _virtual_tester(message, 'has_chi_square_with', 'CP1', 'chi_square', 'EDAM:data_0951', 2)


@pytest.mark.slow
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
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 2)


def test_predict_drug_treats_disease_virtual():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:9008, id=n0, type=disease)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n1, target_qnode_id=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 2)


def test_predict_drug_treats_disease_attribute():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:9008, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'probability_treats', 'EDAM:data_0951', 2)


def test_issue_832():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:9008, id=n0)",
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
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 2)


def test_issue_832_non_drug():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=UniProtKB:Q13627, id=n0)",
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
    # Make sure that no probability_treats were added
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'probability_treats' not in edge_types_in_kg


@pytest.mark.slow
def test_issue_840():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:1588, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n1, target_qnode_id=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'has_paired_concept_frequency_with', 'V1', 'paired_concept_frequency', 'EDAM:data_0951', 2)

    # And for the non-virtual test
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
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_issue_840_non_drug():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=UniProtKB:Q13627, id=n0)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n1, target_qnode_id=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    # Make sure that no probability_treats were added
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'paired_concept_frequency' not in edge_types_in_kg

    # Now for the non-virtual test
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=UniProtKB:Q13627, id=n0)",
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
    # Make sure that no probability_treats were added
    for edge in message.knowledge_graph.edges:
        for attribute in edge.edge_attributes:
            assert attribute.name != 'paired_concept_frequency'


@pytest.mark.slow
def test_issue_892():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(curie=DOID:11830, type=disease, id=n00)",
        "add_qnode(type=gene, curie=[UniProtKB:P39060, UniProtKB:O43829, UniProtKB:P20849], is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(kp=BTE)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=true)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 10)


def test_overlay_exposures_data():
    # NOTE: This example only produces ICEES edge attributes with p-values of 0; still need to find better example
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=MONDO:0012607, id=n0)",
        "add_qnode(curie=MONDO:0010940, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(kp=ARAX/KG2, use_synonyms=false)",
        "overlay(action=overlay_exposures_data)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    print(response.show(level=response.DEBUG))


if __name__ == "__main__":
    pytest.main(['-v'])
