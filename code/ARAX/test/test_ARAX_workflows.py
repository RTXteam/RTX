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

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAXQuery")
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


def test_option_group_id():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:3312, id=n00)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, type=indicated_for, option_group_id=a, id=e00)",
            "add_qedge(source_id=n00, target_id=n01, type=contraindicated_for, option_group_id=1, id=e01)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        ]}}
    [response, message] = _do_arax_query(query)
    for edge in message.query_graph.edges:
        if edge.id == 'e01':
            assert edge.option_group_id == '1'
        if edge.id == 'e00':
            assert edge.option_group_id == 'a'

def test_exclude():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:3312, id=n00)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, type=indicated_for, id=e00)",
            "add_qedge(source_id=n00, target_id=n01, type=contraindicated_for, exclude=true, id=e01)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    for edge in message.query_graph.edges:
        if edge.id == 'e01':
            assert edge.exclude
        if edge.id == 'e00':
            assert not edge.exclude

@pytest.mark.slow
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
    _virtual_tester(message, 'probably_treats', 'P1', 'probability_treats', 'EDAM:data_0951', 2)
    _virtual_tester(message, 'has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM:data_1772', 2)


def test_example_3():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(name=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=1, remove_connected_nodes=t, qnode_id=n01)",
        "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    #assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert len(message.results) >= 60
    assert message.results[0].essence is not None
    _virtual_tester(message, 'has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'EDAM:data_0951', 2)
    _virtual_tester(message, 'has_normalized_google_distance_with', 'N1', 'normalized_google_distance', 'EDAM:data_2526', 2)


@pytest.mark.slow
def test_FET_example_1():
    # This a FET 3-top example: try to find the phenotypes of drugs connected to proteins connected to DOID:14330
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(curie=DOID:14330, id=n00, type=disease)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1, rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_id=n01)",
        "add_qnode(type=chemical_substance, is_set=true, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=e01, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2, rel_edge_id=e01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_id=n02)",
        "add_qnode(type=phenotypic_feature, id=n03)",
        "add_qedge(source_id=n02, target_id=n03, id=e02)",
        "expand(edge_id=e02, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3, rel_edge_id=e02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_id=n03)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 3
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        assert 0 <= float(edge.edge_attributes[0].value) < 0.005
        assert edge.edge_attributes[0].type == 'EDAM:data_1669'
        assert edge.is_defined_by == 'ARAX'
        assert edge.provided_by == 'ARAX'
    FET_query_edges = [edge for edge in message.query_graph.edges if edge.id.find("FET") != -1]
    assert len(FET_query_edges) == 3
    query_node_ids = [node.id for node in message.query_graph.nodes]
    assert len(query_node_ids) == 4
    for query_exge in FET_query_edges:
        assert hasattr(query_exge, 'type')
        assert query_exge.type == 'has_fisher_exact_test_p-value_with'
        assert query_exge.id == query_exge.relation
        assert query_exge.source_id in query_node_ids
        assert query_exge.target_id in query_node_ids


@pytest.mark.slow
def test_FET_example_2():
    # This a FET 4-top example: try to find the diseases connected to proteins connected to biological_process connected to protein connected to CHEMBL.COMPOUND:CHEMBL521
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
        "add_qnode(id=n01, is_set=true, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n01)",
        "add_qnode(type=biological_process, is_set=true, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=e01, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n02)",
        "add_qnode(type=protein, is_set=true, id=n03)",
        "add_qedge(source_id=n02, target_id=n03, id=e02)",
        "expand(edge_id=e02, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n03)",
        "add_qnode(type=disease, id=n04)",
        "add_qedge(source_id=n03, target_id=n04, id=e03)",
        "expand(edge_id=e03, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n03, target_qnode_id=n04, virtual_relation_label=FET4)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n04)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 4
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        assert 0 <= float(edge.edge_attributes[0].value) < 0.01
        assert edge.edge_attributes[0].type == 'EDAM:data_1669'
        assert edge.is_defined_by == 'ARAX'
        assert edge.provided_by == 'ARAX'
    FET_query_edges = [edge for edge in message.query_graph.edges if edge.id.find("FET") != -1]
    assert len(FET_query_edges) == 4
    query_node_ids = [node.id for node in message.query_graph.nodes]
    assert len(query_node_ids) == 5
    for query_exge in FET_query_edges:
        assert hasattr(query_exge, 'type')
        assert query_exge.type == 'has_fisher_exact_test_p-value_with'
        assert query_exge.id == query_exge.relation
        assert query_exge.source_id in query_node_ids
        assert query_exge.target_id in query_node_ids


@pytest.mark.skip(reason="need issue#846 to be solved")
def test_FET_example_3():
    # This a FET 6-top example: try to find the drugs connected to proteins connected to pathways connected to proteins connected to diseases connected to phenotypes of DOID:14330
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(curie=DOID:14330, id=n00, type=disease)",
        "add_qnode(type=phenotypic_feature, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1, rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n01)",
        "add_qnode(type=disease, is_set=true, id=n02)",
        "add_qedge(source_id=n01,target_id=n02,id=e01,type=has_phenotype)",
        "expand(edge_id=e01,kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2, rel_edge_id=e01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n02)",
        "add_qnode(type=protein, is_set=true, id=n03)",
        "add_qedge(source_id=n02, target_id=n03, id=e02, type=gene_mutations_contribute_to)",
        "expand(edge_id=e02, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3, rel_edge_id=e02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n03)",
        "add_qnode(type=pathway, is_set=true, id=n04)",
        "add_qedge(source_id=n03, target_id=n04, id=e03, type=participates_in)",
        "expand(edge_id=e03, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n03, target_qnode_id=n04, virtual_relation_label=FET4, rel_edge_id=e03)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n04)",
        "add_qnode(type=protein, is_set=true, id=n05)",
        "add_qedge(source_id=n04, target_id=n05, id=e04, type=participates_in)",
        "expand(edge_id=e04, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n04, target_qnode_id=n05, virtual_relation_label=FET5, rel_edge_id=e04)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n05)",
        "add_qnode(type=chemical_substance, id=n06)",
        "add_qedge(source_id=n05, target_id=n06, id=e05, type=physically_interacts_with)",
        "expand(edge_id=e05, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n05, target_qnode_id=n06, virtual_relation_label=FET6, rel_edge_id=e05)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n06)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 6
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        assert 0 <= float(edge.edge_attributes[0].value) < 0.001
        assert edge.edge_attributes[0].type == 'EDAM:data_1669'
        assert edge.is_defined_by == 'ARAX'
        assert edge.provided_by == 'ARAX'
    FET_query_edges = [edge for edge in message.query_graph.edges if edge.id.find("FET") != -1]
    assert len(FET_query_edges) == 6
    query_node_ids = [node.id for node in message.query_graph.nodes]
    assert len(query_node_ids) == 7
    for query_exge in FET_query_edges:
        assert hasattr(query_exge, 'type')
        assert query_exge.type == 'has_fisher_exact_test_p-value_with'
        assert query_exge.id == query_exge.relation
        assert query_exge.source_id in query_node_ids
        assert query_exge.target_id in query_node_ids


@pytest.mark.slow
def test_FET_example_4():
    # This a FET 2-top example collecting nodes and edges from both KG1 and KG2: try to find the disease connected to proteins connected to DOID:14330
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(curie=DOID:14330, id=n00, type=disease)",
        "add_qnode(type=phenotypic_feature, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, virtual_relation_label=FET1, target_qnode_id=n01,rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_attribute,edge_attribute=fisher_exact_test_p-value,direction=above,threshold=0.001,remove_connected_nodes=t,qnode_id=n01)",
        "add_qnode(type=disease, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=e01, kp=ARAX/KG2)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET2, target_qnode_id=n02,rel_edge_id=e01)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_types_in_kg = Counter([x.type for x in message.knowledge_graph.edges])
    assert 'has_fisher_exact_test_p-value_with' in edge_types_in_kg
    kp = set([edge.is_defined_by for edge in message.knowledge_graph.edges])
    assert len(kp) == 3
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation and x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 2
    for edge in FET_edges:
        assert hasattr(edge, 'edge_attributes')
        assert edge.edge_attributes
        assert edge.edge_attributes[0].name == 'fisher_exact_test_p-value'
        if edge.relation == "FET1":
            assert 0 <= float(edge.edge_attributes[0].value) < 0.001
        else:
            assert float(edge.edge_attributes[0].value) >= 0
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
def test_FET_ranking():
    query = {"previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(id=n00,curie=UniProtKB:P14136,type=protein)",
            "add_qnode(type=biological_process, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00,kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET)",
            "resultify()",
            "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    ranks = [result.confidence for result in message.results]
    assert min(ranks) != max(ranks)

@pytest.mark.slow
def test_example_2_kg2():
    query = {"previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",  # seems to work just fine
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.008, remove_connected_nodes=t, qnode_id=n02)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 15 
    assert message.results[0].essence is not None
    _virtual_tester(message, 'has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM:data_1772', 2)


@pytest.mark.slow
def test_clinical_overlay_example():
    """
    Gives an example of a KG that does not have edges that COHD can decorate, but does have pairs of nodes that COHD
    could decorate (eg here is drug and chemical_substance), so add the info in as a virtual edge.
    """
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:11830, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
        # overlay a bunch of clinical info
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C1)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C2)",
        "overlay(action=overlay_clinical_info, chi_square=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C3)",
        # filter some stuff out for the fun of it
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=paired_concept_frequency, direction=above, threshold=0.5, remove_connected_nodes=true, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=above, threshold=1, remove_connected_nodes=true, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=chi_square, direction=below, threshold=0.05, remove_connected_nodes=true, qnode_id=n02)",
        # return results
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    _virtual_tester(message, 'has_paired_concept_frequency_with', 'C1', 'paired_concept_frequency', 'EDAM:data_0951', 2)
    _virtual_tester(message, 'has_observed_expected_ratio_with', 'C2', 'observed_expected_ratio', 'EDAM:data_0951', 2)
    _virtual_tester(message, 'has_chi_square_with', 'C3', 'chi_square', 'EDAM:data_0951', 2)


@pytest.mark.skip(reason="redundant if the test_clinical_overlay_example() passes and test_ARAX_overlay passes")
def test_clinical_overlay_example2():
    """
    Gives an example of overlaying (and filtering) clinical attributes when there exist edges in the KG that COHD can decorate
    """
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(name=DOID:11830, id=n00)",
        "add_qnode(type=chemical_substance, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        # overlay a bunch of clinical info
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        # filter some stuff out for the fun of it
        "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=paired_concept_frequency, type=std, remove_connected_nodes=F)",
        "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=observed_expected_ratio, type=std, remove_connected_nodes=F)",
        "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=chi_square, type=std, remove_connected_nodes=F)",
        # return results
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 1)


@pytest.mark.skip(reason="redundant if test_one_hop_based_on_types_1() and test_ARAX_overlay() passes")
def test_two_hop_based_on_types_1():
    """
    Example DSL for a two hop question that is based on types
    """
    #doid_list = {"DOID:11830", "DOID:5612", "DOID:2411", "DOID:8501", "DOID:174"}
    doid_list = {"DOID:11830"}
    for doid in doid_list:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            f"add_qnode(name={doid}, id=n00, type=disease)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            #"expand(edge_id=e00, kp=BTE)",
            "expand(edge_id=e01, kp=ARAX/KG2)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C1)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C2)",
            "overlay(action=overlay_clinical_info, chi_square=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C3)",
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=false, store=true)",
        ]}}
        [response, message] = _do_arax_query(query)
        print(message.id)
        assert response.status == 'OK'
        _virtual_tester(message, 'has_paired_concept_frequency_with', 'C1', 'paired_concept_frequency', 'EDAM:data_0951', 1)
        _virtual_tester(message, 'has_observed_expected_ratio_with', 'C2', 'observed_expected_ratio', 'EDAM:data_0951', 1)
        _virtual_tester(message, 'has_chi_square_with', 'C3', 'chi_square', 'EDAM:data_0951', 1)
        assert len(message.results) > 1


@pytest.mark.slow
def test_one_hop_based_on_types_1():
    """
    Example DSL for a one hop question that is based on types
    """
    #doid_list = {"DOID:11830", "DOID:5612", "DOID:2411", "DOID:8501", "DOID:174"}
    doid_list = {"DOID:11830"}
    for doid in doid_list:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            f"add_qnode(name={doid}, id=n00, type=disease)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            "expand(edge_id=e00, kp=BTE)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=0.75, remove_connected_nodes=true, qnode_id=n01)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=false)",
        ]}}
        [response, message] = _do_arax_query(query)
        print(message.id)
        assert response.status == 'OK'
        assert len(message.results) > 1


@pytest.mark.skip(reason="Work in progress (and takes a very long time)")
def test_one_hop_kitchen_sink_BTE_1():
    """
    Example of throwing everything at a simple BTE query
    """
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:11830, id=n0, type=disease)",
        "add_qnode(type=chemical_substance, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e1)",
        #"expand(edge_id=e00, kp=ARAX/KG2)",
        "expand(edge_id=e1, kp=BTE)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        "overlay(action=predict_drug_treats_disease)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=limit_number_of_results, max_results=50)",
        "return(message=true, store=true)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(message.id)
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 1)


@pytest.mark.skip(reason="Work in progress (and takes a very long time)")
def test_one_hop_kitchen_sink_BTE_2():
    """
    Example of throwing everything at a simple BTE query, but with node types that aren't appropriate for some reasoning capabilities
    """
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:11830, id=n0, type=disease)",
        "add_qnode(type=gene, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e1)",
        #"expand(edge_id=e00, kp=ARAX/KG2)",
        "expand(edge_id=e1, kp=BTE)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        "overlay(action=predict_drug_treats_disease)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=limit_number_of_results, max_results=50)",
        "return(message=true, store=true)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(message.id)
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM:data_0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM:data_0951', 1)


# Not working yet
# def test_example_3_kg2():
#     query = {"previous_message_processing_plan": { "processing_actions": [
#             "create_message",
#             #"add_qnode(id=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
#             "add_qnode(curie=DOID:9406, id=n00)",  # hypopituitarism, original demo example
#             "add_qnode(id=n01, type=chemical_substance, is_set=true)",
#             "add_qnode(id=n02, type=protein)",
#             "add_qedge(id=e00, source_id=n00, target_id=n01)",
#             "add_qedge(id=e01, source_id=n01, target_id=n02)",
#             "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
#             "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
#             "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
#             "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=2, remove_connected_nodes=t, qnode_id=n01)",
#             "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
#             "return(message=true, store=false)"
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     #assert len(message.results) == ?
#     assert message.results[0].essence is not None
#     _virtual_tester(message, 'has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'EDAM:data_0951', 2)
#     _virtual_tester(message, 'has_normalized_google_distance_with', 'N1', 'normalized_google_distance', 'EDAM:data_2526', 2)


if __name__ == "__main__":
    pytest.main(['-v'])

