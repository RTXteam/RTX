#!/bin/env python3
"""
Usage:
    Run all expand tests: pytest -v test_ARAX_expand.py
    Run a single test: pytest -v test_ARAX_expand.py -k test_branched_query
"""

import sys
import os
from typing import List, Dict, Tuple

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/")
from ARAX_query import ARAXQuery
from response import Response
import Expand.expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node


def _run_query_and_do_standard_testing(actions_list: List[str], kg_should_be_incomplete=False, debug=False) -> \
        Tuple[Dict[str, Dict[str, Node]], Dict[str, Dict[str, Edge]]]:
    # Run the query
    araxq = ARAXQuery()
    response = araxq.query({"previous_message_processing_plan": {"processing_actions": actions_list}})
    message = araxq.message
    if response.status != 'OK':
        print(response.show(level=Response.DEBUG))
    assert response.status == 'OK'

    # Convert output knowledge graph to a dictionary format for faster processing (organized by QG IDs)
    dict_kg = eu.convert_standard_kg_to_dict_kg(message.knowledge_graph)
    nodes_by_qg_id = dict_kg['nodes']
    edges_by_qg_id = dict_kg['edges']

    # Optionally print more detail
    if debug:
        _print_nodes(nodes_by_qg_id)
        _print_edges(edges_by_qg_id)
        _print_counts_by_qgid(nodes_by_qg_id, edges_by_qg_id)
        print(response.show(level=Response.DEBUG))

    # Run standard testing (applies to every test case)
    assert eu.qg_is_fulfilled(message.query_graph, dict_kg) or kg_should_be_incomplete
    _check_for_orphans(nodes_by_qg_id, edges_by_qg_id)
    _check_property_types(nodes_by_qg_id, edges_by_qg_id)

    return nodes_by_qg_id, edges_by_qg_id


def _print_counts_by_qgid(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    print(f"KG counts:")
    if nodes_by_qg_id or edges_by_qg_id:
        for qnode_id, corresponding_nodes in sorted(nodes_by_qg_id.items()):
            print(f"  {qnode_id}: {len(corresponding_nodes)}")
        for qedge_id, corresponding_edges in sorted(edges_by_qg_id.items()):
            print(f"  {qedge_id}: {len(corresponding_edges)}")
    else:
        print("  KG is empty")


def _print_nodes(nodes_by_qg_id: Dict[str, Dict[str, Node]]):
    for qnode_id, nodes in sorted(nodes_by_qg_id.items()):
        for node_key, node in sorted(nodes.items()):
            print(f"{qnode_id}: {node.type}, {node.id}, {node.name}, {node.qnode_ids}")


def _print_edges(edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qedge_id, edges in sorted(edges_by_qg_id.items()):
        for edge_key, edge in sorted(edges.items()):
            print(f"{qedge_id}: {edge.id}, {edge.source_id}--{edge.type}->{edge.target_id}, {edge.qedge_ids}")


def _print_node_counts_by_prefix(nodes_by_qg_id: Dict[str, Dict[str, Node]]):
    nodes_by_prefix = dict()
    for qnode_id, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            prefix = node.id.split(':')[0]
            if prefix in nodes_by_prefix.keys():
                nodes_by_prefix[prefix] += 1
            else:
                nodes_by_prefix[prefix] = 1
    print(nodes_by_prefix)


def _check_for_orphans(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    node_ids = set()
    node_ids_used_by_edges = set()
    for qnode_id, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            node_ids.add(node_key)
    for qedge_id, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            node_ids_used_by_edges.add(edge.source_id)
            node_ids_used_by_edges.add(edge.target_id)
    assert node_ids == node_ids_used_by_edges or len(node_ids_used_by_edges) == 0


def _check_property_types(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qnode_id, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            assert type(node.qnode_ids) is list
    for qedge_id, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert type(edge.qedge_ids) is list


def test_kg1_parkinsons_demo_example():
    print("Testing KG1 parkinson's demo example")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(nodes_by_qg_id['n00']) == 1

    # Make sure all e00 edges map to Parkinson's curie for n00
    for edge_id, edge in edges_by_qg_id['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in nodes_by_qg_id['n02'].items():
        assert "chemical_substance" in node.type

    # Make sure drugs include cilnidipine
    assert any(node.name.lower() == 'cilnidipine' for node in nodes_by_qg_id['n02'].values())

    # Make sure there are four proteins connecting to cilnidipine
    proteins_connected_to_cilnidipine = set()
    for edge_id, edge in edges_by_qg_id['e01'].items():
        if edge.source_id == "CHEMBL.COMPOUND:CHEMBL452076" or edge.target_id == "CHEMBL.COMPOUND:CHEMBL452076":
            non_cilnidipine_node = edge.source_id if edge.source_id != "CHEMBL.COMPOUND:CHEMBL452076" else edge.target_id
            proteins_connected_to_cilnidipine.add(non_cilnidipine_node)
    assert(len(proteins_connected_to_cilnidipine) >= 4)


def test_kg2_parkinsons_demo_example():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2, enforce_directionality=true, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(nodes_by_qg_id['n00']) == 1

    # Make sure all e00 edges map to Parkinson's curie for n00
    for edge_id, edge in edges_by_qg_id['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in nodes_by_qg_id['n02'].items():
        assert "chemical_substance" in node.type

    # Make sure drugs include cilnidipine
    assert any(node.name.lower() == 'cilnidipine' for node in nodes_by_qg_id['n02'].values())

    # Make sure there are four proteins connecting to cilnidipine
    proteins_connected_to_cilnidipine = set()
    for edge_id, edge in edges_by_qg_id['e01'].items():
        if edge.source_id == "CHEMBL.COMPOUND:CHEMBL452076" or edge.target_id == "CHEMBL.COMPOUND:CHEMBL452076":
            non_cilnidipine_node = edge.source_id if edge.source_id != "CHEMBL.COMPOUND:CHEMBL452076" else edge.target_id
            proteins_connected_to_cilnidipine.add(non_cilnidipine_node)
    assert(len(proteins_connected_to_cilnidipine) >= 4)

    assert len(nodes_by_qg_id['n00']) == 1
    assert len(nodes_by_qg_id['n01']) == 18
    assert len(nodes_by_qg_id['n02']) == 1119
    assert len(edges_by_qg_id['e00']) == 18
    assert len(edges_by_qg_id['e01']) == 1871


def test_kg2_synonym_map_back_parkinsons_proteins():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    # Make sure all edges have been remapped to original curie for n00
    for edge_key, edge in edges_by_qg_id['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure only one node exists for n00 (the original curie)
    assert len(nodes_by_qg_id['n00']) == 1

    # Take a look at the proteins returned, make sure they're all proteins
    for node_key, node in nodes_by_qg_id['n01'].items():
        assert "protein" in node.type


def test_kg2_synonym_map_back_parkinsons_full_example():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(nodes_by_qg_id['n00']) == 1

    # Make sure all e00 edges have been remapped to original curie for n00
    for edge_id, edge in edges_by_qg_id['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in nodes_by_qg_id['n02'].items():
        assert "chemical_substance" in node.type


def test_kg2_synonym_add_all_parkinsons_full_example():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    # Make sure all drugs returned are as expected
    for node_id, node in nodes_by_qg_id['n02'].items():
        assert "chemical_substance" in node.type


def test_demo_example_1_simple():
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n0)",
        "add_qnode(type=protein, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n0']) >= 1
    assert len(nodes_by_qg_id['n1']) >= 32
    assert len(edges_by_qg_id['e0']) >= 64


def test_demo_example_2_simple():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) >= 1
    assert len(nodes_by_qg_id['n01']) >= 18
    assert len(nodes_by_qg_id['n02']) >= 1119
    assert len(edges_by_qg_id['e00']) >= 18
    assert len(edges_by_qg_id['e01']) >= 1871


def test_demo_example_3_simple():
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01], use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) >= 1
    assert len(nodes_by_qg_id['n01']) >= 29
    assert len(nodes_by_qg_id['n02']) >= 240
    assert len(edges_by_qg_id['e00']) >= 29
    assert len(edges_by_qg_id['e01']) >= 1368


def test_demo_example_1_with_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n0)",
        "add_qnode(type=protein, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n0']) >= 1
    assert len(nodes_by_qg_id['n1']) >= 32
    assert len(edges_by_qg_id['e0']) >= 64


def test_demo_example_2_with_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) >= 1
    assert len(nodes_by_qg_id['n01']) >= 18
    assert len(nodes_by_qg_id['n02']) >= 1119
    assert len(edges_by_qg_id['e00']) >= 18
    assert len(edges_by_qg_id['e01']) >= 1871


def test_demo_example_3_with_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01])",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) >= 1
    assert len(nodes_by_qg_id['n01']) >= 29
    assert len(nodes_by_qg_id['n02']) >= 240
    assert len(edges_by_qg_id['e00']) >= 29
    assert len(edges_by_qg_id['e01']) >= 1368


def test_erics_first_kg1_synonym_test_without_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(name=PHENYLKETONURIA, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_erics_first_kg1_synonym_test_with_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(name=PHENYLKETONURIA, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) > 20


def test_acetaminophen_example_enforcing_directionality():
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, use_synonyms=false, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) == 1
    assert len(nodes_by_qg_id['n01']) == 32
    assert len(edges_by_qg_id['e00']) == 32

    # Make sure the source of every node is acetaminophen
    for node_id in nodes_by_qg_id['n00'].keys():
        assert node_id == "CHEMBL.COMPOUND:CHEMBL112"


def test_parkinsons_example_enforcing_directionality():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    assert len(nodes_by_qg_id['n00']) == 1
    assert len(nodes_by_qg_id['n01']) == 18
    assert len(nodes_by_qg_id['n02']) == 1119
    assert len(edges_by_qg_id['e00']) == 18
    assert len(edges_by_qg_id['e01']) == 1871


def test_ambitious_query_causing_multiple_qnode_ids_error_720():
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(is_set=true, id=n01)",
        "add_qnode(type=disease, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00, e01])",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_kg1_property_format():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    for qnode_id, nodes in nodes_by_qg_id.items():
        for node in nodes.values():
            assert type(node.name) is str
            assert type(node.id) is str
            assert ":" in node.id
            assert type(node.qnode_ids) is list
            assert type(node.type) is list
            assert type(node.uri) is str

    for qedge_id, edges in edges_by_qg_id.items():
        for edge in edges.values():
            assert type(edge.id) is str
            assert type(edge.is_defined_by) is str
            assert type(edge.provided_by) is str
            assert type(edge.qedge_ids) is list
            assert type(edge.type) is str
            if "chembl" in edge.provided_by.lower():
                assert edge.edge_attributes[0].name == "probability"


def test_simple_bte_acetaminophen_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112, type=chemical_substance)",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1
    assert len(nodes_by_qg_id['n01']) == len(edges_by_qg_id['e00'])


def test_add_all_bte_acetaminophen_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE, synonym_handling=add_all)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_bte_parkinsons_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1


def test_bte_query_using_list_of_curies():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=[CHEMBL.COMPOUND:CHEMBL112, CHEMBL.COMPOUND:CHEMBL521])",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_simple_bte_cdk2_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=NCBIGene:1017, type=gene)",
        "add_qnode(id=n01, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1


def test_simple_bidirectional_query_727():
    actions_list = [
        "create_message",
        "add_qnode(name=CHEMBL.COMPOUND:CHEMBL1276308, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_query_that_doesnt_return_original_curie_731():
    actions_list = [
        "create_message",
        "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=[e0,e1], kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n0']) == 1
    assert "MONDO:0005737" in nodes_by_qg_id['n0']

    for edge in edges_by_qg_id['e0'].values():
        assert edge.source_id == "MONDO:0005737" or edge.target_id == "MONDO:0005737"


def test_single_node_query_map_back():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_id=n00, kp=ARAX/KG2, synonym_handling=map_back)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1
    assert nodes_by_qg_id['n00'].get("CHEMBL.COMPOUND:CHEMBL1771")


def test_single_node_query_add_all():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_id=n00, kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1
    assert "CHEMBL.COMPOUND:CHEMBL1771" in nodes_by_qg_id['n00']


def test_single_node_query_without_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1276308)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1
    assert "CHEMBL.COMPOUND:CHEMBL1276308" in nodes_by_qg_id['n00']


def test_query_with_no_edge_or_node_ids():
    actions_list = [
        "create_message",
        "add_qnode(name=CHEMBL.COMPOUND:CHEMBL1276308, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_query_that_produces_multiple_provided_bys():
    actions_list = [
        "create_message",
        "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_babesia_query_producing_self_edges_742():
    actions_list = [
        "create_message",
        "add_qnode(name=babesia, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_three_hop_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:8454)",
        "add_qnode(id=n01, type=phenotypic_feature)",
        "add_qnode(id=n02, type=protein)",
        "add_qnode(id=n03, type=anatomical_entity)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "add_qedge(source_id=n02, target_id=n03, id=e02)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_branched_query():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:0060227)",  # Adams-Oliver
        "add_qnode(id=n01, type=phenotypic_feature, is_set=true)",
        "add_qnode(id=n02, type=disease)",
        "add_qnode(id=n03, type=protein, is_set=true)",
        "add_qedge(source_id=n01, target_id=n00, id=e00)",
        "add_qedge(source_id=n02, target_id=n00, id=e01)",
        "add_qedge(source_id=n00, target_id=n03, id=e02)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_add_all_query_with_multiple_synonyms_in_results():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, name=warfarin)",
        "add_qnode(id=n01, type=disease)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_query_that_expands_same_edge_twice():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521)",  # ibuprofen
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "expand(kp=ARAX/KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert any(edge for edge in edges_by_qg_id['e00'].values() if edge.is_defined_by == "ARAX/KG1")
    assert any(edge for edge in edges_by_qg_id['e00'].values() if edge.is_defined_by == "ARAX/KG2")


def test_query_using_continue_if_no_results_771():
    actions_list = [
        "create_message",
        "add_qnode(curie=UniProtKB:P14136, id=n00)",
        "add_qnode(type=biological_process, id=n01)",
        "add_qnode(curie=UniProtKB:P35579, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n02, target_id=n01, id=e01)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert 'n02' not in nodes_by_qg_id
    assert 'e01' not in edges_by_qg_id


def test_query_using_list_of_curies_map_back_handling():
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert 1 < len(nodes_by_qg_id['n00']) <= 4
    n00_node_ids = set(nodes_by_qg_id['n00'].keys())
    assert n00_node_ids.issubset({"CUI:C0024530", "CUI:C0024535", "CUI:C0024534", "CUI:C0747820"})


def test_query_using_list_of_curies_add_all_handling():
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 4


def test_query_using_list_of_curies_without_synonyms():
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert 1 < len(nodes_by_qg_id['n00']) <= 4
    n00_node_ids = set(nodes_by_qg_id['n00'].keys())
    assert n00_node_ids.issubset({"CUI:C0024530", "CUI:C0024535", "CUI:C0024534", "CUI:C0747820"})


def test_query_with_curies_on_both_ends():
    actions_list = [
        "create_message",
        "add_qnode(name=diabetes, id=n00)",
        "add_qnode(name=ketoacidosis, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 1 and len(nodes_by_qg_id['n01']) == 1


def test_query_with_intermediate_curie_node():
    actions_list = [
        "create_message",
        "add_qnode(type=protein, id=n00)",
        "add_qnode(name=atrial fibrillation, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) == 1


def test_continue_if_no_results_query_causing_774():
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n1)",
        "add_qnode(name=scabies, id=n2)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=e1, kp=ARAX/KG2, continue_if_no_results=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_multiple_qg_ids_test_for_720():
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",
        "add_qnode(id=n01, type=protein)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qnode(id=n03, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "add_qedge(id=e02, source_id=n02, target_id=n03)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    snca_id = "UniProtKB:P37840"
    assert snca_id in nodes_by_qg_id['n01'] and snca_id in nodes_by_qg_id['n03']
    assert set(nodes_by_qg_id['n01'][snca_id].qnode_ids) == {'n01', 'n03'}
    e01_edges_using_snca = {edge.id for edge in edges_by_qg_id['e01'].values() if edge.source_id == snca_id or edge.target_id == snca_id}
    e02_edges_using_snca = {edge.id for edge in edges_by_qg_id['e02'].values() if edge.source_id == snca_id or edge.target_id == snca_id}
    assert e01_edges_using_snca == e02_edges_using_snca


def test_curie_list_issue_623_1():
    actions_list = [
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=e01, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_curie_list_issue_623_2():
    actions_list = [
        "add_qnode(curie=[UniProtKB:P02675,UniProtKB:P01903,UniProtKB:P09601,UniProtKB:Q02878,UniProtKB:P01375,"
        "UniProtKB:Q9BXM7,UniProtKB:P05181,UniProtKB:I3WAC9,UniProtKB:P50914,UniProtKB:P62241,UniProtKB:O15217,"
        "UniProtKB:P09488,UniProtKB:P15559,UniProtKB:P06213,UniProtKB:Q13330,UniProtKB:P38646,UniProtKB:P05231,"
        "UniProtKB:Q9BRL8,UniProtKB:P01344,UniProtKB:Q99683,UniProtKB:P11717,UniProtKB:P01308,UniProtKB:P10635,"
        "UniProtKB:P23560,UniProtKB:Q01959,UniProtKB:P21728,UniProtKB:O60260,UniProtKB:Q9NQ11,UniProtKB:P21397,"
        "UniProtKB:P10636,UniProtKB:P08183,UniProtKB:P09211,UniProtKB:P04062,UniProtKB:P14416,UniProtKB:Q5S007,"
        "UniProtKB:Q99497,UniProtKB:P27338,UniProtKB:P37840,UniProtKB:P08069], is_set=true, id=n00)",
        "add_qnode(type=chemical_substance, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00, type=physically_interacts_with)",
        "expand(edge_id=e00,kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_curie_list_issue_623_3():
    actions_list = [
        "add_qnode(curie=[UniProtKB:P02675, UniProtKB:P01903, UniProtKB:P09601, UniProtKB:Q02878, UniProtKB:P01375, "
        "UniProtKB:Q9BXM7, UniProtKB:P05181, UniProtKB:I3WAC9, UniProtKB:P50914, UniProtKB:P62241, UniProtKB:O15217, "
        "UniProtKB:P09488, UniProtKB:P15559, UniProtKB:P06213, UniProtKB:Q13330, UniProtKB:P38646, UniProtKB:P05231, "
        "UniProtKB:Q9BRL8, UniProtKB:P01344, UniProtKB:Q99683, UniProtKB:P11717, UniProtKB:P01308, UniProtKB:P10635, "
        "UniProtKB:P23560, UniProtKB:Q01959, UniProtKB:P21728, UniProtKB:O60260, UniProtKB:Q9NQ11, UniProtKB:P21397, "
        "UniProtKB:P10636, UniProtKB:P08183, UniProtKB:P09211, UniProtKB:P04062, UniProtKB:P14416, UniProtKB:Q5S007, "
        "UniProtKB:Q99497, UniProtKB:P27338, UniProtKB:P37840, UniProtKB:P08069], is_set=true, id=n00)",
        "add_qnode(type=disease, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    missing_protein = "UniProtKB:Q13330"
    assert missing_protein in nodes_by_qg_id['n00']
    edges_using_protein = [edge.id for edge in edges_by_qg_id['e00'].values() if edge.source_id == missing_protein or edge.target_id == missing_protein]
    assert len(edges_using_protein) == 3


if __name__ == "__main__":
    pytest.main(['-v'])
