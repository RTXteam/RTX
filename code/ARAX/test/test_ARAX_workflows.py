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

def test_FET_example_1():
    # This a FET 3-top example: try to find the phenotypes of drugs connected to proteins connected to DOID:14330
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(curie=DOID:14330, id=n00, type=disease)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1, rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n01)",
        "add_qnode(type=chemical_substance, is_set=true, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=e01, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2, rel_edge_id=e01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n02)",
        "add_qnode(type=phenotypic_feature, id=n03)",
        "add_qedge(source_id=n02, target_id=n03, id=e02)",
        "expand(edge_id=e02, kp=ARAX/KG1)",
        "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3, rel_edge_id=e02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n03)",
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
        assert 0 <= float(edge.edge_attributes[0].value) < 0.001
        assert edge.edge_attributes[0].type == 'data:1669'
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
        assert edge.edge_attributes[0].type == 'data:1669'
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
        assert edge.edge_attributes[0].type == 'data:1669'
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
    FET_edges = [x for x in message.knowledge_graph.edges if x.relation.find("FET") != -1]
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
        assert edge.edge_attributes[0].type == 'data:1669'
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
    _virtual_tester(message, 'has_jaccard_index_with', 'J1', 'jaccard_index', 'data:1772', 2)

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
#     _virtual_tester(message, 'has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'data:0951', 2)
#     _virtual_tester(message, 'has_normalized_google_distance_with', 'N1', 'normalized_google_distance', 'data:2526', 2)


if __name__ == "__main__":
    pytest.main(['-v'])

