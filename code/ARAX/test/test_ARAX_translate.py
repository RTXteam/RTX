#!/usr/bin/env python3

# Intended to test our translate to ARAXi functionality

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
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edges_of_interest = []
    values = set()
    for key, edge in message.knowledge_graph.edges.items():
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
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert edge_predicate in edge_predicates_in_kg
    edges_of_interest = [x for x in message.knowledge_graph.edges.values() if x.relation == relation]
    values = set()
    assert len(edges_of_interest) > 0
    for edge in edges_of_interest:
        assert hasattr(edge, 'attributes')
        assert edge.attributes
        assert edge.attributes[0].original_attribute_name == attribute_name
        values.add(edge.attributes[0].value)
        assert edge.attributes[0].attribute_type_id == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_lookup():
    query = {
        "workflow": [
            {
                "id": "lookup"
            }

        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:SmallMolecule"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0
    for result in message.results:
        assert result.score is None

def test_fill_success():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:rtx-kg2"],
                    "qedge_keys": ["e01"]
                }
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalSubstance"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.knowledge_graph.nodes) > 0
    assert len(message.knowledge_graph.edges) > 0

def test_fill_error():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:rtx-kg2"],
                    "qedge_keys": ["asdf"]
                }
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalSubstance"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'ERROR'
    assert len(message.knowledge_graph.nodes) == 0
    assert len(message.knowledge_graph.edges) == 0

def test_score():
    query = {
        "workflow": [
            {
                "id": "lookup"
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
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:SmallMolecule"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0
    for result in message.results:
        assert result.score is not None

def test_bind():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:rtx-kg2"]
                }
            },
            {
                "id": "bind"
            }

        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalSubstance"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0

def test_complete_results():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:rtx-kg2"]
                }
            },
            {
                "id": "complete_results"
            }

        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalSubstance"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0

def test_filter_results_top_n():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:rtx-kg2"]
                }
            },
            {
                "id": "overlay_compute_ngd",
                "parameters": {
                    "virtual_relation_label": "NGD1",
                    "qnode_keys": ["n0", "n1"]
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
                    "max_results": 20
                }
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:SmallMolecule"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20
    for result in message.results:
        assert result.score is not None

def test_overlay_after_lookup():
    query = {
        "workflow": [
            {
                "id": "lookup"
            },
            {
                "id": "overlay_compute_ngd",
                "parameters": {
                    "virtual_relation_label": "NGD1",
                    "qnode_keys": ["n0", "n1"]
                }
            },
            {
                "id": "score"
            },
            {
                "id": "filter_results_top_n",
                "parameters": {
                    "max_results": 20
                }
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:SmallMolecule"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 20
    ngd_bindings = set()
    for result in message.results:
        assert result.score is not None
        for eb_key, edge_bindings in result.edge_bindings.items():
            for edge_binding in edge_bindings:
                if edge_binding.id.startswith("NGD1"):
                    ngd_bindings.add(edge_binding.id)
    assert len(ngd_bindings) == len(message.results)

@pytest.mark.slow
def test_connect_knodes_2_nodes():
    query = {
      "workflow": [
        {
          "id": "fill"
        },
        {
          "id": "overlay_connect_knodes"
        },
        {
          "id": "complete_results"
        },
        {
          "id": "score"
        },
        {
          "id": "sort_results_score",
          "parameters": {
            "ascending_or_descending": "descending"
          }
        },
        {
          "id": "filter_results_top_n",
          "parameters": {
            "max_results": 30
          }
        }
      ],
      "message": {
        "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Disease"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalEntity"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": [
                            "biolink:treats"
                        ]
                    }
                }
            }
      }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 30
    connected_bindings_ngd = set()
    connected_bindings_fisher = set()
    connected_bindings_paired_freq = set()
    connected_bindings_pred_dtd = set()
    for result in message.results:
        assert result.score is not None
        for eb_key, edge_bindings in result.edge_bindings.items():
            for edge_binding in edge_bindings:
                if edge_binding.id.startswith("connect_knodes_fisher"):
                    connected_bindings_fisher.add(edge_binding.id)
                elif edge_binding.id.startswith("connect_knodes_ngd"):
                    connected_bindings_ngd.add(edge_binding.id)
                elif edge_binding.id.startswith("connect_knodes_paired_freq"):
                    connected_bindings_paired_freq.add(edge_binding.id)
                elif edge_binding.id.startswith("connect_knodes_pred_dtd"):
                    connected_bindings_pred_dtd.add(edge_binding.id)
                    
    assert len(connected_bindings_ngd) > 0
    assert len(connected_bindings_fisher) > 0
    assert len(connected_bindings_paired_freq) > 0
    assert len(connected_bindings_pred_dtd) > 0

@pytest.mark.slow
def test_connect_knodes_3_nodes():
    query = {
      "workflow": [
        {
          "id": "fill"
        },
        {
          "id": "overlay_connect_knodes"
        },
        {
          "id": "complete_results"
        },
        {
          "id": "score"
        },
        {
          "id": "sort_results_score",
          "parameters": {
            "ascending_or_descending": "descending"
          }
        },
        {
          "id": "filter_results_top_n",
          "parameters": {
            "max_results": 30
          }
        }
      ],
      "message": {
        "query_graph": {
                "nodes": {
                    "n0": {
                        "categories": [
                            "biolink:Gene"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:45783"
                        ],
                        "categories": [
                            "biolink:ChemicalEntity"
                        ]
                    },
                    "n2": {
                        "categories": [
                            "biolink:Disease"
                        ]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n1",
                        "object": "n0",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    },
                    "e02": {
                        "subject": "n0",
                        "object": "n2",
                        "predicates": [
                            "biolink:related_to"
                        ]
                    }
                }
            }
      }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 30
    connected_bindings = set()
    for result in message.results:
        assert result.score is not None
        for eb_key, edge_bindings in result.edge_bindings.items():
            for edge_binding in edge_bindings:
                if edge_binding.id.startswith("connect_knodes"):
                    connected_bindings.add(edge_binding.id)
    assert len(connected_bindings) > 0


if __name__ == "__main__":
    pytest.main(['-v'])
