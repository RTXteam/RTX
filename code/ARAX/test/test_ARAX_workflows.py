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
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == attribute_name
        values.add(edge.attributes[0].value)
        assert edge.attributes[0].attribute_type_id == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_option_group_id():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:3312, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:indicated_for, option_group_key=a, id=e00)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, option_group_key=1, id=e01)",
            "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        ]}}
    [response, message] = _do_arax_query(query)
    for key, edge in message.query_graph.edges.items():
        if key == 'e01':
            assert edge.option_group_id == '1'
        elif key == 'e00':
            assert edge.option_group_id == 'a'

def test_exclude():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:3312, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, exclude=true, key=e01)",
            "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    for key, edge in message.query_graph.edges.items():
        if key == 'e01':
            assert edge.exclude
        if key == 'e00':
            assert not edge.exclude

@pytest.mark.slow
def test_example_2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:7551, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_keys=[n02])",
        "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=provided_by, value=Pharos)",
        # "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1, threshold=0)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None
    # _virtual_tester(message, 'biolink:probably_treats', 'P1', 'probability_treats', 'EDAM-DATA:0951', 2)
    _virtual_tester(message, 'biolink:has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM-DATA:1772', 2)


@pytest.mark.slow
def test_example_3():
    query = {"operations": {"actions": [
        "add_qnode(name=MONDO:0005301, key=n00)", # CM: change "DOID:9406" to "MONDO:0005301" because DOID:9406 has no matched OMOP id.
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
        "add_qnode(categories=biolink:Protein, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=1, remove_connected_nodes=t, qnode_keys=[n01])",
        "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_keys=[n02])",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    #assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert len(message.results) >= 60
    assert message.results[0].essence is not None
    _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'EDAM-DATA:0951', 2)
    _virtual_tester(message, 'biolink:occurs_together_in_literature_with', 'N1', 'normalized_google_distance', 'EDAM-DATA:2526', 2)


@pytest.mark.slow
def test_FET_example_1():
    # This a FET 3-top example: try to find the phenotypes of drugs connected to proteins connected to DOID:14330
    query = {"operations": {"actions": [
        "add_qnode(ids=DOID:12889, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=e01, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, rel_edge_key=e01)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n02])",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n03)",
        "add_qedge(subject=n02, object=n03, key=e02)",
        "expand(edge_key=e02, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n02, object_qnode_key=n03, virtual_relation_label=FET3, rel_edge_key=e02)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n03])",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    # FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation is not None and x.relation.find("FET") != -1]
    # FET_edge_labels = set([edge.relation for edge in FET_edges])
    # assert len(FET_edge_labels) == 3
    # for edge in FET_edges:
    #     assert hasattr(edge, 'attributes')
    #     assert edge.attributes
    #     edge_attributes_dict = {attr.original_attribute_name:attr.value for attr in edge.attributes}
    #     assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
    #     assert 0 <= float(edge.attributes[0].value) < 0.005
    #     assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
    #     #assert edge_attributes_dict['is_defined_by'] == 'ARAX'
    #     assert edge_attributes_dict['provided_by'] == 'ARAX'
    # FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    # assert len(FET_query_edges) == 3
    # query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    # assert len(query_node_keys) == 4
    # for key, query_edge in FET_query_edges.items():
    #     assert hasattr(query_edge, 'predicates')
    #     assert 'biolink:has_fisher_exact_test_p_value_with' in query_edge.predicates
    #     assert key == query_edge.relation
    #     assert query_edge.subject in query_node_keys
    #     assert query_edge.object in query_node_keys


@pytest.mark.slow
@pytest.mark.skip(reason="FW: This now runs increadibly slowly and uses a lot of ram after changing to RTX-KG2. Need to find a better drug with fewer connections")
def test_FET_example_2():
    # This a FET 4-top example: try to find the diseases connected to proteins connected to biological_process connected to protein connected to CHEMBL.COMPOUND:CHEMBL521
    query = {"operations": {"actions": [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL1472, categories=biolink:ChemicalEntity)",
        "add_qnode(key=n01, is_set=true, categories=biolink:Protein)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:BiologicalProcess, is_set=true, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=e01, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_keys=[n02])",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n03)",
        "add_qedge(subject=n02, object=n03, key=e02)",
        "expand(edge_key=e02, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n02, object_qnode_key=n03, virtual_relation_label=FET3)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_keys=[n03])",
        "add_qnode(categories=biolink:Disease, key=n04)",
        "add_qedge(subject=n03, object=n04, key=e03)",
        "expand(edge_key=e03, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n03, object_qnode_key=n04, virtual_relation_label=FET4)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_keys=[n04])",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation is not None and x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 4
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        edge_attributes_dict = {attr.original_attribute_name:attr.value for attr in edge.attributes}
        assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
        assert 0 <= float(edge.attributes[0].value) < 0.01
        assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
        #assert edge_attributes_dict['is_defined_by'] == 'ARAX'
        assert edge_attributes_dict['provided_by'] == 'ARAX'
    FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    assert len(FET_query_edges) == 4
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 5
    for key, query_edge in FET_query_edges.items():
        assert hasattr(query_edge, 'predicates')
        assert 'biolink:has_fisher_exact_test_p_value_with' in query_edge.predicates
        assert key == query_edge.relation
        assert query_edge.subject in query_node_keys
        assert query_edge.object in query_node_keys


@pytest.mark.skip(reason="need issue#846 to be solved")
def test_FET_example_3():
    # This a FET 6-top example: try to find the drugs connected to proteins connected to pathways connected to proteins connected to diseases connected to phenotypes of DOID:14330
    query = {"operations": {"actions": [
        "add_qnode(ids=DOID:14330, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:PhenotypicFeature, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:has_phenotype)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:Disease, is_set=true, key=n02)",
        "add_qedge(subject=n01,object=n02,key=e01,predicates=biolink:has_phenotype)",
        "expand(edge_key=e01, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, rel_edge_key=e01)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n02])",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n03)",
        "add_qedge(subject=n02, object=n03, key=e02, predicates=biolink:gene_mutations_contribute_to)",
        "expand(edge_key=e02, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n02, object_qnode_key=n03, virtual_relation_label=FET3, rel_edge_key=e02)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n03])",
        "add_qnode(categories=biolink:Pathway, is_set=true, key=n04)",
        "add_qedge(subject=n03, object=n04, key=e03, predicates=biolink:participates_in)",
        "expand(edge_key=e03, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n03, object_qnode_key=n04, virtual_relation_label=FET4, rel_edge_key=e03)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n04])",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n05)",
        "add_qedge(subject=n04, object=n05, key=e04, predicates=biolink:participates_in)",
        "expand(edge_key=e04, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n04, object_qnode_key=n05, virtual_relation_label=FET5, rel_edge_key=e04)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n05])",
        "add_qnode(categories=biolink:ChemicalEntity, key=n06)",
        "add_qedge(subject=n05, object=n06, key=e05, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=e05, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n05, object_qnode_key=n06, virtual_relation_label=FET6, rel_edge_key=e05)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n06])",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation.find("FET") != -1]
    FET_edge_labels = set([edge.relation for edge in FET_edges])
    assert len(FET_edge_labels) == 6
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        edge_attributes_dict = {attr.original_attribute_name:attr.value for attr in edge.attributes}
        assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
        assert 0 <= float(edge.attributes[0].value) < 0.001
        assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
        #assert edge_attributes_dict['is_defined_by'] == 'ARAX'
        assert edge_attributes_dict['provided_by'] == 'ARAX'
    FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    assert len(FET_query_edges) == 4
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 5
    for key, query_edge in FET_query_edges.items():
        assert hasattr(query_edge, 'predicates')
        assert 'biolink:has_fisher_exact_test_p_value_with' in query_edge.predicates
        assert key == query_edge.relation
        assert query_edge.subject in query_node_keys
        assert query_edge.object in query_node_keys


@pytest.mark.slow
def test_FET_example_4():
    # This a FET 2-top example collecting nodes and edges from both KG1 and KG2: try to find the disease connected to proteins connected to DOID:14330
    # FW: Now only does KG2 since we are disabling KG1
    query = {"operations": {"actions": [
        "add_qnode(ids=DOID:10718, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:PhenotypicFeature, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, virtual_relation_label=FET1, object_qnode_key=n01,rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute=fisher_exact_test_p-value,direction=above,threshold=0.001,remove_connected_nodes=t,qnode_keys=[n01])",
        "add_qnode(categories=biolink:Disease, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=e01, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, virtual_relation_label=FET2, object_qnode_key=n02,rel_edge_id=e01)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    # FET_edges = [x for x in message.knowledge_graph.edges.values() if x.relation and x.relation.find("FET") != -1]
    # FET_edge_labels = set([edge.relation for edge in FET_edges])
    # assert len(FET_edge_labels) == 2
    # for edge in FET_edges:
    #     assert hasattr(edge, 'attributes')
    #     assert edge.attributes
    #     edge_attributes_dict = {attr.original_attribute_name:attr.value for attr in edge.attributes}
    #     assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
    #     if edge.relation == "FET1":
    #         assert 0 <= float(edge.attributes[0].value) < 0.001
    #     else:
    #         assert float(edge.attributes[0].value) >= 0
    #     assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
    #     #assert edge_attributes_dict['is_defined_by'] == 'ARAX'
    #     assert edge_attributes_dict['provided_by'] == 'ARAX'
    # FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    # assert len(FET_query_edges) == 2
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 2
    # for key, query_edge in FET_query_edges.items():
    #     assert hasattr(query_edge, 'predicates')
    #     assert 'biolink:has_fisher_exact_test_p_value_with' in query_edge.predicates
    #     assert key == query_edge.relation
    #     assert query_edge.subject in query_node_keys
    #     assert query_edge.object in query_node_keys

# @pytest.mark.slow
# def test_FET_ranking_1():
#     query = {"operations": { "actions": [
#             "create_message",
#             "add_qnode(key=n00,ids=UniProtKB:P14136,categories=biolink:Protein)",
#             "add_qnode(categories=biolink:BiologicalProcess, key=n01)",
#             "add_qedge(subject=n00, object=n01, key=e00)",
#             "expand(edge_key=e00,kp=infores:rtx-kg2)",
#             "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET)",
#             "resultify()",
#             "return(message=true, store=false)",
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     ranks = [result.score for result in message.results]
#     assert min(ranks) != max(ranks)

@pytest.mark.slow
def test_example_2_kg2():
    query = {"operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:molecularly_interacts_with)",
            "expand(edge_key=[e00,e01], infores:rtx-kg2)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",  # seems to work just fine
            "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=jaccard_index, direction=below, threshold=.008, remove_connected_nodes=t, qnode_keys=[n02])",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 15
    assert message.results[0].essence is not None
    _virtual_tester(response.envelope.message, 'biolink:has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM-DATA:1772', 2)


@pytest.mark.slow
def test_clinical_overlay_example1():
    """
    Gives an example of a KG that does not have edges that COHD can decorate, but does have pairs of nodes that COHD
    could decorate (eg here is drug and chemical_substance), so add the info in as a virtual edge.
    """
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:11830, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:molecularly_interacts_with)",
        "expand(edge_key=[e00,e01], infores:rtx-kg2)",
        # overlay a bunch of clinical info
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C1)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C2)",
        "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C3)",
        # filter some stuff out for the fun of it
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=paired_concept_frequency, direction=above, threshold=0.5, remove_connected_nodes=true, qnode_keys=[n02])",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=observed_expected_ratio, direction=above, threshold=1, remove_connected_nodes=true, qnode_keys=[n02])",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=chi_square, direction=below, threshold=0.05, remove_connected_nodes=true, qnode_keys=[n02])",
        # return results
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    _virtual_tester(message, 'biolink:has_paired_concept_frequency_with', 'C1', 'paired_concept_frequency', 'EDAM-DATA:0951', 2)
    _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C2', 'observed_expected_ratio', 'EDAM-DATA:0951', 2)
    _virtual_tester(message, 'biolink:has_chi_square_with', 'C3', 'chi_square', 'EDAM-DATA:0951', 2)


@pytest.mark.skip(reason="redundant if the test_clinical_overlay_example() passes and test_ARAX_overlay passes")
def test_clinical_overlay_example2():
    """
    Gives an example of overlaying (and filtering) clinical attributes when there exist edges in the KG that COHD can decorate
    """
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:11830, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, infores:rtx-kg2)",
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
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM-DATA:0951', 1)


@pytest.mark.skip(reason="redundant if test_one_hop_based_on_types_1() and test_ARAX_overlay() passes")
def test_two_hop_based_on_types_1():
    """
    Example DSL for a two hop question that is based on types
    """
    #doid_list = {"DOID:11830", "DOID:5612", "DOID:2411", "DOID:8501", "DOID:174"}
    doid_list = {"DOID:11830"}
    for doid in doid_list:
        query = {"operations": {"actions": [
            "create_message",
            f"add_qnode(name={doid}, key=n00, categories=biolink:Disease)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_key=e00, infores:rtx-kg2)",
            #"expand(edge_key=e00, kp=infores:biothings-explorer)",
            "expand(edge_key=e01, infores:rtx-kg2)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C1)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C2)",
            "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C3)",
            # "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=false, store=true)",
        ]}}
        [response, message] = _do_arax_query(query)
        print(message.id)
        assert response.status == 'OK'
        _virtual_tester(message, 'biolink:has_paired_concept_frequency_with', 'C1', 'paired_concept_frequency', 'EDAM-DATA:0951', 1)
        _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C2', 'observed_expected_ratio', 'EDAM-DATA:0951', 1)
        _virtual_tester(message, 'biolink:has_chi_square_with', 'C3', 'chi_square', 'EDAM-DATA:0951', 1)
        assert len(message.results) > 1


@pytest.mark.external
@pytest.mark.slow
def test_one_hop_based_on_types_1():
    """
    Example DSL for a one hop question that is based on types
    """
    #doid_list = {"DOID:11830", "DOID:5612", "DOID:2411", "DOID:8501", "DOID:174"}
    doid_list = {"DOID:11830"}
    for doid in doid_list:
        query = {"operations": {"actions": [
            "create_message",
            f"add_qnode(ids={doid}, key=n00, categories=biolink:Disease)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, infores:rtx-kg2)",
            "expand(edge_key=e00, kp=infores:biothings-explorer)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            # "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=probability_treats, direction=below, threshold=0.75, remove_connected_nodes=true, qnode_keys=[n01])",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=false)",
        ]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) > 1


@pytest.mark.skip(reason="Work in progress (and takes a very long time)")
def test_one_hop_kitchen_sink_BTE_1():
    """
    Example of throwing everything at a simple BTE query
    """
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(curie=DOID:11830, key=n0, categories=biolink:Disease)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e1)",
        #"expand(edge_key=e00, infores:rtx-kg2)",
        "expand(edge_key=e1, kp=infores:biothings-explorer)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        # "overlay(action=predict_drug_treats_disease)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=limit_number_of_results, max_results=50)",
        "return(message=true, store=true)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(message.id)
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM-DATA:0951', 1)


@pytest.mark.skip(reason="Work in progress (and takes a very long time)")
def test_one_hop_kitchen_sink_BTE_2():
    """
    Example of throwing everything at a simple BTE query, but with node types that aren't appropriate for some reasoning capabilities
    """
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(curie=DOID:11830, key=n0, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e1)",
        #"expand(edge_key=e00, infores:rtx-kg2)",
        "expand(edge_key=e1, kp=infores:biothings-explorer)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        # "overlay(action=predict_drug_treats_disease)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=limit_number_of_results, max_results=50)",
        "return(message=true, store=true)",
    ]}}
    [response, message] = _do_arax_query(query)
    print(message.id)
    assert response.status == 'OK'
    _attribute_tester(message, 'paired_concept_frequency', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'observed_expected_ratio', 'EDAM-DATA:0951', 1)
    _attribute_tester(message, 'chi_square', 'EDAM-DATA:0951', 1)

def test_FET_ranking_2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(key=n00,ids=[UniProtKB:P14136,UniProtKB:P35579],is_set=true,categories=biolink:Protein)",
        "add_qnode(categories=biolink:BiologicalProcess, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00,kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    fet_ranking_value = {}
    for result in message.results:
        for key, edge_bindings in result.analyses[0].edge_bindings.items():
            if key.startswith('FET'):
                for edge in edge_bindings:
                    for attribute in message.knowledge_graph.edges[edge.id].attributes:
                        if attribute.original_attribute_name == "fisher_exact_test_p-value":
                            if str(result.score) in fet_ranking_value:
                                fet_ranking_value[str(result.score)].append(float(attribute.value))
                            else:
                                fet_ranking_value[str(result.score)] = [float(attribute.value)]

    for fet_val, conf_list in fet_ranking_value.items():
        if len(conf_list) > 1:
            for diff in [abs(x - y) for i,x in enumerate(conf_list) for j,y in enumerate(conf_list) if i < j]:
                assert diff == 0


@pytest.mark.external
def test_genetics_kp_ranking():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=type 2 diabetes mellitus, categories=biolink:Disease, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0, predicates=biolink:condition_associated_with_gene)",
        "expand(edge_key=e0,kp=infores:genetics-data-provider)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    gen_kp_ranking_value = {}
    for result in message.results:
        for key, edge_bindings in result.edge_bindings.items():
            for edge in edge_bindings:
                if edge.id.startswith('infores:genetics-data-provider'):
                    if message.knowledge_graph.edges[edge.id].attributes is not None:
                        for attribute in message.knowledge_graph.edges[edge.id].attributes:
                            if attribute.original_attribute_name == "pValue":
                                if str(result.score) in gen_kp_ranking_value:
                                    gen_kp_ranking_value[str(result.score)].append(float(attribute.value))
                                else:
                                    gen_kp_ranking_value[str(result.score)] = [float(attribute.value)]
    assert len(gen_kp_ranking_value) > 0

@pytest.mark.slow
def test_ranker_float_error_ex1():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, key=n0, categories=biolink:ChemicalEntity)",
        "add_qnode(categories=biolink:DiseaseOrPhenotypicFeature, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand()",
        "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
        "overlay(action=fisher_exact_test,subject_qnode_key=n0,virtual_relation_label=F1,object_qnode_key=n1)",
        "overlay(action=overlay_clinical_info,COHD_method=paired_concept_frequency,virtual_relation_label=C1,subject_qnode_key=n0,object_qnode_key=n1)",
        # "overlay(action=predict_drug_treats_disease,virtual_relation_label=P1,subject_qnode_key=n0,object_qnode_key=n1,threshold=0.8,slow_mode=false)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

@pytest.mark.external
def test_ranker_float_error_ex2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=MONDO:0005301, key=n0)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(kp=infores:cohd)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    result_scores = [x.score for x in message.results]
    assert max(result_scores) == 1

@pytest.mark.external
def test_cmap_ranking():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(key=n00,categories=biolink:Gene,ids=HGNC:321)",
        "add_qnode(categories=biolink:ChemicalEntity)",
        "add_qedge(subject=n00,object=n01)",
        "expand(kp=infores:molepro)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=500)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    result_scores = {x.score for x in message.results}
    assert len(result_scores) > 1

@pytest.mark.slow
def test_ranker_float_error_ex3():
    query={"message": {
            "query_graph": {
              "edges": {
                "e00": {
                  "object": "n01",
                  "subject": "n00"
                },
                "e01": {
                  "object": "n02",
                  "subject": "n01"
                }
              },
              "nodes": {
                "n00": {
                  "categories": [
                    "biolink:Disease"
                  ],
                  "ids": [
                    "DOID:14330"
                  ]
                },
                "n01": {
                  "categories": [
                    "biolink:NamedThing"
                  ]
                },
                "n02": {
                  "categories": [
                    "biolink:Disease"
                  ],
                  "ids": [
                    "DOID:8778"
                  ]
                }
              }
            }
          }
        }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'


@pytest.mark.external
def test_issue_1848():
    query = {
            "workflow": [
                {
                    "id": "fill",
                    "parameters": { "allowlist": ["infores:cohd"],
                        "qedge_keys": [
                            "e0"
                        ]
                    }
                },
                {
                    "id": "overlay_compute_ngd",
                    "parameters": {
                        "virtual_relation_label": "N1",
                        "qnode_keys": [
                            "n0",
                            "n1"
                        ]
                    }
                },
                {
                    "id": "bind"
                },
                {
                    "id": "score"
                },
                {
                    "id": "filter_results_top_n",
                    "parameters": {
                        "max_results": 3
                    }
                },
                {
                    "id": "fill",
                    "parameters": { "allowlist": ["infores:rtx-kg2"],
                        "qedge_keys": [
                            "e1",
                            "e2",
                            "e3",
                            "e4"
                        ]
                    }
                },
                {
                    "id": "bind"
                },
                {
                    "id": "score"
                }
            ],
            "message": {
                "query_graph": {
                    "edges": {
                        "e0": {
                            "subject": "n0",
                            "object": "n1",
                            "predicates": [
                                "biolink:has_real_world_evidence_of_association_with"
                            ]
                        },
                        "e1": {
                            "subject": "n1",
                            "object": "n2",
                            "predicates": [
                                "biolink:increases_activity_of"
                            ]
                        },
                        "e2": {
                            "subject": "n3",
                            "object": "n2",
                            "predicates": [
                                "biolink:increases_activity_of"
                            ]
                        },
                        "e3": {
                            "subject": "n1",
                            "object": "n2",
                            "predicates": [
                                "biolink:decreases_activity_of"
                            ],
                            "option_group_id": "decr"
                        },
                        "e4": {
                            "subject": "n3",
                            "object": "n2",
                            "predicates": [
                                "biolink:decreases_activity_of"
                            ],
                            "option_group_id": "decr"
                        }
                    },
                    "nodes": {
                        "n0": {
                            "ids": [
                                "MONDO:0009061"
                            ],
                            "name": "MONDO:0009061"
                        },
                        "n1": {
                            "categories": [
                                "biolink:ChemicalEntity"
                            ]
                        },
                        "n2": {
                            "categories": [
                                "biolink:Gene",
                                "biolink:Protein"
                            ]
                        },
                        "n3": {
                            "categories": [
                                "biolink:ChemicalEntity"
                            ]
                        }
                    }
                }
            }
        }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

# Not working yet
# def test_example_3_kg2():
#     query = {"operations": { "actions": [
#             "create_message",
#             #"add_qnode(key=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
#             "add_qnode(curie=DOID:9406, key=n00)",  # hypopituitarism, original demo example
#             "add_qnode(key=n01, categories=chemical_substance, is_set=true)",
#             "add_qnode(key=n02, categories=protein)",
#             "add_qedge(key=e00, subject=n00, object=n01)",
#             "add_qedge(key=e01, subject=n01, object=n02)",
#             "expand(edge_key=[e00,e01], infores:rtx-kg2)",
#             "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
#             "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
#             "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=2, remove_connected_nodes=t, qnode_keys=[n01])",
#             "filter_kg(action=remove_orphaned_nodes, node_category=protein)",
#             "return(message=true, store=false)"
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     #assert len(message.results) == ?
#     assert message.results[0].essence is not None
#     _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'EDAM-DATA:0951', 2)
#     _virtual_tester(message, 'biolink:occurs_together_in_literature_with', 'N1', 'normalized_google_distance', 'EDAM-DATA:2526', 2)

@pytest.mark.slow
def test_example_3_issue_679():
    query = {"operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:9406, key=n00)",
            "add_qnode(categories=[biolink:ChemicalEntity], is_set=true, key=n01)",
            "add_qnode(categories=[biolink:Protein], key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand()",
            "overlay(action=overlay_clinical_info, COHD_method=observed_expected_ratio, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute=observed_expected_ratio,direction=below,threshold=3,remove_connected_nodes=true,qnode_keys=n01)",
            "filter_kg(action=remove_orphaned_nodes,node_category=biolink:Protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute=ngd,direction=above,threshold=0.85,remove_connected_nodes=true,qnode_keys=n02)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.results[0].essence is not None


if __name__ == "__main__":
    pytest.main(['-v'])
