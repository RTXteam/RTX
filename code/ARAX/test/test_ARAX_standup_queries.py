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
    attribute_type: the attribute type (eg. 'EDAM:data_1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edges_of_interest = []
    values = set()
    for key, edge in message.knowledge_graph.edges.items():
        if hasattr(edge, 'edge_attributes'):
            for attr in edge.edge_attributes:
                if attr.name == attribute_name:
                    edges_of_interest.append(edge)
                    assert attr.type == attribute_type
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
        assert edge.attributes[0].name == attribute_name
        values.add(edge.attributes[0].value)
        assert edge.attributes[0].type == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_gene_to_pathway_issue_9():
    query = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": ["NCBIGENE:1017"],
                        "categories": ["biolink:Gene"]
                    },
                    "n1": {
                        
                        "categories": ["biolink:Pathway"]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1"
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_chemicals_to_gene_issue_10():
    query = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": ["UniProtKB:P52788"],
                        "categories":["biolink:Gene"]
                    },
                    "n1": {
                        "categories": ["biolink:ChemicalSubstance"]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1"
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_named_thing_associated_with_acrocynaosis_issue_12():
    query = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": ["UMLS:C0221347"],
                        "categories":["biolink:PhenotypicFeature"]
                    },
                    "n1": {
                        "categories": ["biolink:NamedThing"]
                    }
                },
                "edges": {
                    "e01": {
                        "subject": "n0",
                        "object": "n1"
                    }
                }
            }
        }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_chemical_substances_correlated_with_asthma_issue_18():
    query = {
      "message": {
        "query_graph": {
          "nodes": {
            "n0": {
              "ids": ["MONDO:0004979"],
              "categories": ["biolink:Disease"]
            },
            "n1": {
              "categories": ["biolink:ChemicalSubstance"]
            }
          },
          "edges": {
            "e01": {
              "subject": "n0",
              "object": "n1",
              "predicates": ["biolink:correlated_with"]
            }
          }
        }
      }
    }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_diseases_treated_by_drug_issue_20():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e01": {
              "object": "n0",
              "predicates": ["biolink:treated_by"],
              "subject": "n1"
            }
          },
          "nodes": {
            "n0": {
              "categories": ["biolink:Drug"],
              "ids": ["DRUGBANK:DB00394"]
            },
            "n1": {
              "categories": ["biolink:Disease"]
            }
          }
        }
      }
     }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_chemical_substances_that_down_regulate_STK11_issue_28():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e01": {
              "object": "n0",
              "predicates": ["biolink:prevents",
                "biolink:negatively_regulates",
                "biolink:decreases_secretion_of",
                "biolink:decreases_secretion_of",
                "biolink:decreases_transport_of",
                "biolink:decreases_activity_of",
                "biolink:decreases_synthesis_of",
                "biolink:decreases_expression_of",
                "biolink:increases_degradation_of",
                "biolink:entity_negatively_regulates_entity",
                "biolink:disrupts",
                "biolink:directly_negatively_regulates",
                "biolink:inhibits",
                "biolink:inhibitor",
                "biolink:channel_blocker",
                "biolink:disrupts",
                "biolink:may_inhibit_effect_of"
              ],
              "subject": "n1"
            }
          },
          "nodes": {
            "n0": {
              "ids": ["HGNC:11389"]
            },
            "n1": {
              "categories": ["biolink:ChemicalSubstance"]
            }
          }
        }
      }
     }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


# This query doesn't find results after conflations were resolved in KG2.6.7
@pytest.mark.skip
def test_phenotypes_for_angel_shaped_phalango_epiphyseal_dysplasia_issue_33():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e01": {
              "object": "n0",
              "subject": "n1",
              "predicates":["biolink:has_phenotype"]
            }
          },
          "nodes": {
            "n0": {
              "ids": ["MONDO:0007114"],
              "categories":["biolink:Disease"]
            },
            "n1": {
              "categories": ["biolink:PhenotypicFeature"]
            }
          }
        }
      }
     }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0


if __name__ == "__main__":
    pytest.main(['-v'])

