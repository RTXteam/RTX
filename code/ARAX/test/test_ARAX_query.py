#!/usr/bin/env python3

import sys
import os
import pytest


sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery


def test_query_by_query_graph_2():
    query = { "message": { "query_graph": { "edges": {
                "qg2": { "subject": "qg1", "object": "qg0", "predicates": ["biolink:physically_interacts_with"] }
            },
            "nodes": {
                "qg0": { "name": "acetaminophen", "ids": ["CHEMBL.COMPOUND:CHEMBL112"], "categories": ["biolink:ChemicalEntity"] },
                "qg1": { "name": None, "ids": None, "categories": ["biolink:Protein"] }
            } } } }
    araxq = ARAXQuery()
    araxq.query(query)
    response = araxq.response
    print(response.show())

    assert response.status == 'OK'
    message = response.envelope.message
    assert len(message.results) >= 10
    assert response.envelope.schema_version == '1.4.0'


if __name__ == "__main__": pytest.main(['-v'])
