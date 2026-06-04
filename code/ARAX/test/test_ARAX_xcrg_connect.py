#!/usr/bin/env python3

"""Fast tests for the ARAX xCRG connect integration.

These tests avoid live Retriever calls and local database requirements. The
package itself is exercised through its public query detector, while ARAX's
connect wiring is tested with a mocked xCRG runner.
"""

import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server")

import ARAX_connect
from ARAX_connect import (
    ARAXConnect,
    XCRG_RETRIEVER_URL_ENV,
    get_xcrg_retriever_url,
)
from ARAX_messenger import ARAXMessenger
from ARAX_query_graph_interpreter import ARAXQueryGraphInterpreter
from ARAX_response import ARAXResponse
from result_transformer import ResultTransformer


def _xcrg_query_graph():
    return {
        "nodes": {
            "chem": {
                "categories": ["biolink:ChemicalEntity"],
            },
            "gene": {
                "ids": ["NCBIGene:6323"],
                "categories": ["biolink:Gene"],
            },
        },
        "edges": {
            "e0": {
                "subject": "chem",
                "object": "gene",
                "predicates": ["biolink:affects"],
                "knowledge_type": "inferred",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
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
            },
        },
    }


def _xcrg_response(query_graph):
    return {
        "schema_version": "1.6.0",
        "biolink_version": "4.3.2",
        "message": {
            "query_graph": query_graph,
            "knowledge_graph": {
                "nodes": {
                    "CHEBI:1": {"categories": ["biolink:ChemicalEntity"]},
                    "NCBIGene:6323": {"categories": ["biolink:Gene"]},
                },
                "edges": {
                    "xcrg_edge_0": {
                        "subject": "CHEBI:1",
                        "predicate": "biolink:affects",
                        "object": "NCBIGene:6323",
                        "attributes": [],
                        "sources": [
                            {
                                "resource_id": "infores:arax",
                                "resource_role": "primary_knowledge_source",
                            },
                        ],
                    },
                },
            },
            "auxiliary_graphs": {},
            "results": [
                {
                    "node_bindings": {
                        "chem": [{"id": "CHEBI:1", "attributes": []}],
                        "gene": [{"id": "NCBIGene:6323", "attributes": []}],
                    },
                    "analyses": [
                        {
                            "resource_id": "infores:arax",
                            "edge_bindings": {
                                "e0": [{"id": "xcrg_edge_0", "attributes": []}],
                            },
                            "score": 1.0,
                        },
                    ],
                },
            ],
        },
    }


def _response_with_query_graph(query_graph):
    response = ARAXResponse()
    ARAXMessenger().create_envelope(response)
    response.envelope.message = ARAXMessenger().from_dict(
        {
            "query_graph": query_graph,
            "knowledge_graph": {"nodes": {}, "edges": {}},
            "results": [],
            "auxiliary_graphs": {},
        }
    )
    return response


def test_xcrg_retriever_url_uses_arax_maturity(monkeypatch):
    monkeypatch.delenv(XCRG_RETRIEVER_URL_ENV, raising=False)

    assert (
        get_xcrg_retriever_url(SimpleNamespace(maturity="staging"))
        == "https://retriever.ci.transltr.io/query"
    )
    assert (
        get_xcrg_retriever_url(SimpleNamespace(maturity="testing"))
        == "https://retriever.test.transltr.io/query"
    )
    assert (
        get_xcrg_retriever_url(SimpleNamespace(maturity="production"))
        == "https://retriever.transltr.io/query"
    )
    assert (
        get_xcrg_retriever_url(SimpleNamespace(maturity="unknown"))
        == "https://retriever.ci.transltr.io/query"
    )


def test_xcrg_retriever_url_allows_env_override(monkeypatch):
    monkeypatch.setenv(XCRG_RETRIEVER_URL_ENV, "https://example.org/retriever/query")

    assert (
        get_xcrg_retriever_url(SimpleNamespace(maturity="production"))
        == "https://example.org/retriever/query"
    )


def test_xcrg_query_graph_routes_to_connect_xcrg():
    response = _response_with_query_graph(_xcrg_query_graph())

    response = ARAXQueryGraphInterpreter().translate_to_araxi(response)

    assert response.status == "OK"
    assert response.data["araxi_commands"] == ["connect(action=xcrg)"]


def test_non_xcrg_query_graph_does_not_route_to_connect_xcrg():
    query_graph = _xcrg_query_graph()
    query_graph["edges"]["e0"]["predicates"] = ["biolink:related_to"]
    response = _response_with_query_graph(query_graph)

    response = ARAXQueryGraphInterpreter().translate_to_araxi(response)

    assert response.status == "OK"
    assert response.data.get("araxi_commands") != ["connect(action=xcrg)"]


def test_connect_xcrg_calls_package_and_updates_response(monkeypatch):
    query_graph = _xcrg_query_graph()
    response = _response_with_query_graph(query_graph)
    captured = {}

    class MockRTXConfiguration:
        maturity = "testing"
        trapi_version = "1.6.0"

    class MockKPQueryCacher:
        def get_cached_result(self, *_args, **_kwargs):
            return None, -2, 0, None

        def store_response(self, *_args, **_kwargs):
            return None

        def _get_n_results(self, _response_data):
            return 0

    def mock_run_xcrg(query, config, logger):
        captured["query"] = query
        captured["config"] = config
        captured["logger"] = logger
        return _xcrg_response(query_graph)

    monkeypatch.delenv(XCRG_RETRIEVER_URL_ENV, raising=False)
    monkeypatch.setenv("ARAX_XCRG_TIMEOUT", "17")
    monkeypatch.setenv("ARAX_XCRG_TF_BATCH_SIZE", "23")
    monkeypatch.setattr(ARAX_connect, "RTXConfiguration", MockRTXConfiguration)
    monkeypatch.setattr(ARAX_connect, "KPQueryCacher", MockKPQueryCacher)
    monkeypatch.setattr(ARAX_connect, "get_curie_ngd_path", lambda: "sqlite:/tmp/xcrg-ngd.sqlite")
    monkeypatch.setattr(ARAX_connect, "get_curie_to_pmids_path", lambda: "sqlite:/tmp/xcrg-pmids.sqlite")
    monkeypatch.setattr(ARAX_connect, "get_current_arax_biolink_version", lambda: "4.3.2")
    monkeypatch.setattr(ARAX_connect, "run_xcrg", mock_run_xcrg)

    response = ARAXConnect().apply(response, {"action": "xcrg"})

    assert response.status == "OK"
    assert response.data["xcrg_connect"] is True
    assert response.envelope.schema_version == "1.6.0"
    assert response.envelope.biolink_version == "4.3.2"
    assert response.total_results_count == 1
    assert len(response.envelope.message.results) == 1
    assert captured["query"]["message"]["query_graph"]["edges"]["e0"]["knowledge_type"] == "inferred"
    assert captured["config"].retriever_url == "https://retriever.test.transltr.io/query"
    assert captured["config"].ngd_db_path == "/tmp/xcrg-ngd.sqlite"
    assert captured["config"].curie_to_pmids_db_path == "/tmp/xcrg-pmids.sqlite"
    assert captured["config"].timeout == 17
    assert captured["config"].tiers == [0]
    assert captured["config"].tf_batch_size == 23
    xcrg_plan = response.query_plan["qedge_keys"]["e0"]["arax-xcrg"]
    assert xcrg_plan["status"] == "Done"
    assert xcrg_plan["description"].startswith("Returned 1 results in ")
    assert xcrg_plan["query"]["message"]["query_graph"]["edges"]["e0"]["knowledge_type"] == "inferred"


def test_result_transformer_leaves_xcrg_response_unchanged():
    response = _response_with_query_graph(_xcrg_query_graph())
    response.envelope.message = ARAXMessenger().from_dict(_xcrg_response(_xcrg_query_graph())["message"])
    response.data["xcrg_connect"] = True

    ResultTransformer.transform(response)

    assert response.status == "OK"
    assert len(response.envelope.message.results) == 1
