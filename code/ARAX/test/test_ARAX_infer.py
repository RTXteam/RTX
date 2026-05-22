#!/usr/bin/env python3

# Intended to test ARAX infer

import sys
import os
import pytest
from collections import Counter
from typing import List, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

PACKAGE_PARENT = '../../UI/OpenAPI/openapi_server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.message import Message  # noqa: E402


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
            "return(message=true, store=false)"
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
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert message.auxiliary_graphs
    assert len(message.results) > 0

def test_xdtd_infer_rituximab_1():
    query = {"operations": {"actions": [
            "create_message",
            "infer(action=drug_treatment_graph_expansion,drug_curie=UNII:4F4X42SYQ6)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert len(message.query_graph.edges) == 1
    assert len(message.results) > 0

def test_xdtd_infer_rituximab_2():
    query = {"operations": {"actions": [
            "create_message",
            "infer(action=drug_treatment_graph_expansion,drug_curie=UNII:4F4X42SYQ6,n_diseases=2,n_paths=15)",
            "return(message=true, store=false)"
        ]}}
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert message.auxiliary_graphs
    assert len(message.results) > 0


def test_xdtd_issue2160():
    query = {
        "message": {"query_graph": 
            {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "on",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "sn"
                    }
                },
                "nodes": {
                    "on": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0019600"
                    ],
                    },
                    "sn": {
                    "categories": [
                        "biolink:SmallMolecule"
                    ],
                    "constraints": [],
                    "ids": [
                        "PUBCHEM.COMPOUND:23931"
                    ],
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'

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
            "return(message=true, store=false)"
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
            "return(message=true, store=false)"
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
            "infer(action=drug_treatment_graph_expansion, disease_curie=MONDO:0015564, qedge_id=t_edge, n_drugs=20, n_paths=15)",
            "return(message=true, store=false)"
        ]}
    }
    [response, message] = _do_arax_query(query)
    # return response, message
    assert response.status == 'OK'
    assert message.auxiliary_graphs
    assert len(message.results) > 0


@pytest.mark.slow
def test_xdtd_with_qg4():
    query = {
        "message": {"query_graph": {
            "nodes": {
                "disease": {
                    "categories": ["biolink:Disease"]
                },
                "chemical": {
                    "ids": ["UNII:4F4X42SYQ6"]
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
            "infer(action=drug_treatment_graph_expansion, drug_curie=UNII:4F4X42SYQ6, qedge_id=t_edge)",
            "return(message=true, store=false)"
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
            "return(message=true, store=false)"
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
            "return(message=true, store=false)"
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
        assert edge_result.predicate in ['biolink:regulates', 'biolink:affects']


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
                    "predicates": ['biolink:affects'],
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
            "return(message=true, store=false)"
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
        assert edge_result.predicate in ['biolink:regulates', 'biolink:affects']

@pytest.mark.slow
def test_xcrg_with_only_qg():
    query = {
            "message": {"query_graph": {
            "edges": {
                "t_edge": {
                "knowledge_type": "inferred",
                "object": "ON",
                "predicates": [
                    "biolink:affects"
                ],
                "qualifier_constraints": [
                    {
                    "qualifier_set": [
                        {
                        "qualifier_type_id": "biolink:object_aspect_qualifier",
                        "qualifier_value": "activity_or_abundance"
                        },
                        {
                        "qualifier_type_id": "biolink:object_direction_qualifier",
                        "qualifier_value": "increased"
                        }
                    ]
                    }
                ],
                "subject": "SN"
                }
            },
            "nodes": {
                "ON": {
                "categories": [
                    "biolink:Gene"
                ],
                "ids": [
                    "NCBIGene:1576"
                ]
                },
                "SN": {
                "categories": [
                    "biolink:ChemicalEntity"
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
        assert edge_result.predicate in ['biolink:regulates', 'biolink:affects']

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
            "return(message=true, store=false)"
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
def test_xdtd_publications_in_edge_attributes():
    query = {
        "message": {"query_graph": {
            "edges": {
                "t_edge": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "on",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "sn"
                }
            },
            "nodes": {
                "on": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0015564"
                    ],
                },
                "sn": {
                    "categories": [
                        "biolink:SmallMolecule"
                    ],
                    "constraints": [],
                }
            }
        }}
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0

    prediction_edge_keys = {k for k in message.knowledge_graph.edges if k.startswith("creative_DTD_prediction_")}
    path_edge_keys = set(message.knowledge_graph.edges.keys()) - prediction_edge_keys

    publications_found = False
    for edge_key in path_edge_keys:
        edge = message.knowledge_graph.edges[edge_key]
        if edge.attributes:
            for attr in edge.attributes:
                if attr.attribute_type_id == "biolink:publications":
                    publications_found = True
                    assert attr.original_attribute_name == "publications"
                    assert attr.value is not None
                    assert isinstance(attr.value, list)
                    assert len(attr.value) > 0
                    assert all(isinstance(v, str) for v in attr.value)
                    break
        if publications_found:
            break

    assert publications_found, "No biolink:publications attribute found on any explanation path edge"


@pytest.mark.slow
def test_xdtd_extra_edge_attributes():
    query = {
        "message": {"query_graph": {
            "edges": {
                "t_edge": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "on",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "sn"
                }
            },
            "nodes": {
                "on": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0015564"
                    ],
                },
                "sn": {
                    "categories": [
                        "biolink:SmallMolecule"
                    ],
                    "constraints": [],
                }
            }
        }}
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0

    new_column_type_ids = {
        "biolink:category",
        "biolink:original_subject",
        "biolink:original_object",
    }

    extra_attr_type_ids = {
        "biolink:qualified_predicate",
        "biolink:has_confidence_score",
        "biolink:object_aspect_qualifier",
        "biolink:object_direction_qualifier",
        "biolink:has_affinity",
        "biolink:species_context_qualifier",
        "biolink:max_research_phase",
        "biolink:p_value",
        "biolink:has_supporting_studies",
    }

    found_new_column_attrs = set()
    found_extra_attrs = set()
    infer_edge_count = 0

    for edge_key, edge in message.knowledge_graph.edges.items():
        if not edge_key.startswith("urn:uuid:"):
            continue
        if not edge.attributes:
            continue
        infer_edge_count += 1

        for attr in edge.attributes:
            if attr.attribute_type_id in new_column_type_ids:
                found_new_column_attrs.add(attr.attribute_type_id)
                assert attr.value is not None
                assert attr.original_attribute_name is None
            if attr.attribute_type_id in extra_attr_type_ids:
                found_extra_attrs.add(attr.attribute_type_id)
                assert attr.value is not None
                assert attr.original_attribute_name is None

    assert infer_edge_count > 0, "No infer-produced path edges found"
    assert found_new_column_attrs, (
        "No new column attributes (category/original_subject/original_object) "
        "found on any infer path edge"
    )
    assert "biolink:category" in found_new_column_attrs, (
        "biolink:category attribute not found on any infer path edge"
    )
    assert found_extra_attrs, (
        "No extra_attributes (qualified_predicate, has_confidence_score, etc.) "
        "found on any infer path edge"
    )
