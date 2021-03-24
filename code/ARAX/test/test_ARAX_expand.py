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
from ARAX_response import ARAXResponse
import Expand.expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.query_graph import QueryGraph


def _run_query_and_do_standard_testing(actions_list: List[str], kg_should_be_incomplete=False, debug=False,
                                       should_throw_error=False) -> Tuple[Dict[str, Dict[str, Node]], Dict[str, Dict[str, Edge]]]:
    # Run the query
    araxq = ARAXQuery()
    response = araxq.query({"operations": {"actions": actions_list}})
    message = araxq.message
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
    assert response.status == 'OK' or should_throw_error

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
    _check_counts_of_curie_qnodes(nodes_by_qg_id, message.query_graph)

    return nodes_by_qg_id, edges_by_qg_id


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
            print(f"{qnode_key}: {node.category}, {node_key}, {node.name}, {node.qnode_keys}")


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
            assert isinstance(node.name, str) or node.name is None
            assert node.qnode_keys and isinstance(node.qnode_keys, list)
            assert node.category and isinstance(node.category, list)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge_key and isinstance(edge_key, str)
            assert edge.qedge_keys and isinstance(edge.qedge_keys, list)
            assert edge.subject and isinstance(edge.subject, str)
            assert edge.object and isinstance(edge.object, str)


def _check_node_categories(nodes: Dict[str, Node], query_graph: QueryGraph):
    for node in nodes.values():
        for qnode_key in node.qnode_keys:
            qnode = query_graph.nodes[qnode_key]
            if qnode.category:
                assert qnode.category in node.category  # Could have additional categories if it has multiple qnode keys


def _check_counts_of_curie_qnodes(nodes_by_qg_id: Dict[str, Dict[str, Node]], query_graph: QueryGraph):
    qnodes_with_single_curie = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.id and isinstance(qnode.id, str)]
    for qnode_key in qnodes_with_single_curie:
        if qnode_key in nodes_by_qg_id:
            assert len(nodes_by_qg_id[qnode_key]) == 1
    qnodes_with_multiple_curies = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.id and isinstance(qnode.id, list)]
    for qnode_key in qnodes_with_multiple_curies:
        qnode = query_graph.nodes[qnode_key]
        if qnode_key in nodes_by_qg_id:
            assert 1 <= len(nodes_by_qg_id[qnode_key]) <= len(qnode.id)


def test_erics_first_kg1_synonym_test_without_synonyms():
    actions_list = [
        "add_qnode(id=REACT:R-HSA-2160456, key=n00)",
        "add_qnode(key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_erics_first_kg1_synonym_test_with_synonyms():
    actions_list = [
        "add_qnode(id=REACT:R-HSA-2160456, key=n00)",
        "add_qnode(key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) > 20


def test_acetaminophen_example_enforcing_directionality():
    actions_list = [
        "add_qnode(id=CHEMBL.COMPOUND:CHEMBL112, key=n00)",
        "add_qnode(category=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG1, edge_key=e00, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    for edge_key, edge in edges_by_qg_id['e00'].items():
        assert edge.subject in nodes_by_qg_id['n00']
        assert edge.object in nodes_by_qg_id['n01']


@pytest.mark.slow
def test_720_ambitious_query_causing_multiple_qnode_keys_error():
    actions_list = [
        "add_qnode(id=DOID:14330, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:Disease, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=ARAX/KG1, edge_key=[e00, e01])",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert set(nodes_by_qg_id['n00']).intersection(set(nodes_by_qg_id['n02']))


@pytest.mark.slow
def test_720_multiple_qg_ids_in_different_results():
    actions_list = [
        "add_qnode(key=n00, id=DOID:14330)",
        "add_qnode(key=n01, category=biolink:Protein)",
        "add_qnode(key=n02, category=biolink:ChemicalSubstance)",
        "add_qnode(key=n03, category=biolink:Protein, id=UniProtKB:P37840)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "add_qedge(key=e01, subject=n01, object=n02)",
        "add_qedge(key=e02, subject=n02, object=n03)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert set(nodes_by_qg_id['n01']).intersection(set(nodes_by_qg_id['n03']))
    assert any(set(node.qnode_keys) == {'n01', 'n03'} for node in nodes_by_qg_id['n01'].values())


@pytest.mark.slow
def test_bte_acetaminophen_query():
    actions_list = [
        "add_qnode(key=n00, id=CHEMBL.COMPOUND:CHEMBL112, category=biolink:ChemicalSubstance)",
        "add_qnode(key=n01, category=biolink:Disease)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_bte_protein_query():
    actions_list = [
        "add_qnode(id=UniProtKB:P16471, category=biolink:Protein, key=n00)",
        "add_qnode(category=biolink:Cell, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_bte_without_synonyms():
    actions_list = [
        "add_qnode(id=UniProtKB:P16471, category=biolink:Protein, key=n00)",
        "add_qnode(category=biolink:Cell, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=BTE, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_bte_using_list_of_curies():
    actions_list = [
        "add_qnode(key=n00, id=[CHEMBL.COMPOUND:CHEMBL112, CHEMBL.COMPOUND:CHEMBL521], category=biolink:ChemicalSubstance)",
        "add_qnode(key=n01, category=biolink:Disease)",
        "add_qedge(key=e00, subject=n01, object=n00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) > 1


def test_single_node_query_with_synonyms():
    actions_list = [
        "add_qnode(key=n00, id=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_key=n00, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_without_synonyms():
    actions_list = [
        "add_qnode(key=n00, id=CHEMBL.COMPOUND:CHEMBL1276308)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_no_results():
    actions_list = [
        "add_qnode(key=n00, id=FAKE:curie)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_single_node_query_with_list():
    actions_list = [
        "add_qnode(key=n00, id=[CHEMBL.COMPOUND:CHEMBL108, CHEMBL.COMPOUND:CHEMBL110])",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 2


@pytest.mark.slow
def test_query_that_returns_multiple_provided_bys():
    actions_list = [
        "add_qnode(id=MONDO:0005737, key=n0, category=biolink:Disease)",
        "add_qnode(category=biolink:Protein, key=n1)",
        "add_qnode(category=biolink:Disease, key=n2)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_three_hop_query():
    actions_list = [
        "add_qnode(key=n00, id=DOID:8454)",
        "add_qnode(key=n01, category=biolink:PhenotypicFeature)",
        "add_qnode(key=n02, category=biolink:Protein)",
        "add_qnode(key=n03, category=biolink:AnatomicalEntity)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "add_qedge(subject=n02, object=n03, key=e02)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_branched_query():
    actions_list = [
        "add_qnode(key=n00, id=DOID:0060227)",  # Adams-Oliver
        "add_qnode(key=n01, category=biolink:PhenotypicFeature, is_set=true)",
        "add_qnode(key=n02, category=biolink:Disease)",
        "add_qnode(key=n03, category=biolink:Protein, is_set=true)",
        "add_qedge(subject=n01, object=n00, key=e00)",
        "add_qedge(subject=n02, object=n00, key=e01)",
        "add_qedge(subject=n00, object=n03, key=e02)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_no_synonym_query_with_duplicate_nodes_in_results():
    actions_list = [
        "add_qnode(key=n00, id=DOID:14330)",
        "add_qnode(key=n01, category=biolink:Disease)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG2, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) > 1


@pytest.mark.slow
def test_query_that_expands_same_edge_twice():
    actions_list = [
        "add_qnode(key=n00, id=DOID:9065)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "expand(kp=ARAX/KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert any(edge for edge in edges_by_qg_id['e00'].values() if
               any(attr for attr in edge.attributes if attr.name == "is_defined_by" and attr.value == "ARAX/KG1"))
    assert any(edge for edge in edges_by_qg_id['e00'].values() if
               any(attr for attr in edge.attributes if attr.name == "is_defined_by" and attr.value == "ARAX/KG2c"))


def test_771_continue_if_no_results_query():
    actions_list = [
        "add_qnode(id=UniProtKB:P14136, key=n00)",
        "add_qnode(category=biolink:BiologicalProcess, key=n01)",
        "add_qnode(id=UniProtKB:P35579, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n02, object=n01, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert 'n02' not in nodes_by_qg_id
    assert 'e01' not in edges_by_qg_id


@pytest.mark.slow
def test_774_continue_if_no_results_query():
    actions_list = [
        "add_qnode(id=CHEMBL.COMPOUND:CHEMBL112, key=n1)",
        "add_qnode(id=DOID:8295, key=n2)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(edge_key=e1, kp=ARAX/KG2, continue_if_no_results=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_curie_list_query_with_synonyms():
    actions_list = [
        "add_qnode(id=[DOID:6419, DOID:3717, DOID:11406], key=n00)",
        "add_qnode(category=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_curie_list_query_without_synonyms():
    actions_list = [
        "add_qnode(id=[DOID:6419, DOID:3717, DOID:11406], key=n00)",
        "add_qnode(category=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_curies_on_both_ends():
    actions_list = [
        "add_qnode(id=MONDO:0005393, key=n00)",  # Gout
        "add_qnode(id=UMLS:C0018100, key=n01)",  # Antigout agents
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_intermediate_curie_node():
    actions_list = [
        "add_qnode(category=biolink:Protein, key=n00)",
        "add_qnode(id=HP:0005110, key=n01)",  # atrial fibrillation
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_847_dont_expand_curie_less_edge():
    actions_list = [
        "add_qnode(key=n00, category=biolink:Protein)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, should_throw_error=True)


@pytest.mark.slow
def test_deduplication_and_self_edges():
    actions_list = [
        "add_qnode(id=UMLS:C0004572, key=n00)",  # Babesia
        "add_qnode(key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    # Check that deduplication worked appropriately
    all_node_keys = {node_key for nodes in nodes_by_qg_id.values() for node_key in nodes}
    babesia_curies = {"UMLS:C0004572", "CHV:0000001647", "LNC:LP19999-9", "MEDDRA:10003963", "MESH:D001403",
                      "NCIT:C122040", "NCI_CDISC:C122040", "SNOMEDCT:35029001"}
    babesia_curies_in_answer = all_node_keys.intersection(babesia_curies)
    assert len(babesia_curies_in_answer) <= 1
    # Check that we don't have any self-edges
    self_edges = [edge for edge in edges_by_qg_id['e00'].values() if edge.subject == edge.object]
    assert not self_edges


@pytest.mark.slow
def test_889_missing_curies():
    actions_list = [
        "add_qnode(name=DOID:11830, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:molecularly_interacts_with)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n02']) > 30


@pytest.mark.slow
def test_873_consider_both_gene_and_protein():
    actions_list_protein = [
        "add_qnode(id=DOID:9452, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_protein, edges_by_qg_id_protein = _run_query_and_do_standard_testing(actions_list_protein)
    actions_list_gene = [
        "add_qnode(id=DOID:9452, key=n00)",
        "add_qnode(category=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_gene, edges_by_qg_id_gene = _run_query_and_do_standard_testing(actions_list_gene)
    assert set(nodes_by_qg_id_protein['n01']) == set(nodes_by_qg_id_gene['n01'])


def test_987_override_node_categories():
    actions_list = [
        "add_qnode(name=DOID:8398, key=n00)",
        "add_qnode(category=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:has_phenotype, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all('biolink:PhenotypicFeature' in node.category for node in nodes_by_qg_id['n01'].values())


@pytest.mark.slow
def test_COHD_expand_paired_concept_freq():
    actions_list = [
        "add_qnode(id=UMLS:C0015967, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=paired_concept_freq, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_paired_concept_frequency_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].name == "paired_concept_frequency" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].type == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.slow
def test_COHD_expand_observed_expected_ratio():
    actions_list = [
        "add_qnode(id=DOID:10718, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=observed_expected_ratio, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_ln_observed_expected_ratio_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].name == "ln_observed_expected_ratio" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].type == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


def test_COHD_expand_chi_square():
    actions_list = [
        "add_qnode(id=DOID:1588, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=chi_square, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_chi_square_pvalue_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].name == "chi_square_pvalue" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].type == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


def test_DTD_expand_1():
    actions_list = [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].name == "probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].type == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])

@pytest.mark.slow
def test_DTD_expand_2():
    actions_list = [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(category=disease, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0.8, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].name == "probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].type == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])

def test_ngd_expand():
    actions_list = [
        "add_qnode(name=DOID:14330, key=n00)",
        "add_qnode(category=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:has_phenotype, key=e00)",
        "expand(kp=NGD)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_genetics_kp_simple():
    actions_list = [
        "add_qnode(id=NCBIGene:1803, category=biolink:Gene, key=n00)",
        "add_qnode(category=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicate=biolink:gene_associated_with_condition)",
        "expand(kp=GeneticsKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_genetics_kp_all_scores():
    actions_list = [
        "add_qnode(name=type 2 diabetes mellitus, category=biolink:Disease, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicate=biolink:condition_associated_with_gene)",
        "expand(kp=GeneticsKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_genetics_kp_2_hop():
    actions_list = [
        "add_qnode(id=UniProtKB:Q99712, key=n00, category=biolink:Protein)",
        "add_qnode(category=biolink:Disease, key=n01)",
        "add_qnode(category=biolink:Gene, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00, predicate=biolink:gene_associated_with_condition)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:condition_associated_with_gene)",
        "expand(kp=GeneticsKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_genetics_kp_multi_kp():
    actions_list = [
        "add_qnode(key=n0, name=ertugliflozin, category=biolink:ChemicalSubstance)",
        "add_qnode(key=n1, category=biolink:Disease, is_set=true)",
        "add_qnode(key=n2, category=biolink:Protein)",
        "add_qedge(key=e0, subject=n0, object=n1)",
        "add_qedge(key=e1, subject=n1, object=n2, predicate=biolink:condition_associated_with_gene)",
        "expand(kp=ARAX/KG2, edge_key=e0)",
        "expand(kp=GeneticsKP, edge_key=e1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_multi_kp_two_hop_query():
    actions_list = [
        "add_qnode(id=MONDO:0005737, key=n00, category=biolink:Disease)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=ARAX/KG2, edge_key=[e00,e01], continue_if_no_results=true)",
        "expand(kp=ARAX/KG1, edge_key=e01, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_molepro_query():
    actions_list = [
        "add_qnode(id=HGNC:9379, category=biolink:Gene, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=MolePro)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_exclude_edge_parallel():
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, key=e01)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_contraindicated_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["e01"])
    n01_nodes_contraindicated = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_contraindicated_edge)
    assert n01_nodes_contraindicated

    # Then exclude the contraindicated edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, exclude=true, key=e01)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_not, edges_by_qg_id_not = _run_query_and_do_standard_testing(actions_list)
    # None of the contraindicated n01 nodes should appear in the answer this time
    assert not n01_nodes_contraindicated.intersection(set(nodes_by_qg_id_not["n01"]))
    assert "e01" not in edges_by_qg_id_not


@pytest.mark.slow
def test_exclude_edge_perpendicular():
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(id=DOID:3312, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "add_qnode(category=biolink:Pathway, key=n03)",
        "add_qedge(subject=n01, object=n03, key=e02)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_kryptonite_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["e02"])
    n01_nodes_to_blow_away = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_kryptonite_edge)
    assert n01_nodes_to_blow_away

    # Then use a kryptonite edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(id=DOID:3312, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "add_qnode(category=biolink:Pathway, key=n03)",
        "add_qedge(subject=n01, object=n03, key=e02, exclude=true)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_not, edges_by_qg_id_not = _run_query_and_do_standard_testing(actions_list)
    assert not n01_nodes_to_blow_away.intersection(set(nodes_by_qg_id_not["n01"]))
    assert "e02" not in edges_by_qg_id_not and "n03" not in nodes_by_qg_id_not


@pytest.mark.slow
def test_exclude_edge_ordering():
    # This test makes sures that kryptonite qedges are expanded AFTER their adjacent qedges
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, exclude=true, key=e01)",
        "expand(kp=ARAX/KG1, edge_key=e00)",
        "expand(kp=ARAX/KG1, edge_key=e01)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_a, edges_by_qg_id_a = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, exclude=true, key=e01)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_b, edges_by_qg_id_b = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, exclude=true, key=e01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_c, edges_by_qg_id_c = _run_query_and_do_standard_testing(actions_list)
    # All of these queries should produce the same KG contents
    assert set(nodes_by_qg_id_a["n01"]) == set(nodes_by_qg_id_b["n01"]) == set(nodes_by_qg_id_c["n01"])
    assert set(edges_by_qg_id_a["e00"]) == set(edges_by_qg_id_b["e00"]) == set(edges_by_qg_id_c["e00"])


def test_exclude_edge_no_results():
    # Tests query with an exclude edge that doesn't have any matches in the KP (shouldn't error out)
    actions = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:not_a_real_edge_type, exclude=true, key=e01)",
        "expand(kp=ARAX/KG1)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_option_group_query_one_hop():
    # Tests a simple one-hop query with an optional edge
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:positively_regulates)",
        "add_qedge(key=e01, subject=n00, object=n01, predicate=biolink:correlated_with, option_group_id=1)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


@pytest.mark.slow
def test_option_group_query_no_results():
    # Tests query with optional path that doesn't have any matches in the KP (shouldn't error out)
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, id=CHEBI:48607)",
        "add_qnode(key=n02, category=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:related_to)",
        "add_qedge(key=e01, subject=n00, object=n02, option_group_id=1, predicate=biolink:overlaps)",
        "add_qedge(key=e02, subject=n02, object=n01, option_group_id=1, predicate=biolink:affects)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_category_and_predicate_format():
    actions_list = [
        "add_qnode(id=UniProtKB:P42857, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicate=biolink:positively_regulates_entity_to_entity)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    for qnode_key, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            assert all(category.startswith("biolink:") for category in node.category)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge.predicate.startswith("biolink:")
            assert "," not in edge.predicate


def test_issue_1212():
    # If a qnode curie isn't recognized by synonymizer, shouldn't end up with results when using KG2c
    actions_list = [
        "add_qnode(id=FAKE:Curie, category=biolink:Drug, key=n00)",
        "add_qnode(category=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=ARAX/KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)


def test_issue_1314():
    # KG2 should return answers for "treated_by" (even though it only contains "treats" edges)
    actions_list = [
        "add_qnode(key=n0, id=DRUGBANK:DB00394, category=biolink:Drug)",
        "add_qnode(key=n1, category=biolink:Disease)",
        "add_qedge(key=e0, subject=n1, object=n0, predicate=biolink:treated_by)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_expand.py'])
