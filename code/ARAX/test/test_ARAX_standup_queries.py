#!/usr/bin/env python3

# Intended to test our more complicated workflows

import sys
import os
import pytest
import copy
import json
import ast
from typing import List, Union, Optional

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

PACKAGE_PARENT = '../../UI/OpenAPI/openapi_server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.message import Message


def _do_arax_query(query: dict, timeout: Optional[int] = None) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    if timeout:
        query["query_options"] = {"kp_timeout": timeout}
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, response.envelope.message]


def test_gene_to_pathway_issue_9():
    query = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": ["NCBIGene:1017"],
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
    [response, message] = _do_arax_query(query, timeout=30)
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
                        "categories": ["biolink:ChemicalEntity"]
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
    [response, message] = _do_arax_query(query, timeout=30)
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
    [response, message] = _do_arax_query(query, timeout=30)
    assert response.status == 'OK'
    assert len(message.results) > 0


@pytest.mark.external
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
              "categories": ["biolink:ChemicalEntity"]
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
    [response, message] = _do_arax_query(query, timeout=30)
    assert response.status == 'OK'
    assert len(message.results) > 0


@pytest.mark.slow
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
    [response, message] = _do_arax_query(query, timeout=30)
    assert response.status == 'OK'
    assert len(message.results) > 0


def test_chemical_substances_that_down_regulate_STK11_issue_28():
    # "Down-regulates" is expressed with qualifiers on biolink:affects now, not with the old regulation predicates
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e01": {
              "subject": "n1",
              "object": "n0",
              "predicates": ["biolink:affects"],
              "qualifier_constraints": [{"qualifier_set": [
                {"qualifier_type_id": "biolink:object_aspect_qualifier", "qualifier_value": "activity_or_abundance"},
                {"qualifier_type_id": "biolink:object_direction_qualifier", "qualifier_value": "decreased"}
              ]}]
            }
          },
          "nodes": {
            "n0": {
              "ids": ["HGNC:11389"]
            },
            "n1": {
              "categories": ["biolink:ChemicalEntity"]
            }
          }
        }
      }
     }
    [response, message] = _do_arax_query(query, timeout=30)
    assert response.status == 'OK'
    assert len(message.results) > 0


# The disease is the subject of has_phenotype (disease has_phenotype phenotypic feature)
def test_phenotypes_for_angel_shaped_phalango_epiphyseal_dysplasia_issue_33():
    query = {
      "message": {
        "query_graph": {
          "edges": {
            "e01": {
              "subject": "n0",
              "object": "n1",
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
    [response, message] = _do_arax_query(query, timeout=30)
    assert response.status == 'OK'
    assert len(message.results) > 0


if __name__ == "__main__":
    pytest.main(['-v'])

