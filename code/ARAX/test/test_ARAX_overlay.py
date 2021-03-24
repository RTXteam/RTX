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


def _attribute_tester(message, attribute_name: str, attribute_type: str, num_different_values=2, num_edges_of_interest=1):
    """
    Tests attributes of a message
    message: returned from _do_arax_query
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    num_edges_of_interest: the minimum number of edges in the KG you wish to see have the attribute of interest
    """
    edges_of_interest = []
    values = set()
    for edge in message.knowledge_graph.edges.values():
        if hasattr(edge, 'attributes') and edge.attributes:
            for attr in edge.attributes:
                if attr.name == attribute_name:
                    edges_of_interest.append(edge)
                    assert attr.type == attribute_type
                    values.add(attr.value)
    assert len(edges_of_interest) >= num_edges_of_interest
    if edges_of_interest:
        assert len(values) >= num_different_values


def _virtual_tester(message: Message, edge_predicate: str, relation: str, attribute_name: str, attribute_type: str,
                    num_different_values=2, num_edges_of_interest=1):
    """
    Tests overlay functions that add virtual edges
    message: returned from _do_arax_query
    edge_predicate: the name of the virtual edge (eg. biolink:has_jaccard_index_with)
    relation: the relation you picked for the virtual_edge_relation (eg. N1)
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    num_edges_of_interest: the minimum number of virtual edges you wish to see have been added to the KG
    """
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert edge_predicate in edge_predicates_in_kg
    edges_of_interest = [x for x in message.knowledge_graph.edges.values() if x.relation == relation]
    assert len(edges_of_interest) >= num_edges_of_interest
    if edges_of_interest:
        values = set()
        for edge in edges_of_interest:
            assert hasattr(edge, 'attributes')
            assert edge.attributes
            assert edge.attributes[0].name == attribute_name
            values.add(edge.attributes[0].value)
            assert edge.attributes[0].type == attribute_type
        # make sure two or more values were added
        assert len(values) >= num_different_values


def test_jaccard():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:14717, key=n00)",
        "add_qnode(category=biolink:biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_jaccard_index_with' in edge_predicates_in_kg
    jaccard_edges = [x for x in message.knowledge_graph.edges.values() if x.relation == "J1"]
    for edge in jaccard_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].name == 'jaccard_index'
        assert edge.attributes[0].value >= 0


def test_add_node_pmids():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:384, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "overlay(action=add_node_pmids, max_num=15)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    # check response status
    assert response.status == 'OK'
    # check if there are nodes with attributes
    nodes_with_attributes = [x for x in message.knowledge_graph.nodes.values() if hasattr(x, 'attributes')]
    assert len(nodes_with_attributes) > 0
    # check if pmids were added
    nodes_with_pmids = []
    for node in nodes_with_attributes:
        for attr in node.attributes:
            if attr.name == 'pubmed_ids':
                nodes_with_pmids.append(node)
    assert len(nodes_with_pmids) > 0
    # check types
    for node in nodes_with_pmids:
        for attr in node.attributes:
            if attr.name == "pubmed_ids":
                assert attr.type == 'EDAM:data_0971'
                assert attr.value.__class__ == list


def test_compute_ngd_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:384, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "overlay(action=compute_ngd, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=N1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_normalized_google_distance_with' in edge_predicates_in_kg
    ngd_edges = [x for x in message.knowledge_graph.edges.values() if x.relation == "N1"]
    assert len(ngd_edges) > 0
    for edge in ngd_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        attribute_names = {attribute.name: attribute.value for attribute in edge.attributes}
        assert "publications" in attribute_names
        assert len(attribute_names["publications"]) <= 30
        assert edge.attributes[0].name == 'normalized_google_distance'
        assert float(edge.attributes[0].value) >= 0


def test_compute_ngd_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:384, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    ngd_edges = []
    for edge in message.knowledge_graph.edges.values():
        if hasattr(edge, 'attributes'):
            for attr in edge.attributes:
                if attr.name == 'normalized_google_distance':
                    ngd_edges.append(edge)
                    assert float(attr.value) >= 0
                    assert attr.type == 'EDAM:data_2526'
    assert len(ngd_edges) > 0
    for edge in ngd_edges:
        attribute_names = {attribute.name: attribute.value for attribute in edge.attributes}
        assert "ngd_publications" in attribute_names
        assert len(attribute_names["ngd_publications"]) <= 30


def test_FET_ex1():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:12889, key=n00, category=disease)",
        "add_qnode(category=protein, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01,key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_key=n01)",
        "add_qnode(category=chemical_substance, is_set=true, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:physically_interacts_with)",
        "expand(edge_key=e01, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, rel_edge_key=e01, filter_type=cutoff, value=0.05)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p-value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 2
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        edge_attributes_dict = {attr.name:attr.value for attr in edge.attributes}
        assert edge.attributes[0].name == 'fisher_exact_test_p-value'
        assert edge.attributes[0].type == 'EDAM:data_1669'
        assert edge_attributes_dict['is_defined_by'] == 'ARAX'
        assert edge_attributes_dict['provided_by'] == 'ARAX'
        if edge.relation == 'FET1':
            assert 0 <= float(edge.attributes[0].value) < 0.001
        else:
            assert 0 <= float(edge.attributes[0].value) < 0.05
    FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    assert len(FET_query_edges) == 2
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 3
    for key, query_edge in FET_query_edges.items():
        assert hasattr(query_edge, 'predicate')
        assert query_edge.predicate == 'biolink:has_fisher_exact_test_p-value_with'
        assert key == query_edge.relation
        assert query_edge.subject in query_node_keys
        assert query_edge.object in query_node_keys


@pytest.mark.slow
def test_FET_ex2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:12889, key=n00, category=disease)",
        "add_qnode(category=protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, virtual_relation_label=FET, object_qnode_key=n01, rel_edge_key=e00, top_n=20)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p-value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation and x.relation.find("FET") != -1]
    assert len(FET_edges) >= 2
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 1
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        edge_attributes_dict = {attr.name:attr.value for attr in edge.attributes}
        assert edge.attributes[0].name == 'fisher_exact_test_p-value'
        assert edge.attributes[0].type == 'EDAM:data_1669'
        assert edge_attributes_dict['is_defined_by'] == 'ARAX'
        assert edge_attributes_dict['provided_by'] == 'ARAX'
    FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    assert len(FET_query_edges) == 1
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 2
    for key, query_edge in FET_query_edges.items():
        assert hasattr(query_edge, 'predicate')
        assert query_edge.predicate == 'biolink:has_fisher_exact_test_p-value_with'
        assert key == query_edge.relation
        assert query_edge.subject in query_node_keys
        assert query_edge.object in query_node_keys


@pytest.mark.slow
def test_paired_concept_frequency_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_paired_concept_frequency_with', 'CP1', 'paired_concept_frequency', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_paired_concept_frequency_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=paired_concept_frequency)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_observed_expected_ratio_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info,observed_expected_ratio=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'CP1', 'observed_expected_ratio', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_observed_expected_ratio_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=observed_expected_ratio)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_chi_square_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_chi_square_with', 'CP1', 'chi_square', 'EDAM:data_0951', 2)


@pytest.mark.slow
def test_chi_square_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=chi_square)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 2)


def test_predict_drug_treats_disease_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0, category=biolink:Disease)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 2)


def test_predict_drug_treats_disease_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _attribute_tester(message, 'probability_treats', 'EDAM:data_0951', 2)


def test_issue_832():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 2)


def test_issue_832_non_drug():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(id=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    # Make sure that no probability_treats were added
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'probability_treats' not in edge_predicates_in_kg


@pytest.mark.slow
def test_issue_840():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_paired_concept_frequency_with', 'V1', 'paired_concept_frequency', 'EDAM:data_0951', 2)

    # And for the non-virtual test
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
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
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    # Make sure that no probability_treats were added
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'paired_concept_frequency' not in edge_predicates_in_kg

    # Now for the non-virtual test
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    # Make sure that no probability_treats were added
    for edge in message.knowledge_graph.edges.values():
        for attribute in edge.attributes:
            assert attribute.name != 'paired_concept_frequency'


@pytest.mark.slow
def test_issue_892():
    query = {"operations": {"actions": [
        "add_qnode(id=DOID:11830, category=biolink:Disease, key=n00)",
        "add_qnode(category=biolink:Gene, id=[UniProtKB:P39060, UniProtKB:O43829, UniProtKB:P20849], is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=BTE)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 10)


def test_overlay_exposures_data_virtual():
    query = {"operations": {"actions": [
        "add_qnode(name=CHEMBL.COMPOUND:CHEMBL635, key=n0)",
        "add_qnode(name=MESH:D052638, key=n1)",
        "expand(kp=ARAX/KG2)",
        "overlay(action=overlay_exposures_data, virtual_relation_label=E1, subject_qnode_key=n0, object_qnode_key=n1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    print(response.show())
    _virtual_tester(message, 'biolink:has_icees_p-value_with', 'E1', 'icees_p-value', 'EDAM:data_1669', 1, 0)


def test_overlay_exposures_data_attribute():
    query = {"operations": {"actions": [
        "add_qnode(name=MONDO:0012607, key=n0)",
        "add_qnode(name=MONDO:0010940, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(kp=ARAX/KG2)",
        "overlay(action=overlay_exposures_data)",
        "resultify()",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    print(response.show())
    _attribute_tester(message, 'icees_p-value', 'EDAM:data_1669', 1, 0)


@pytest.mark.slow
def test_overlay_clinical_info_no_ids():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "expand(kp=ARAX/KG2)",
        "overlay(action=overlay_clinical_info,COHD_method=paired_concept_frequency,virtual_relation_label=C1,subject_qnode_key=n0,object_qnode_key=n1)",
        "overlay(action=overlay_clinical_info,COHD_method=observed_expected_ratio,virtual_relation_label=C2,subject_qnode_key=n0,object_qnode_key=n1)",
        "overlay(action=overlay_clinical_info,COHD_method=chi_square,virtual_relation_label=C3,subject_qnode_key=n0,object_qnode_key=n1)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_paired_concept_frequency_with', 'C1', 'paired_concept_frequency', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 1)
    _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C2', 'observed_expected_ratio', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 1)
    _virtual_tester(message, 'biolink:has_chi_square_with', 'C3', 'chi_square', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 1)


if __name__ == "__main__":
    pytest.main(['-v'])
