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
from swagger_server.models.query_graph import QueryGraph


def _run_query_and_do_standard_testing(actions_list: List[str], kg_should_be_incomplete=False, debug=False,
                                       should_throw_error=False) -> Tuple[Dict[str, Dict[str, Node]], Dict[str, Dict[str, Edge]]]:
    # Run the query
    araxq = ARAXQuery()
    response = araxq.query({"previous_message_processing_plan": {"processing_actions": actions_list}})
    message = araxq.message
    if response.status != 'OK':
        print(response.show(level=Response.DEBUG))
    assert response.status == 'OK' or should_throw_error

    # Convert output knowledge graph to a dictionary format for faster processing (organized by QG IDs)
    dict_kg = eu.convert_standard_kg_to_dict_kg(message.knowledge_graph)
    nodes_by_qg_id = dict_kg.nodes_by_qg_id
    edges_by_qg_id = dict_kg.edges_by_qg_id

    # Optionally print more detail
    if debug:
        _print_nodes(nodes_by_qg_id)
        _print_edges(edges_by_qg_id)
        _print_counts_by_qgid(nodes_by_qg_id, edges_by_qg_id)
        print(response.show(level=Response.DEBUG))

    # Run standard testing (applies to every test case)
    assert eu.qg_is_fulfilled(message.query_graph, dict_kg) or kg_should_be_incomplete or should_throw_error
    _check_for_orphans(nodes_by_qg_id, edges_by_qg_id)
    _check_property_format(nodes_by_qg_id, edges_by_qg_id)
    _check_node_types(message.knowledge_graph.nodes, message.query_graph)
    if not any(action for action in actions_list if "synonym_handling=add_all" in action):
        _check_counts_of_curie_qnodes(nodes_by_qg_id, message.query_graph)

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
    node_counts_by_prefix = dict()
    for qnode_id, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            prefix = node.id.split(':')[0]
            if prefix in node_counts_by_prefix.keys():
                node_counts_by_prefix[prefix] += 1
            else:
                node_counts_by_prefix[prefix] = 1
    print(node_counts_by_prefix)


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


def _check_property_format(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qnode_id, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            assert node.id and isinstance(node.id, str)
            assert isinstance(node.name, str) or node.name is None
            assert node.qnode_ids and isinstance(node.qnode_ids, list)
            assert node.type and isinstance(node.type, list)
    for qedge_id, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge.id and isinstance(edge.id, str)
            assert edge.qedge_ids and isinstance(edge.qedge_ids, list)
            assert edge.type and isinstance(edge.type, str)
            assert edge.source_id and isinstance(edge.source_id, str)
            assert edge.target_id and isinstance(edge.target_id, str)
            assert isinstance(edge.provided_by, str) or isinstance(edge.provided_by, list)
            assert edge.is_defined_by and isinstance(edge.is_defined_by, str)


def _check_node_types(nodes: List[Node], query_graph: QueryGraph):
    qnode_id_to_type_map = {qnode.id: qnode.type for qnode in query_graph.nodes}
    for node in nodes:
        for qnode_id in node.qnode_ids:
            corresponding_qnode_type = qnode_id_to_type_map.get(qnode_id)
            if corresponding_qnode_type:
                assert corresponding_qnode_type in node.type  # Could have additional types if it has multiple qnode ids


def _check_counts_of_curie_qnodes(nodes_by_qg_id: Dict[str, Dict[str, Node]], query_graph: QueryGraph):
    qnodes_with_single_curie = [qnode for qnode in query_graph.nodes if qnode.curie and isinstance(qnode.curie, str)]
    for qnode in qnodes_with_single_curie:
        if qnode.id in nodes_by_qg_id:
            assert len(nodes_by_qg_id[qnode.id]) == 1
    qnodes_with_curie_list = [qnode for qnode in query_graph.nodes if qnode.curie and isinstance(qnode.curie, list)]
    for qnode in qnodes_with_curie_list:
        if qnode.id in nodes_by_qg_id:
            assert 1 <= len(nodes_by_qg_id[qnode.id]) <= len(qnode.curie)


def test_erics_first_kg1_synonym_test_without_synonyms():
    actions_list = [
        "add_qnode(curie=REACT:R-HSA-2160456, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_erics_first_kg1_synonym_test_with_synonyms():
    actions_list = [
        "add_qnode(curie=REACT:R-HSA-2160456, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) > 20


def test_acetaminophen_example_enforcing_directionality():
    actions_list = [
        "add_qnode(curie=CHEMBL.COMPOUND:CHEMBL112, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, use_synonyms=false, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    for edge_id, edge in edges_by_qg_id['e00'].items():
        assert edge.source_id in nodes_by_qg_id['n00']
        assert edge.target_id in nodes_by_qg_id['n01']


@pytest.mark.slow
def test_720_ambitious_query_causing_multiple_qnode_ids_error():
    actions_list = [
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=disease, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00, e01], use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert set(nodes_by_qg_id['n00']).intersection(set(nodes_by_qg_id['n02']))


@pytest.mark.slow
def test_720_multiple_qg_ids_in_different_results():
    actions_list = [
        "add_qnode(id=n00, curie=DOID:14330)",
        "add_qnode(id=n01, type=protein)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qnode(id=n03, type=protein, curie=UniProtKB:P37840)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "add_qedge(id=e02, source_id=n02, target_id=n03)",
        "expand(use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    snca_id = "UniProtKB:P37840"
    assert snca_id in nodes_by_qg_id['n01'] and snca_id in nodes_by_qg_id['n03']
    assert set(nodes_by_qg_id['n01'][snca_id].qnode_ids) == {'n01', 'n03'}
    e01_edges_using_snca = {edge.id for edge in edges_by_qg_id['e01'].values() if edge.source_id == snca_id or edge.target_id == snca_id}
    e02_edges_using_snca = {edge.id for edge in edges_by_qg_id['e02'].values() if edge.source_id == snca_id or edge.target_id == snca_id}
    assert e01_edges_using_snca == e02_edges_using_snca


@pytest.mark.slow
def test_bte_simple_acetaminophen_query():
    actions_list = [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112, type=chemical_substance)",
        "add_qnode(id=n01, type=disease)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_bte_add_all_query():
    actions_list = [
        "add_qnode(curie=UniProtKB:P16471, type=protein, id=n00)",
        "add_qnode(type=cell, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=BTE, synonym_handling=add_all)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_bte_map_back_query():
    actions_list = [
        "add_qnode(curie=UniProtKB:P16471, type=protein, id=n00)",
        "add_qnode(type=cell, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_bte_using_list_of_curies():
    actions_list = [
        "add_qnode(id=n00, curie=[CHEMBL.COMPOUND:CHEMBL112, CHEMBL.COMPOUND:CHEMBL521], type=chemical_substance)",
        "add_qnode(id=n01, type=disease)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_single_node_query_map_back():
    actions_list = [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_id=n00, kp=ARAX/KG1, synonym_handling=map_back)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_add_all():
    actions_list = [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL2220442)",
        "expand(node_id=n00, kp=ARAX/KG1, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_single_node_query_without_synonyms():
    actions_list = [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1276308)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_no_results():
    actions_list = [
        "add_qnode(id=n00, curie=FAKE:curie)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_single_node_query_with_list():
    actions_list = [
        "add_qnode(id=n00, curie=[CHEMBL.COMPOUND:CHEMBL108, CHEMBL.COMPOUND:CHEMBL110])",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 2


@pytest.mark.slow
def test_query_that_returns_multiple_provided_bys():
    actions_list = [
        "add_qnode(curie=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_three_hop_query():
    actions_list = [
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


@pytest.mark.slow
def test_branched_query():
    actions_list = [
        "add_qnode(id=n00, curie=DOID:0060227)",  # Adams-Oliver
        "add_qnode(id=n01, type=phenotypic_feature, is_set=true)",
        "add_qnode(id=n02, type=disease)",
        "add_qnode(id=n03, type=protein, is_set=true)",
        "add_qedge(source_id=n01, target_id=n00, id=e00)",
        "add_qedge(source_id=n02, target_id=n00, id=e01)",
        "add_qedge(source_id=n00, target_id=n03, id=e02)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_add_all_query_with_multiple_synonyms_in_results():
    actions_list = [
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1464)",  # warfarin
        "add_qnode(id=n01, type=disease)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_query_that_expands_same_edge_twice():
    actions_list = [
        "add_qnode(id=n00, curie=DOID:9065)",
        "add_qnode(id=n01, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "expand(kp=ARAX/KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert any(edge for edge in edges_by_qg_id['e00'].values() if edge.is_defined_by == "ARAX/KG1")
    assert any(edge for edge in edges_by_qg_id['e00'].values() if edge.is_defined_by == "ARAX/KG2")


def test_771_continue_if_no_results_query():
    actions_list = [
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


@pytest.mark.slow
def test_774_continue_if_no_results_query():
    actions_list = [
        "add_qnode(curie=CHEMBL.COMPOUND:CHEMBL112, id=n1)",
        "add_qnode(curie=DOID:8295, id=n2)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=e1, kp=ARAX/KG2, continue_if_no_results=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_curie_list_query_map_back():
    actions_list = [
        "add_qnode(curie=[DOID:6419, DOID:3717, DOID:11406], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_curie_list_query_add_all():
    actions_list = [
        "add_qnode(curie=[DOID:6419, DOID:3717, DOID:11406], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG1, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 4


def test_curie_list_query_without_synonyms():
    actions_list = [
        "add_qnode(curie=[DOID:6419, DOID:3717, DOID:11406], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_curies_on_both_ends():
    actions_list = [
        "add_qnode(curie=CHV:0000003834, id=n00)",  # diabetes
        "add_qnode(curie=HP:0001993, id=n01)",  # ketoacidosis
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_intermediate_curie_node():
    actions_list = [
        "add_qnode(type=protein, id=n00)",
        "add_qnode(curie=HP:0005110, id=n01)",  # atrial fibrillation
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_847_dont_expand_curie_less_edge():
    actions_list = [
        "add_qnode(id=n00, type=protein)",
        "add_qnode(id=n01, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, should_throw_error=True)


@pytest.mark.slow
def test_deduplication_and_self_edges():
    actions_list = [
        "add_qnode(curie=CUI:C0004572, id=n00)",  # Babesia
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    # Check that deduplication worked appropriately
    all_node_ids = {node.id for nodes in nodes_by_qg_id.values() for node in nodes.values()}
    babesia_curies = {"CUI:C0004572", "CHV:0000001647", "LNC:LP19999-9", "MEDDRA:10003963", "MESH:D001403",
                      "NCIT:C122040", "NCI_CDISC:C122040", "SNOMEDCT:35029001"}
    babesia_curies_in_answer = all_node_ids.intersection(babesia_curies)
    assert len(babesia_curies_in_answer) <= 1
    # Check that we don't have any self-edges
    self_edges = [edge for edge in edges_by_qg_id['e00'].values() if edge.source_id == edge.target_id]
    assert not self_edges


@pytest.mark.slow
def test_889_missing_curies():
    actions_list = [
        "add_qnode(name=DOID:11830, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n02']) > 30


@pytest.mark.slow
def test_873_consider_both_gene_and_protein():
    actions_list_protein = [
        "add_qnode(curie=DOID:9452, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_protein, edges_by_qg_id_protein = _run_query_and_do_standard_testing(actions_list_protein)
    actions_list_gene = [
        "add_qnode(curie=DOID:9452, id=n00)",
        "add_qnode(type=gene, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_gene, edges_by_qg_id_gene = _run_query_and_do_standard_testing(actions_list_gene)
    assert set(nodes_by_qg_id_protein['n01']) == set(nodes_by_qg_id_gene['n01'])


def test_987_override_node_types():
    actions_list = [
        "add_qnode(name=DOID:8398, id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, type=has_phenotype, id=e00)",
        "expand(edge_id=e00)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all('phenotypic_feature' in node.type for node in nodes_by_qg_id['n01'].values())

@pytest.mark.slow
def test_COHD_expand_paired_concept_freq():
    actions_list = [
        "add_qnode(curie=UMLS:C0015967, id=n00)",
        "add_qnode(type=chemical_substance, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=COHD, COHD_method=paired_concept_freq, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_id][edge_id].type == "has_paired_concept_frequency_with" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.name == "paired_concept_frequency" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.type == "EDAM:data_0951" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.url == "http://cohd.smart-api.info/" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])

def test_COHD_expand_observed_expected_ratio():
    actions_list = [
        "add_qnode(curie=DOID:10718, id=n00)",
        "add_qnode(type=chemical_substance, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=COHD, COHD_method=observed_expected_ratio, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_id][edge_id].type == "has_ln_observed_expected_ratio_with" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.name == "ln_observed_expected_ratio" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.type == "EDAM:data_0951" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.url == "http://cohd.smart-api.info/" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])

def test_COHD_expand_chi_square():
    actions_list = [
        "add_qnode(curie=DOID:5844, id=n00)",
        "add_qnode(type=chemical_substance, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=COHD, COHD_method=chi_square, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_id][edge_id].type == "has_chi_square_pvalue_with" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.name == "chi_square_pvalue" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.type == "EDAM:data_0951" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])
    assert all([edges_by_qg_id[qedge_id][edge_id].edge_attributes.url == "http://cohd.smart-api.info/" for qedge_id in edges_by_qg_id for edge_id in edges_by_qg_id[qedge_id]])


def test_ngd_expand():
    actions_list = [
        "add_qnode(name=DOID:8398, id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, type=has_phenotype, id=e00)",
        "expand(kp=NGD)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_expand.py'])
