import os
import pprint
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
from ARAX_query import ARAXQuery

def test_issue_2735():
    qg = {
        "edges": {
            "7b348721": {
                "attribute_constraints": [],
                "knowledge_type": "inferred",
                "object": "on",
                "predicates": [
                    "biolink:affects",
                ],
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:qualified_predicate",
                                "qualifier_value": "biolink:causes",
                            },
                            {
                                "qualifier_type_id": "biolink:object_aspect_qualifier",
                                "qualifier_value": "activity_or_abundance",
                            },
                            {
                                "qualifier_type_id": "biolink:object_direction_qualifier",
                                "qualifier_value": "decreased",
                            },
                        ],
                    },
                ],
                "subject": "sn",
            },
        },
        "nodes": {
            "on": {
                "categories": [
                    "biolink:Gene",
                ],
                "constraints": [],
                "is_set": False,
                "set_interpretation": "BATCH",
            },
            "sn": {
                "categories": [
                    "biolink:ChemicalEntity",
                ],
                "constraints": [],
                "ids": [
                    "CHEBI:167574",
                ],
                "is_set": False,
                "set_interpretation": "BATCH",
            },
        },
    }
    response = ARAXQuery().query({"message":
                                 {"query_graph": qg}}).envelope
    assert any('no results remain' in log_entry['message'] \
               for log_entry in response.logs)

    
