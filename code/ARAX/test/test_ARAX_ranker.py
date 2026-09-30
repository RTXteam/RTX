#!/usr/bin/env python3

# Usage:
# run all: pytest -v test_ARAX_ranker.py
# run just certain tests: pytest -v test_ARAX_ranker.py -k test_ARAXRanker

import sys
import os
import numpy as np
import scipy.stats
import pytest
import requests_cache
import pickle
import copy
import ast
from typing import List, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_query import ARAXQuery
from query_graph_info import QueryGraphInfo
from actions_parser import ActionsParser
from result_transformer import ResultTransformer
from ARAX_ranker import ARAXRanker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer")
from node_synonymizer import NodeSynonymizer
synonymizer = NodeSynonymizer()

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

def _extract_ARAX_online_results(response_id: str, api_link: str = 'https://arax.ncats.io/api/arax/v1.4/response/') -> List[Union[ARAXResponse, Message]]:
    # Extracts the ARAXResponse objects from the ARAX online results
    
    # generate an ARAX response object
    response = ARAXResponse()
    #### Create an empty envelope
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    response.envelope.submitter = '?'

    # extract results based on response_id
    message = messenger.fetch_message(f'{api_link}{response_id}')
    response.envelope.message = message
    return [response, response.envelope.message]

def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    # Perform the ARAX query
    
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    #return [response, araxq.message]
    return [response, response.envelope.message]

def _do_arax_rank(response: ARAXResponse) -> Message:
    # Rank the ARAX results
    
    ranker = ARAXRanker()
    ranker.aggregate_scores_dmk(response)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return response.envelope.message

def _ranker_tester(query: dict = None, response_id: str = None) -> Message:
    # Test the ARAX ranker
    
    if response_id is not None:
        [response, _] = _extract_ARAX_online_results(response_id)
    else:
        [response, _] = _do_arax_query(query)
    message = _do_arax_rank(response)
    return message

@pytest.mark.slow
def test_ARAXRanker_test1_asset12():
    # test 'rituximab treats Castleman Disease'
    expected_answer = 'rituximab'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0015564"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248097')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test5_asset70():
    # test 'Miglustat treats Niemann-Pick type C'
    expected_answer = 'Miglustat'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']
    
    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0018982"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248115')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test6_asset72():
    # test 'Lomitapide treats Homozygous Familial Hypercholesterolemia'
    expected_answer = 'Lomitapide'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0018328"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248120')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test9_asset614():
    # test 'famotidine treats Gastroesophageal Reflux Disease'
    expected_answer = 'famotidine'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0007186"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test9_asset619():
    # test 'lansoprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'lansoprazole'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']
    
    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0007186"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message
    
    # returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test9_asset623():
    # test 'rabeprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'rabeprazole'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "e01": {
                    "attribute_constraints": [],
                    "knowledge_type": "inferred",
                    "object": "ON",
                    "predicates": [
                        "biolink:treats"
                    ],
                    "qualifier_constraints": [],
                    "subject": "SN"
                    }
                },
                "nodes": {
                    "ON": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "constraints": [],
                    "ids": [
                        "MONDO:0007186"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test13_asset311():
    # test 'Benazepril decreases activity or abundance of ACE'
    expected_answer = 'Benazepril'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:1636"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test13_asset355():
    # test 'Fosinopril decreases activity or abundance of ACE'
    expected_answer = 'Fosinopril'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:1636"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test13_asset360():
    # test 'Trandolapril decreases activity or abundance of ACE'
    expected_answer = 'Trandolapril'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:1636"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)
    
@pytest.mark.slow
def test_ARAXRanker_test13_asset361():
    # test 'Moexipril decreases activity or abundance of ACE'
    expected_answer = 'Moexipril'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:1636"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test21_asset338():
    # test 'canagliflozin decreases activity or abundance of SLC5A2 (human)'
    expected_answer = 'canagliflozin'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:6524"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248191')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

@pytest.mark.slow
def test_ARAXRanker_test23_asset381():
    # test 'atenolol decreases activity or abundance of ADRB2'
    expected_answer = 'atenolol'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:154"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248199')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


@pytest.mark.slow
def test_ARAXRanker_test23_asset378():
    # test 'propranolol decreases activity or abundance of ADRB2'
    expected_answer = 'propranolol'
    preferred_curie = synonymizer.get_canonical_curies(names=expected_answer)[expected_answer]
    if preferred_curie is None:
        expected_answer = expected_answer
    else:
        expected_answer = preferred_curie['preferred_name']

    query = { "message": { "query_graph": {
                "edges": {
                    "t_edge": {
                    "attribute_constraints": [],
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
                            "qualifier_value": "decreased"
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
                    "constraints": [],
                    "ids": [
                        "NCBIGene:154"
                    ],
                    "set_interpretation": "BATCH"
                    },
                    "SN": {
                    "categories": [
                        "biolink:ChemicalEntity"
                    ],
                    "constraints": [],
                    "set_interpretation": "BATCH"
                    }
                }
            } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message

    # returned_message = _ranker_tester(response_id='248199')
    rank_right_answer = -1
    for index, result in enumerate(message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(message.results)
    
    assert rank_right_answer != -1
    assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


if __name__ == "__main__":
    pytest.main(['-v'])


# ── Statistical Significance Qualifier tests ───────────────────────────

def test_significance_qualifier_score_mapping():
    """Verify ordinal score mapping for all five significance bands."""
    from ARAX_ranker import _significance_band_scores
    scores = []
    for band in ["very_strongly_significant", "strongly_significant",
                 "significant", "suggestive", "not_significant"]:
        score = _significance_band_scores[band]
        assert 0.0 <= score <= 1.0
        scores.append(score)
    # Scores must be strictly descending (more significant = higher score)
    assert scores == sorted(scores, reverse=True)
    assert scores[-1] == 0.0  # not_significant → 0


def test_significance_qualifier_lookup():
    """Verify _get_significance_qualifier_value finds the qualifier in edge.qualifiers."""
    from openapi_server.models.qualifier import Qualifier
    ranker = ARAXRanker()

    # In edge.qualifiers (expected Retriever path)
    edge_q = Edge(subject="A", object="B", predicate="biolink:related_to",
                  qualifiers=[Qualifier(qualifier_type_id="biolink:statistical_significance_qualifier",
                                        qualifier_value="significant")])
    assert ranker._get_significance_qualifier_value(edge_q) == "significant"

    # biolink:-prefixed value
    edge_prefixed = Edge(subject="A", object="B", predicate="biolink:related_to",
                         qualifiers=[Qualifier(qualifier_type_id="biolink:statistical_significance_qualifier",
                                               qualifier_value="biolink:significant")])
    assert ranker._get_significance_qualifier_value(edge_prefixed) == "significant"

    # No qualifier at all
    edge_none = Edge(subject="A", object="B", predicate="biolink:related_to")
    assert ranker._get_significance_qualifier_value(edge_none) is None


def test_significance_qualifier_lookup_edge_cases():
    """Verify lookup handles edge cases: multiple qualifiers, unrecognized values, empty lists."""
    from openapi_server.models.qualifier import Qualifier
    ranker = ARAXRanker()

    # Multiple qualifiers on same edge — only pick the significance one
    edge_multi_q = Edge(subject="A", object="B", predicate="biolink:related_to",
                        qualifiers=[
                            Qualifier(qualifier_type_id="biolink:object_direction_qualifier",
                                      qualifier_value="increased"),
                            Qualifier(qualifier_type_id="biolink:statistical_significance_qualifier",
                                      qualifier_value="suggestive"),
                            Qualifier(qualifier_type_id="biolink:object_aspect_qualifier",
                                      qualifier_value="activity_or_abundance"),
                        ])
    assert ranker._get_significance_qualifier_value(edge_multi_q) == "suggestive"

    # Empty qualifiers list (not None)
    edge_empty_q = Edge(subject="A", object="B", predicate="biolink:related_to", qualifiers=[])
    assert ranker._get_significance_qualifier_value(edge_empty_q) is None

    # Qualifier present but value is an unrecognized enum string
    edge_bad = Edge(subject="A", object="B", predicate="biolink:related_to",
                    qualifiers=[Qualifier(qualifier_type_id="biolink:statistical_significance_qualifier",
                                          qualifier_value="totally_significant")])
    # Lookup returns the raw value; the scorer maps unknown → 0.0
    assert ranker._get_significance_qualifier_value(edge_bad) == "totally_significant"


def test_significance_qualifier_additive_with_pvalue():
    """Verify the qualifier contributes additively alongside a numeric pValue attribute."""
    from openapi_server.models.attribute import Attribute
    from openapi_server.models.qualifier import Qualifier
    ranker = ARAXRanker()

    # Edge with both a pValue attribute AND a significance qualifier
    edge = Edge(subject="A", object="B", predicate="biolink:related_to",
                attributes=[Attribute(attribute_type_id="biolink:pValue",
                                      original_attribute_name="pValue",
                                      value="0.001")],
                qualifiers=[Qualifier(qualifier_type_id="biolink:statistical_significance_qualifier",
                                      qualifier_value="very_strongly_significant")])
    confidence = ranker.edge_attribute_score_combiner("A--biolink:related_to--B--infores:test", edge)
    assert 0.0 < confidence <= 1.0
    # Should be higher than base score of 0.5 since both signals are positive
    assert confidence > 0.5

    # Edge with only pValue (no qualifier) — should still be > 0.5 but lower contribution
    edge_no_qual = Edge(subject="A", object="B", predicate="biolink:related_to",
                        attributes=[Attribute(attribute_type_id="biolink:pValue",
                                              original_attribute_name="pValue",
                                              value="0.001")])
    confidence_no_qual = ranker.edge_attribute_score_combiner("A--biolink:related_to--B--infores:test", edge_no_qual)
    assert confidence >= confidence_no_qual  # additive qualifier can only help or be neutral


@pytest.mark.slow
def test_significance_qualifier_ranking_integration():
    """End-to-end: expand, rank, verify results are scored and sorted."""
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=MONDO:0005148, key=n00)",
        "add_qnode(categories=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    assert response.status == 'OK'
    message = response.envelope.message
    assert len(message.results) > 0
    scores = [r.analyses[0].score for r in message.results]
    assert scores == sorted(scores, reverse=True)
