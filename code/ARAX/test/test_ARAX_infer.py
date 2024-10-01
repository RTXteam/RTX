#!/usr/bin/env python3

# Intended to test ARAX infer

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
        assert 'primary_knowledge_source' in [attribute.attribute_type_id for attribute in edge.attributes]
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == attribute_name
        values.add(edge.attributes[0].value)
        assert edge.attributes[0].attribute_type_id == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_xdtd_infer_castleman_disease_1():
    query = {"operations": {"actions": [
            "create_message",
            "infer(action=drug_treatment_graph_expansion,disease_curie=MONDO:0015564)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 1
    assert len(message.results) > 0

def test_xdtd_infer_castleman_disease_2():
    query = {"operations": {"actions": [
            "create_message",
            "infer(action=drug_treatment_graph_expansion,disease_curie=MONDO:0015564,n_drugs=2,n_paths=15)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert message.auxiliary_graphs
    assert len(message.results) > 0

def test_xdtd_with_qg():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0003912"]
                },
                "chemical": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats"],
                    "knowledge_type": "inferred"
                }
            }
        }
        },
        "operations": {"actions": [
            "infer(action=drug_treatment_graph_expansion, disease_curie=test_xdtd_with_qg, qedge_id=t_edge)",
            "return(message=true, store=true)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'ERROR'
    #assert len(message.query_graph.edges) > 1
    #assert len(message.results) > 0


def test_xdtd_with_qg2():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats"],
                    "knowledge_type": "inferred"
                }
            }
        }
        },
        "operations": {"actions": [
            "infer(action=drug_treatment_graph_expansion, disease_curie=MONDO:0015564, qedge_id=t_edge)",
            "return(message=true, store=true)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 1
    assert len(message.results) > 0


def test_xdtd_with_qg3():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats"],
                    "knowledge_type": "inferred"
                }
            }
        }
        },
        "operations": {"actions": [
            "infer(action=drug_treatment_graph_expansion, disease_curie=MONDO:0015564, qedge_id=t_edge, n_drugs=10, n_paths=10)",
            "return(message=true, store=true)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert message.auxiliary_graphs
    assert len(message.results) > 0

def test_xdtd_with_only_qg():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats"],
                    "knowledge_type": "inferred"
                }
            }
        }
        }
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 1
    assert len(message.results) > 0

@pytest.mark.slow
def test_xcrg_infer_bomeol():
    query = {"operations": {"actions": [
            "create_message",
            "infer(action=chemical_gene_regulation_graph_expansion, subject_curie=CHEMBL.COMPOUND:CHEMBL1097205, regulation_type=increase, threshold=0.6, path_len=2, n_result_curies=1, n_paths=1)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0
    creative_mode_edges = [x for x in list(message.knowledge_graph.edges.keys()) if 'creative_CRG_prediction' in x]
    if len(creative_mode_edges) != 0:
        edge_key = creative_mode_edges[0]
        edge_result = message.knowledge_graph.edges[edge_key]
        assert edge_result.predicate in ['biolink:regulates', 'biolink:affects']

@pytest.mark.slow
def test_xcrg_with_qg1():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "gene": {
                    "ids": ["UniProtKB:P48736"]
                },
                "chemical": {
                    "categories": ['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']
                }
            },
            "edges": {
                "r_edge": {
                    "object": "gene",
                    "subject": "chemical",
                    "predicates": ['biolink:regulates', 'biolink:affects'],
                    "knowledge_type": "inferred",
                    "qualifier_constraints": [
                        {
                            "qualifier_set": [
                                {
                                    "qualifier_type_id": "biolink:object_direction_qualifier",
                                    "qualifier_value": "increased"
                                }
                            ]
                        }
                    ]
                }
            }
        }
        },
        "operations": {"actions": [
            "infer(action=chemical_gene_regulation_graph_expansion,object_qnode_id=gene,qedge_id=r_edge,n_result_curies=1, n_paths=1)",
            "return(message=true, store=true)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0
    creative_mode_edges = [x for x in list(message.knowledge_graph.edges.keys()) if 'creative_CRG_prediction' in x]
    if len(creative_mode_edges) != 0:
        edge_key = creative_mode_edges[0]
        edge_result = message.knowledge_graph.edges[edge_key]
        assert edge_result.predicate == 'biolink:regulates'


@pytest.mark.slow
def test_xcrg_with_qg2():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "chemical": {
                    "ids": ["CHEMBL.COMPOUND:CHEMBL1097205"]
                },
                "gene": {
                    "categories": ["biolink:Gene","biolink:Protein"]
                },

            },
            "edges": {
                "r_edge": {
                    "object": "gene",
                    "subject": "chemical",
                    "predicates": ['biolink:regulates', 'biolink:affects'],
                    "knowledge_type": "inferred",
                    "qualifier_constraints": [
                        {
                            "qualifier_set": [
                                {
                                    "qualifier_type_id": "biolink:object_direction_qualifier",
                                    "qualifier_value": "decreased"
                                }
                            ]
                        }
                    ]
                }
            }
        }
        },
        "operations": {"actions": [
            "infer(action=chemical_gene_regulation_graph_expansion,subject_qnode_id=chemical,qedge_id=r_edge,n_result_curies=1, n_paths=1)",
            "return(message=true, store=true)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0
    creative_mode_edges = [x for x in list(message.knowledge_graph.edges.keys()) if 'creative_CRG_prediction' in x]
    if len(creative_mode_edges) != 0:
        edge_key = creative_mode_edges[0]
        edge_result = message.knowledge_graph.edges[edge_key]
        assert edge_result.predicate == 'biolink:regulates'


@pytest.mark.slow
def test_xcrg_with_only_qg():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "gene": {
                    "ids": ["UniProtKB:P48736"]
                },
                "chemical": {
                    "categories": ['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']
                }
            },
            "edges": {
                "r_edge": {
                    "object": "gene",
                    "subject": "chemical",
                    "predicates": ["biolink:regulates", "biolink:affects"],
                    "knowledge_type": "inferred",
                    "qualifier_constraints": [
                        {
                            "qualifier_set": [
                                {
                                    "qualifier_type_id": "biolink:object_direction_qualifier",
                                    "qualifier_value": "decreased"
                                }
                            ]
                        }
                    ]
                }
            }
        }
        }
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0
    creative_mode_edges = [x for x in list(message.knowledge_graph.edges.keys()) if 'creative_CRG_prediction' in x]
    if len(creative_mode_edges) != 0:
        edge_key = creative_mode_edges[0]
        edge_result = message.knowledge_graph.edges[edge_key]
        assert edge_result.predicate == 'biolink:regulates'

@pytest.mark.slow
def test_xcrg_infer_dsl():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=acetaminophen, key=n0)",
            "add_qnode(categories=biolink:Gene, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "infer(action=chemical_gene_regulation_graph_expansion, subject_qnode_id=n0, qedge_id=e0, regulation_type=increase, n_result_curies=1, n_paths=1)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=30)",
            "return(message=true, store=true)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) >= 1
    assert len(message.results) > 0
    creative_mode_edges = [x for x in list(message.knowledge_graph.edges.keys()) if 'creative_CRG_prediction' in x]
    if len(creative_mode_edges) != 0:
        edge_key = creative_mode_edges[0]
        edge_result = message.knowledge_graph.edges[edge_key]
        assert edge_result.predicate == 'biolink:regulates'
