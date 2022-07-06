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
from ARAX_filter_kg import ARAXFilterKG
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


def _do_arax_query(query: dict, print_response: bool=True) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK' and print_response:
        print(response.show(level=response.DEBUG))
    #return [response, araxq.message]
    return [response, response.envelope.message]

def test_command_definitions():
    fkg = ARAXFilterKG()
    assert fkg.allowable_actions == set(fkg.command_definitions.keys())

def test_warnings():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:8741, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=infores:rtx-kg2)",
            "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=asdfghjkl, direction=below, threshold=.2)",
            "filter_kg(action=remove_edges_by_discrete_attribute, edge_attribute=asdfghjkl, value=qwertyuiop)",
            "filter_kg(action=remove_edges_by_std_dev, edge_attribute=asdfghjkl, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)",
            "filter_kg(action=remove_edges_by_top_n, edge_attribute=asdfghjkl, remove_connected_nodes=f, n=50, top=f, direction=above)",
            "filter_kg(action=remove_edges_by_percentile, edge_attribute=asdfghjkl, remove_connected_nodes=f, threshold=25, top=f, direction=above)",
            "overlay(action=compute_ngd, virtual_relation_label=N2, subject_qnode_key=n00, object_qnode_key=n01)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20

def test_error():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:treats)",
            "expand(edge_key=e00, kp=infores:rtx-kg2)",
            "filter_kg(action=remove_edges_by_predicate, edge_predicate=biolink:treats, remove_connected_nodes=t, qedge_keys=[e00])",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query, False)
    assert response.status == 'ERROR'
    assert response.error_code == "RemovedQueryNode"

def test_edge_key_removal():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:11086, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qnode(categories=biolink:Disease, key=n02)",
            "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:treats)",
            "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:treats)",
            "expand(kp=infores:rtx-kg2)",
            "filter_kg(action=remove_edges_by_predicate, edge_predicate=biolink:treats, remove_connected_nodes=f, qedge_keys=[e01])",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query, False)
    assert response.status == 'OK'
    edge_key_set = set()
    for edge in message.knowledge_graph.edges.values():
        edge_key_set = edge_key_set.union(edge.qedge_keys)
    assert 'e01' not in edge_key_set

def test_default_std_dev():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    all_vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    comp_val = np.mean(all_vals) + np.std(all_vals)
    comp_len = len([x for x in all_vals if x > comp_val])
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_std_dev, edge_attribute=jaccard_index, remove_connected_nodes=f)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    assert len(vals) == comp_len
    assert np.min(vals) > comp_val

def test_std_dev():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    all_vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    assert len(all_vals) > 0
    comp_val = np.mean(all_vals) - 0.25*np.std(all_vals)
    comp_len = len([x for x in all_vals if x < comp_val])
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_std_dev, edge_attribute=jaccard_index, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    assert len(vals) == comp_len
    assert len([x for x in vals if x == 1]) == 0
    assert np.max(vals) < comp_val

def test_default_top_n():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    all_vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    all_vals.sort()
    all_vals.reverse()
    sorted_vals = all_vals[:50]
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:0060680, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J2)",
        "filter_kg(action=remove_edges_by_top_n, edge_attribute=jaccard_index, remove_connected_nodes=f)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    vals = [float(y.value) for x in message.knowledge_graph.edges.values() if x.attributes is not None for y in x.attributes if y.original_attribute_name == 'jaccard_index']
    assert len(vals) == 50
    vals.sort()
    vals.reverse()
    assert vals == sorted_vals

def test_remove_property_known_attributes():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=CHEBI:17754, categories=biolink:ChemicalEntity, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n1, object=n0, key=e0,predicates=biolink:negatively_regulates_entity_to_entity)",
        "expand(kp=infores:rtx-kg2)",
        "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=provided_by,value=SEMMEDDB:,remove_connected_nodes=false)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

@pytest.mark.slow
def  test_remove_attribute_known_attributes():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:14330, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_keys=[n02])",
        #"filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=provided_by, value=Pharos)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

def test_provided_by_filter():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=CHEBI:17754, categories=biolink:ChemicalEntity, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n1, object=n0, key=e0,predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=infores:rtx-kg2)",
        "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=biolink:knowledge_source,value=infores:semmeddb,remove_connected_nodes=false)",
        # The below lines are now outdated ways of doing it, but including for now to prevent error until new code is rolled out to KG2 API
        # "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=biolink:original_source,value=infores:semmeddb,remove_connected_nodes=false)",
        # "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=provided_by,value=infores:semmeddb,remove_connected_nodes=false)",
        "resultify()",
        #"filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    count1 = len(message.results)
    assert count1 == 0
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=CHEBI:17754, categories=biolink:ChemicalEntity, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n1, object=n0, key=e0,predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=infores:rtx-kg2)",
        #"filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=biolink:original_source,value=infores:semmeddb,remove_connected_nodes=false)",
        "resultify()",
        #"filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    count2 = len(message.results)
    assert count2 > count1

@pytest.mark.external
@pytest.mark.slow
def test_stats_error_int_threshold():
    query = {"operations": {"actions": [
        "create_message",
        # Multiple sclerosis -> chemical substance with "related_to" from Clinical Risk KP
        "add_qnode(ids=MONDO:0005301, key=n0)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0, predicates=biolink:related_to)",
        "expand(kp=infores:biothings-multiomics-clinical-risk,edge_key=e0)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=10)",
        # Then look for proteins that are shared with these chemical substances and MS
        "add_qnode(categories=biolink:Protein, key=n2, is_set=True)",
        "add_qedge(subject=n0, object=n2, key=e1)",
        "add_qedge(subject=n1, object=n2, key=e2)",
        "expand(edge_key=[e1,e2])",
        # Rank drugs by Jaccard Index
        "overlay(action=compute_jaccard,start_node_key=n0,intermediate_node_key=n2,end_node_key=n1,virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_top_n,edge_attribute=jaccard_index, n=10,remove_connected_nodes=true,qnode_keys=[n2])",
        "overlay(action=compute_ngd, virtual_relation_label=N2, subject_qnode_key=n1, object_qnode_key=n2)",
        "overlay(action=compute_ngd, virtual_relation_label=N3, subject_qnode_key=n0, object_qnode_key=n2)",
        "resultify()",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

def test_tuple_bug():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(key=n00,ids=DRUGBANK:DB00150,categories=biolink:ChemicalEntity)",
        "add_qnode(key=n01,categories=biolink:Protein)",
        "add_qedge(key=e00,subject=n00,object=n01)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "overlay(action=fisher_exact_test,subject_qnode_key=n00,virtual_relation_label=F0,object_qnode_key=n01)",
        "filter_kg(action=remove_edges_by_top_n,edge_attribute=fisher_exact_test_p-value,direction=below,n=10,remove_connected_nodes=true,qnode_keys=[n01])",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=100)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'

if __name__ == "__main__":
    pytest.main(['-v'])
