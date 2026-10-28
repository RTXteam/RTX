#!/usr/bin/env python3

# Intended to test our translate to ARAXi functionality

import sys
import os
import pytest
from typing import List, Union


sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/openapi_server/models")
from openapi_server.models.message import Message


def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, response.envelope.message]


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
                        "ids": [
                            "NCBIGene:1544"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:46195"
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
                    "allowlist": ["infores:retriever"],
                    "qedge_keys": ["e01"]
                }
            }
        ],
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": [
                            "NCBIGene:677884"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:46195"
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
                    "allowlist": ["infores:retriever"],
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
                        "ids": [
                            "NCBIGene:1571"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:46195"
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
        assert result.analyses[0].score is not None

def test_bind():
    query = {
        "workflow": [
            {
                "id": "fill",
                "parameters": {
                    "allowlist": ["infores:retriever"]
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
                        "ids": [
                            "NCBIGene:79886"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:46195"
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
                    "allowlist": ["infores:retriever"]
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
                        "ids": [
                            "NCBIGene:122809"
                        ]
                    },
                    "n1": {
                        "ids": [
                            "CHEBI:46195"
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
                    "allowlist": ["infores:retriever"]
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
                            "CHEBI:2948"
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
        assert result.analyses[0].score is not None

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
                            "CHEBI:2948"
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
        assert result.analyses[0].score is not None
        for eb_key, edge_bindings in result.analyses[0].edge_bindings.items():
            for edge_binding in edge_bindings:
                if edge_binding.id.startswith("NGD1"):
                    ngd_bindings.add(edge_binding.id)
    assert len(ngd_bindings) == len(message.results)

@pytest.mark.slow
def _get_result_edge_keys(message: Message) -> list[set[str]]:
    """Edge keys each result uses: bound edges plus edges in its support graphs (where virtual edges end up)"""
    edge_keys_by_result = []
    for result in message.results:
        edge_keys = set()
        for analysis in result.analyses:
            edge_keys.update(edge_binding.id for edge_bindings in analysis.edge_bindings.values()
                             for edge_binding in edge_bindings)
            for aux_graph_key in analysis.support_graphs or []:
                edge_keys.update(message.auxiliary_graphs[aux_graph_key].edges)
        edge_keys_by_result.append(edge_keys)
    return edge_keys_by_result


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
    assert 0 < len(message.results) <= 30
    assert all(result.analyses[0].score is not None for result in message.results)
    result_edge_keys = set().union(*_get_result_edge_keys(message))
    assert any(edge_key.startswith("connect_knodes_ngd") for edge_key in result_edge_keys)
    assert any(edge_key.startswith("connect_knodes_fisher") for edge_key in result_edge_keys)

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
    assert 0 < len(message.results) <= 30
    assert all(result.analyses[0].score is not None for result in message.results)
    result_edge_keys = set().union(*_get_result_edge_keys(message))
    assert any(edge_key.startswith("connect_knodes") for edge_key in result_edge_keys)


def test_unknown_operation():
    # Tests if unknown operations are handled correctly
        query = {
            "workflow": [
                {
                    "id": "gobbledegook"
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
        assert response.status == 'ERROR'


if __name__ == "__main__":
    pytest.main(['-v'])
