#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery


def test_query_by_canned_query_Q0():
    query = { 'message': { 'query_type_id': 'Q0', 'terms': { 'term': 'lovastatin' } } }
    araxq = ARAXQuery()
    result = araxq.query(query)
    assert result.status == 'OK'
    message = araxq.message
    assert message.n_results == 1
    assert message.type == 'translator_reasoner_message'
    assert message.schema_version == '0.9.2'                    # FIXME

def test_query_by_query_graph_2():
    query = { "message": { "query_graph": { "edges": [
                { "id": "qg2", "source_id": "qg1", "target_id": "qg0", "type": "physically_interacts_with" }
            ],
            "nodes": [
                { "id": "qg0", "name": "acetaminophen", "curie": "CHEMBL.COMPOUND:CHEMBL112", "type": "chemical_substance" },
                { "id": "qg1", "name": None, "desc": "Generic protein", "curie": None, "type": "protein" }
            ] } } }
    araxq = ARAXQuery()
    result = araxq.query(query)
    assert result.status == 'OK'
    message = araxq.message
    assert message.n_results == 32
    assert message.schema_version == '0.9.3'
    assert message.results[0].essence == 'cytochrome P450 family 3 subfamily A member 4 (CP3A4)'


if __name__ == "__main__": pytest.main(['-v'])
