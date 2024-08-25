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


def test_ARAXRanker_test1_asset12():
    # test 'rituximab treats Castleman Disease'
    expected_answer = 'rituximab'

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
    
    # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

def test_ARAXRanker_test5_asset70():
    # test 'Miglustat treats Niemann-Pick type C'
    expected_answer = 'Miglustat'
    
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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

def test_ARAXRanker_test6_asset72():
    # test 'Lomitapide treats Homozygous Familial Hypercholesterolemia'
    expected_answer = 'Lomitapide'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)

def test_ARAXRanker_test9_asset614():
    # test 'famotidine treats Gastroesophageal Reflux Disease'
    expected_answer = 'famotidine'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test9_asset619():
    # test 'lansoprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'lansoprazole'
    
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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test9_asset623():
    # test 'rabeprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'rabeprazole'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test13_asset311():
    # test 'Benazepril decreases activity or abundance of ACE'
    expected_answer = 'Benazepril'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test13_asset355():
    # test 'Fosinopril decreases activity or abundance of ACE'
    expected_answer = 'Fosinopril'

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
    
    # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test13_asset360():
    # test 'Trandolapril decreases activity or abundance of ACE'
    expected_answer = 'Trandolapril'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)
    
    
def test_ARAXRanker_test13_asset361():
    # test 'Moexipril decreases activity or abundance of ACE'
    expected_answer = 'Moexipril'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test21_asset338():
    # test 'canagliflozin decreases activity or abundance of SLC5A2 (human)'
    expected_answer = 'canagliflozin'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test23_asset381():
    # test 'atenolol decreases activity or abundance of ADRB2'
    expected_answer = 'atenolol'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


def test_ARAXRanker_test23_asset378():
    # test 'propranolol decreases activity or abundance of ADRB2'
    expected_answer = 'propranolol'

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
    
    # # comment out this until the full build of xDTD
    # assert rank_right_answer != -1
    # assert (rank_right_answer < 0.1 * total_results) or (rank_right_answer < 0.3 * total_results)


if __name__ == "__main__":
    pytest.main(['-v'])
