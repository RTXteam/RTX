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


@pytest.mark.broken 
def test_jaccard():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:14221, key=n00)",
        "add_qnode(categories=biolink:Gene, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:interacts_with)",
        "expand(edge_key=[e00,e01], kp=infores:retriever)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_jaccard_index_with' in edge_predicates_in_kg
    jaccard_edges = []
    for edge in message.knowledge_graph.edges.values():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        add_edge = False
        for attribute in edge.attributes:
            if attribute.original_attribute_name == "virtual_relation_label":
                if attribute.value == "J1":
                    add_edge = True
        if add_edge:
            jaccard_edges.append(edge)
    assert len(jaccard_edges) > 0
    for edge in jaccard_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == 'jaccard_index'
        assert edge.attributes[0].value >= 0


def test_add_node_pmids():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=MONDO:0018077, key=n00)",
        "add_qnode(ids=CHEBI:17076, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
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
            if attr.original_attribute_name == 'pubmed_ids':
                nodes_with_pmids.append(node)
    assert len(nodes_with_pmids) > 0
    # check types
    for node in nodes_with_pmids:
        for attr in node.attributes:
            if attr.original_attribute_name == "pubmed_ids":
                assert attr.attribute_type_id == 'EDAM-DATA:0971'
                assert attr.value.__class__ == list


def test_compute_ngd_virtual():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:384, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "overlay(action=compute_ngd, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=N1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:occurs_together_in_literature_with' in edge_predicates_in_kg
    ngd_edges = []
    for edge in message.knowledge_graph.edges.values():
        add_edge = False
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        for attribute in edge.attributes:
            if attribute.original_attribute_name == "virtual_relation_label":
                if attribute.value == "N1":
                    add_edge = True
        if add_edge:
            ngd_edges.append(edge)
    assert len(ngd_edges) > 0
    for edge in ngd_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        attribute_names = {attribute.original_attribute_name: attribute.value for attribute in edge.attributes}
        if 'publications' in attribute_names:
            assert len(attribute_names["publications"]) <= 30
        assert edge.attributes[0].original_attribute_name == 'normalized_google_distance'
        assert float(edge.attributes[0].value) >= 0


def test_compute_ngd_attribute():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:384, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "overlay(action=compute_ngd)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    ngd_edges = []
    for edge in message.knowledge_graph.edges.values():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        if hasattr(edge, 'attributes'):
            for attr in edge.attributes:
                if attr.original_attribute_name == 'normalized_google_distance':
                    ngd_edges.append(edge)
                    assert float(attr.value) >= 0
                    assert attr.attribute_type_id == 'EDAM-DATA:2526'
    assert len(ngd_edges) > 0
    for edge in ngd_edges:
        attribute_names = {attribute.original_attribute_name: attribute.value for attribute in edge.attributes}
        if "publications" in attribute_names:
            assert len(attribute_names["publications"]) <= 30

def test_FET_ex1():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=DOID:12889, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Gene, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01,key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:interacts_with)",
        "expand(edge_key=e01, kp=infores:retriever)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, filter_type=cutoff, value=0.05)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = []
    FET_edge_labels = set()
    for edge in message.knowledge_graph.edges.values():
        relation_name = None
        add_edge = False
        for attribute in edge.attributes:
            if attribute.original_attribute_name == "virtual_relation_label":
                if attribute.value is not None and attribute.value.find("FET") != -1:
                    add_edge = True
                    FET_edge_labels.add(attribute.value)
                    relation_name = attribute.value
        if add_edge:
            FET_edges.append((edge, relation_name))
    assert len(FET_edges) > 0
    assert len(FET_edge_labels) == 2
    for edge_tuple in FET_edges:
        edge, relation_name = edge_tuple
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
        assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        if relation_name == 'FET1':
            assert 0 <= float(edge.attributes[0].value) < 0.005
        else:
            assert 0 <= float(edge.attributes[0].value) < 0.05
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


@pytest.mark.slow
def test_FET_ex2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=DOID:12889, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, virtual_relation_label=FET, object_qnode_key=n01, rel_edge_key=e00, top_n=20)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = []
    FET_edge_labels = set()
    for edge in message.knowledge_graph.edges.values():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        relation_name = None
        add_edge = False
        for attribute in edge.attributes:
            if attribute.original_attribute_name == "virtual_relation_label":
                if attribute.value is not None and attribute.value.find("FET") != -1:
                    add_edge = True
                    FET_edge_labels.add(attribute.value)
                    relation_name = attribute.value
        if add_edge:
            FET_edges.append((edge, relation_name))
    assert len(FET_edges) >= 2
    assert len(FET_edge_labels) == 1
    for edge_tuple in FET_edges:
        edge, relation_name = edge_tuple
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == 'fisher_exact_test_p-value'
        assert edge.attributes[0].attribute_type_id == 'EDAM-DATA:1669'
    # FET_query_edges = {key:edge for key, edge in message.query_graph.edges.items() if key.find("FET") != -1}
    # assert len(FET_query_edges) == 1
    query_node_keys = [key for key, node in message.query_graph.nodes.items()]
    assert len(query_node_keys) == 2
    # for key, query_edge in FET_query_edges.items():
    #     assert hasattr(query_edge, 'predicates')
    #     assert 'biolink:has_fisher_exact_test_p_value_with' in query_edge.predicates
    #     assert key == query_edge.relation
    #     assert query_edge.subject in query_node_keys
    #     assert query_edge.object in query_node_keys


@pytest.mark.slow
def test_missing_ngd_pmids():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(ids=UniProtKB:P52788, key=n0)",
        "add_qnode(categories=[biolink:Protein,biolink:Gene], key=n1, is_set=true)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "add_qnode(categories=[biolink:ChemicalEntity,biolink:Drug], key=n2)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(kp=infores:retriever)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
        "overlay(action=compute_ngd, virtual_relation_label=N2, subject_qnode_key=n1, object_qnode_key=n2)",
        "overlay(action=compute_ngd, virtual_relation_label=N3, subject_qnode_key=n0, object_qnode_key=n2)",
        "overlay(action=compute_jaccard, start_node_key=n0, intermediate_node_key=n1, end_node_key=n2, virtual_relation_label=J1)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=30)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    ngd_publications = {}
    for edge_key, edge in message.knowledge_graph.edges.items():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        if edge.attributes is not None:
            for attribute in edge.attributes:
                if attribute.original_attribute_name == 'normalized_google_distance':
                    if edge_key not in ngd_publications:
                        ngd_publications[edge_key] = {}
                    ngd_publications[edge_key]['ngd'] = attribute.value
                elif attribute.original_attribute_name == 'publications':
                    if edge_key not in ngd_publications:
                        ngd_publications[edge_key] = {}
                    ngd_publications[edge_key]['pubs'] = attribute.value

    for edge_dict in ngd_publications.values():
        if 'ngd' in edge_dict and 'pubs' in edge_dict:
            if edge_dict['pubs'] == []:
                assert edge_dict['ngd'] == 'inf'

@pytest.mark.slow
def test_jaccard_not_above_1():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(key=N0,ids=chembl.compound:CHEMBL787)",
        "add_qnode(key=N1,categories=biolink:Protein)",
        "add_qedge(key=E0,subject=N0,object=N1,predicates=biolink:physically_interacts_with)",
        "add_qnode(key=N2,categories=biolink:ChemicalEntity)",
        "add_qedge(key=E2,subject=N1,object=N2)",
        "expand(kp=infores:retriever)",
        "overlay(action=compute_ngd,default_value=inf,virtual_relation_label=V1,subject_qnode_key=N0,object_qnode_key=N1)",
        "overlay(action=compute_ngd,default_value=inf,virtual_relation_label=V2,subject_qnode_key=N1,object_qnode_key=N2)",
        "overlay(action=compute_ngd,default_value=inf,virtual_relation_label=V3,subject_qnode_key=N0,object_qnode_key=N2)",
        "overlay(action=compute_jaccard,start_node_key=N0,intermediate_node_key=N1,end_node_key=N2,virtual_relation_label=VJ)",
        "resultify()",
        #"filter_results(action=limit_number_of_results,max_results=100,prune_kg=true)",
        "return(message=true, store=false)",
        ]}}
    [response, message] = _do_arax_query(query)
    print(response.show())
    assert response.status == 'OK'
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_jaccard_index_with' in edge_predicates_in_kg
    jaccard_edges = []
    for edge in message.knowledge_graph.edges.values():
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        add_edge = False
        for attribute in edge.attributes:
            if attribute.original_attribute_name == "virtual_relation_label":
                if attribute.value == "VJ":
                    add_edge = True
        if add_edge:
            jaccard_edges.append(edge)
    assert len(jaccard_edges) > 0
    for edge in jaccard_edges:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == 'jaccard_index'
        assert edge.attributes[0].value >= 0
        assert edge.attributes[0].value <= 1

@pytest.mark.slow
def test_ngd_sqlite_syntax_error():
    query = {"message":{"query_graph":{
          "edges": {
            "e00": {
              "object": "n01",
              "subject": "n00"
            }
          },
          "nodes": {
            "n00": {
              "ids": [
                "CHEBI:16680"
              ],
              "is_set": False
            },
            "n01": {
              "categories": [
                "biolink:Pathway",
                "biolink:BiologicalProcess",
                "biolink:MolecularActivity",
                "biolink:CellularComponent",
                "biolink:InformationContentEntity",
                "biolink:NamedThing"
              ],
              "is_set": False
            }
          }
        }
    }}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'


if __name__ == "__main__":
    pytest.main(['-v'])
