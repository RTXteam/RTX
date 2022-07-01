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
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.attribute import Attribute


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
        _print_nodes(nodes_by_qg_id)
        _print_edges(edges_by_qg_id)
        _print_counts_by_qgid(nodes_by_qg_id, edges_by_qg_id)
        print(response.show(level=ARAXResponse.DEBUG))

    # Run standard testing (applies to every test case)
    assert eu.qg_is_fulfilled(message.query_graph, dict_kg, enforce_required_only=True) or kg_should_be_incomplete or should_throw_error
    _check_for_orphans(nodes_by_qg_id, edges_by_qg_id)
    _check_property_format(nodes_by_qg_id, edges_by_qg_id)
    _check_node_categories(message.knowledge_graph.nodes, message.query_graph)

    return nodes_by_qg_id, edges_by_qg_id, response


def _print_counts_by_qgid(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    print(f"KG counts:")
    if nodes_by_qg_id or edges_by_qg_id:
        for qnode_key, corresponding_nodes in sorted(nodes_by_qg_id.items()):
            print(f"  {qnode_key}: {len(corresponding_nodes)}")
        for qedge_key, corresponding_edges in sorted(edges_by_qg_id.items()):
            print(f"  {qedge_key}: {len(corresponding_edges)}")
    else:
        print("  KG is empty")


def _print_nodes(nodes_by_qg_id: Dict[str, Dict[str, Node]]):
    for qnode_key, nodes in sorted(nodes_by_qg_id.items()):
        for node_key, node in sorted(nodes.items()):
            print(f"{qnode_key}: {node.categories}, {node_key}, {node.name}, {node.qnode_keys}")


def _print_edges(edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qedge_key, edges in sorted(edges_by_qg_id.items()):
        for edge_key, edge in sorted(edges.items()):
            print(f"{qedge_key}: {edge_key}, {edge.subject}--{edge.predicate}->{edge.object}, {edge.qedge_keys}")


def _print_node_counts_by_prefix(nodes_by_qg_id: Dict[str, Dict[str, Node]]):
    node_counts_by_prefix = dict()
    for qnode_key, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            prefix = node_key.split(':')[0]
            if prefix in node_counts_by_prefix.keys():
                node_counts_by_prefix[prefix] += 1
            else:
                node_counts_by_prefix[prefix] = 1
    print(node_counts_by_prefix)


def _check_for_orphans(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    node_keys = set()
    node_keys_used_by_edges = set()
    for qnode_key, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            node_keys.add(node_key)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            node_keys_used_by_edges.add(edge.subject)
            node_keys_used_by_edges.add(edge.object)
    assert node_keys == node_keys_used_by_edges or len(node_keys_used_by_edges) == 0


def _check_property_format(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qnode_key, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            assert node_key and isinstance(node_key, str)
            assert node.qnode_keys and isinstance(node.qnode_keys, list)
            assert isinstance(node.name, str) or node.name is None
            assert isinstance(node.categories, list) or node.categories is None
            if node.attributes:
                for attribute in node.attributes:
                    _check_attribute(attribute)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge_key and isinstance(edge_key, str)
            assert edge.qedge_keys and isinstance(edge.qedge_keys, list)
            assert edge.subject and isinstance(edge.subject, str)
            assert edge.object and isinstance(edge.object, str)
            assert isinstance(edge.predicate, str) or edge.predicate is None
            if edge.attributes:
                for attribute in edge.attributes:
                    _check_attribute(attribute)


def _check_attribute(attribute: Attribute):
    assert attribute.attribute_type_id and isinstance(attribute.attribute_type_id, str)
    assert attribute.value is not None and (isinstance(attribute.value, str) or isinstance(attribute.value, list) or
                                            isinstance(attribute.value, int) or isinstance(attribute.value, float) or
                                            isinstance(attribute.value, dict))
    assert isinstance(attribute.value_type_id, str) or attribute.value_type_id is None
    assert isinstance(attribute.value_url, str) or attribute.value_url is None
    assert isinstance(attribute.attribute_source, str) or attribute.attribute_source is None
    assert isinstance(attribute.original_attribute_name, str) or attribute.original_attribute_name is None
    assert isinstance(attribute.description, str) or attribute.description is None


def _check_node_categories(nodes: Dict[str, Node], query_graph: QueryGraph):
    for node in nodes.values():
        for qnode_key in node.qnode_keys:
            qnode = query_graph.nodes[qnode_key]
            if qnode.categories:
                assert set(qnode.categories).issubset(set(node.categories))  # Could have additional categories if it has multiple qnode keys


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
    assert 'biolink:has_normalized_google_distance_with' in qg.edges['N1'].predicates


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


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_json_queries.py'])




