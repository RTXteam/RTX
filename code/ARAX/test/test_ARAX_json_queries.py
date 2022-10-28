#!/usr/bin/env python3
# For testing the ARAX json queries with things like the query graph interpreter
import sys
import os
import pytest
from typing import List, Dict, Tuple, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse
import Expand.expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_ARAX_expand import check_node_categories, check_property_format, check_for_orphans, print_nodes, print_edges, print_counts_by_qgid


def _run_query_and_do_standard_testing(actions: Optional[List[str]] = None, json_query: Optional[dict] = None,
                                       kg_should_be_incomplete=False, debug=False, should_throw_error=False,
                                       error_code: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[Dict[str, Dict[str, Node]], Dict[str, Dict[str, Edge]], ARAXResponse]:
    # Run the query
    araxq = ARAXQuery()
    assert actions or json_query  # Must provide some sort of query to run
    # Stick the actions in if they are provided
    if actions:
        query_object = {"operations": {"actions": actions}}
    # otherwise check if it's just the query_graph element
    elif "message" not in json_query:
        query_object = {"message": {"query_graph": json_query}}
    else:
        query_object = json_query
    if timeout:
        query_object["query_options"] = {"kp_timeout": timeout}
    response = araxq.query(query_object)
    message = araxq.message
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
    assert response.status == 'OK' or should_throw_error
    if should_throw_error and error_code:
        assert response.error_code == error_code

    # Convert output knowledge graph to a dictionary format for faster processing (organized by QG IDs)
    dict_kg = eu.convert_standard_kg_to_qg_organized_kg(message.knowledge_graph)
    nodes_by_qg_id = dict_kg.nodes_by_qg_id
    edges_by_qg_id = dict_kg.edges_by_qg_id

    # Optionally print more detail
    if debug:
        print_nodes(nodes_by_qg_id)
        print_edges(edges_by_qg_id)
        print_counts_by_qgid(nodes_by_qg_id, edges_by_qg_id)
        print(response.show(level=ARAXResponse.DEBUG))

    # Run standard testing (applies to every test case)
    assert eu.qg_is_fulfilled(message.query_graph, dict_kg, enforce_required_only=True) or kg_should_be_incomplete or should_throw_error
    check_for_orphans(nodes_by_qg_id, edges_by_qg_id)
    check_property_format(nodes_by_qg_id, edges_by_qg_id)
    check_node_categories(message.knowledge_graph.nodes, message.query_graph)

    return nodes_by_qg_id, edges_by_qg_id, response


def test_query_by_query_graph_2():
    query = { "message": { "query_graph": { "edges": {
                "qg2": { "subject": "qg1", "object": "qg0", "predicates": ["biolink:physically_interacts_with"] }
            },
            "nodes": {
                "qg0": { "name": "acetaminophen", "ids": ["CHEMBL.COMPOUND:CHEMBL112"], "categories": ["biolink:ChemicalEntity"] },
                "qg1": { "name": None, "ids": None, "categories": ["biolink:Protein"] }
            } } } }
    #araxq = ARAXQuery()
    #araxq.query(query)
    #response = araxq.response
    #print(response.show())
    nodes_by_qg_id, edges_by_qg_id, response = _run_query_and_do_standard_testing(json_query=query)
    #assert response.status == 'OK'
    #message = response.envelope.message
    #assert len(message.results) >= 20
    #assert response.envelope.schema_version == '1.2.0'


def test_ngd_added():
    """
    Test that the NGD added property is set correctly and was added by the QGI
    """
    query = {
        "edges": {
            "e00": {
                "subject": "n00",
                "object": "n01",
                "predicates": ["biolink:physically_interacts_with"]
            }
        },
        "nodes": {
            "n00": {
                "ids": ["CHEMBL.COMPOUND:CHEMBL112"]
            },
            "n01": {
                "categories": ["biolink:Protein"]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, response = _run_query_and_do_standard_testing(json_query=query)
    qg = response.envelope.message.query_graph
    assert 'N1' in qg.edges
    assert 'biolink:occurs_together_in_literature_with' in qg.edges['N1'].predicates


def test_drug_disease_query():
    query = {
        "edges": {
            "e00": {
                "subject": "n00",
                "object": "n01"
            }
        },
        "nodes": {
            "n00": {
                "ids": ["MONDO:0021783"],
                "categories": ["biolink:Disease"]
            },
            "n01": {
                "categories": ["biolink:ChemicalEntity"]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, response = _run_query_and_do_standard_testing(json_query=query)
    qg = response.envelope.message.query_graph
    assert 'N1' in qg.edges
    assert 'biolink:occurs_together_in_literature_with' in qg.edges['N1'].predicates


def test_workflow1():
    """
    Test a fill (with one KP), bind, score workflow
    """
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": [
                        "infores:rtx-kg2"
                    ],
                    "qedge_keys": [
                        "e00"
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
                    "e00": {
                        "subject": "n00",
                        "object": "n01",
                        "predicates": [
                            "biolink:physically_interacts_with"
                        ]
                    }
                },
                "nodes": {
                    "n00": {
                        "ids": [
                            "CHEMBL.COMPOUND:CHEMBL112"
                        ]
                    },
                    "n01": {
                        "categories": [
                            "biolink:Protein"
                        ]
                    }
                }
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, response = _run_query_and_do_standard_testing(json_query=query)
    essences = [x.to_dict()['essence'] for x in response.envelope.message.results]
    assert 'METICRANE' in essences

@pytest.mark.slow
def test_workflow2():
    """
    Every possible combination of allowlist and qedge_keys
    """
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": [
                        "infores:rtx-kg2",
                        "infores:biothings-explorer"
                    ],
                    "qedge_keys": [
                        "e0"
                    ]
                }
            },
            {
                "id": "fill",
                "parameters": {
                    "qedge_keys": [
                        "e0"
                    ]
                }
            },
            {
                "id": "fill",
                "parameters": {
                    "allowlist": [
                        "infores:rtx-kg2",
                        "infores:biothings-explorer"
                    ]
                }
            },
            {
                "id": "fill",
                "parameters": {
                    "allowlist": [
                        "infores:connections-hypothesis"
                    ],
                    "qedge_keys": [
                        "e1",
                        "e2"
                    ]
                }
            },
            {
                "id": "fill",
                "parameters": {
                    "allowlist": [
                        "infores:rtx-kg2",
                        "infores:biothings-explorer"
                    ],
                    "qedge_keys": [
                        "e2"
                    ]
                }
            },
            {
                "id": "bind"
            },
            {
                "id": "complete_results"
            },
            {
                "id": "score"
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Disease"
                        ],
                        "ids": [
                            "MONDO:0009061"
                        ]
                    },
                    "n1": {
                        "categories": [
                            "biolink:GrossAnatomicalStructure"
                        ]
                    },
                    "n2": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n3": {
                        "categories": [
                            "biolink:Drug",
                            "biolink:SmallMolecule"
                        ]
                    }
                },
                "edges": {
                    "e0": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    },
                    "e1": {
                        "subject": "n1",
                        "object": "n2",
                        "predicates": [
                            "biolink:expresses"
                        ]
                    },
                    "e2": {
                        "subject": "n3",
                        "object": "n2",
                        "predicates": [
                            "biolink:affects"
                        ]
                    }
                }
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, response = _run_query_and_do_standard_testing(json_query=query)
    assert response.status == 'OK'
    essences = [x.to_dict()['essence'] for x in response.envelope.message.results]

if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_json_queries.py'])




