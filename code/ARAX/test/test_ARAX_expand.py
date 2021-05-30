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
            assert isinstance(node.name, str) or node.name is None
            assert node.qnode_keys and isinstance(node.qnode_keys, list)
            assert node.categories and isinstance(node.categories, list) or node.categories is None
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge_key and isinstance(edge_key, str)
            assert edge.qedge_keys and isinstance(edge.qedge_keys, list)
            assert edge.subject and isinstance(edge.subject, str)
            assert edge.object and isinstance(edge.object, str)
            assert edge.predicate and isinstance(edge.predicate, str) or edge.predicate is None


def _check_node_categories(nodes: Dict[str, Node], query_graph: QueryGraph):
    for node in nodes.values():
        for qnode_key in node.qnode_keys:
            qnode = query_graph.nodes[qnode_key]
            if qnode.categories:
                assert set(qnode.categories).issubset(set(node.categories))  # Could have additional categories if it has multiple qnode keys


def _check_counts_of_curie_qnodes(nodes_by_qg_id: Dict[str, Dict[str, Node]], query_graph: QueryGraph):
    # Note: Can't really use this function anymore since KPs can respond with multiple curies per 1 qg curie now...
    qnodes_with_single_curie = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.ids and len(qnode.ids) == 1]
    for qnode_key in qnodes_with_single_curie:
        if qnode_key in nodes_by_qg_id:
            assert len(nodes_by_qg_id[qnode_key]) == 1
    qnodes_with_multiple_curies = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.ids and len(qnode.ids) > 1]
    for qnode_key in qnodes_with_multiple_curies:
        qnode = query_graph.nodes[qnode_key]
        if qnode_key in nodes_by_qg_id:
            assert 1 <= len(nodes_by_qg_id[qnode_key]) <= len(qnode.ids)


@pytest.mark.slow
def test_720_multiple_qg_ids_in_different_results():
    actions_list = [
        "add_qnode(key=n00, ids=MONDO:0014324)",
        "add_qnode(key=n01, categories=biolink:Protein)",
        "add_qnode(key=n02, categories=biolink:ChemicalSubstance)",
        "add_qnode(key=n03, categories=biolink:Protein)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "add_qedge(key=e01, subject=n01, object=n02, predicates=biolink:molecularly_interacts_with)",
        "add_qedge(key=e02, subject=n02, object=n03, predicates=biolink:molecularly_interacts_with)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert set(nodes_by_qg_id['n01']).intersection(set(nodes_by_qg_id['n03']))
    assert any(set(node.qnode_keys) == {'n01', 'n03'} for node in nodes_by_qg_id['n01'].values())


@pytest.mark.external
def test_bte_query():
    actions_list = [
        "add_qnode(ids=UniProtKB:P16471, categories=biolink:Protein, key=n00)",
        "add_qnode(categories=biolink:Cell, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_synonyms():
    actions_list = [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_key=n00, kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_without_synonyms():
    actions_list = [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL1276308)",
        "expand(kp=RTX-KG2, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_no_results():
    actions_list = [
        "add_qnode(key=n00, ids=FAKE:curie)",
        "expand(kp=RTX-KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_single_node_query_with_list():
    actions_list = [
        "add_qnode(key=n00, ids=[CHEMBL.COMPOUND:CHEMBL108, CHEMBL.COMPOUND:CHEMBL110])",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 2


@pytest.mark.slow
def test_query_that_returns_multiple_provided_bys():
    actions_list = [
        "add_qnode(ids=MONDO:0005737, key=n0, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Protein, key=n1)",
        "add_qnode(categories=biolink:Disease, key=n2)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_branched_query():
    actions_list = [
        "add_qnode(key=n00, ids=DOID:0060227)",  # Adams-Oliver
        "add_qnode(key=n01, categories=biolink:PhenotypicFeature, is_set=true)",
        "add_qnode(key=n02, categories=biolink:Disease)",
        "add_qnode(key=n03, categories=biolink:Protein, is_set=true)",
        "add_qedge(subject=n01, object=n00, key=e00)",
        "add_qedge(subject=n02, object=n00, key=e01)",
        "add_qedge(subject=n00, object=n03, key=e02)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_no_synonym_query_with_duplicate_nodes_in_results():
    actions_list = [
        "add_qnode(key=n00, ids=DOID:14330)",
        "add_qnode(key=n01, categories=biolink:Disease)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n01']) > 1


@pytest.mark.slow
def test_query_that_expands_same_edge_twice():
    actions_list = [
        "add_qnode(key=n00, ids=DOID:9065, categories=biolink:Disease)",
        "add_qnode(key=n01, categories=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:treats)",
        "expand(kp=RTX-KG2)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_771_continue_if_no_results_query():
    actions_list = [
        "add_qnode(ids=UniProtKB:P14136, key=n00)",
        "add_qnode(categories=biolink:BiologicalProcess, key=n01)",
        "add_qnode(ids=NOTAREALCURIE, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n02, object=n01, key=e01)",
        "expand(edge_key=[e00,e01], kp=RTX-KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert 'n02' not in nodes_by_qg_id
    assert 'e01' not in edges_by_qg_id


@pytest.mark.slow
def test_774_continue_if_no_results_query():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, key=n1)",
        "add_qnode(ids=DOID:8295, key=n2)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(edge_key=e1, kp=RTX-KG2, continue_if_no_results=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_curie_list_query():
    actions_list = [
        "add_qnode(ids=[DOID:6419, DOID:3717, DOID:11406], key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id["n00"]) == 3


@pytest.mark.slow
def test_query_with_curies_on_both_ends():
    actions_list = [
        "add_qnode(ids=MONDO:0005393, key=n00)",  # Gout
        "add_qnode(ids=UMLS:C0018100, key=n01)",  # Antigout agents
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_intermediate_curie_node():
    actions_list = [
        "add_qnode(categories=biolink:Protein, key=n00)",
        "add_qnode(ids=HP:0005110, key=n01)",  # atrial fibrillation
        "add_qnode(categories=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_847_dont_expand_curie_less_edge():
    actions_list = [
        "add_qnode(key=n00, categories=biolink:Protein)",
        "add_qnode(key=n01, categories=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, should_throw_error=True)


@pytest.mark.slow
def test_deduplication_and_self_edges():
    actions_list = [
        "add_qnode(ids=UMLS:C0004572, key=n00)",  # Babesia
        "add_qnode(key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=RTX-KG2)",
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
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:molecularly_interacts_with)",
        "expand(edge_key=[e00,e01], kp=RTX-KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n02']) > 30


@pytest.mark.slow
def test_873_consider_both_gene_and_protein():
    actions_list_protein = [
        "add_qnode(ids=DOID:9452, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_protein, edges_by_qg_id_protein = _run_query_and_do_standard_testing(actions_list_protein)
    actions_list_gene = [
        "add_qnode(ids=DOID:9452, key=n00)",
        "add_qnode(categories=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_gene, edges_by_qg_id_gene = _run_query_and_do_standard_testing(actions_list_gene)
    assert set(nodes_by_qg_id_protein['n01']) == set(nodes_by_qg_id_gene['n01'])


def test_987_override_node_categories():
    actions_list = [
        "add_qnode(name=DOID:8398, key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:has_phenotype, key=e00)",
        "expand(edge_key=e00, kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all('biolink:PhenotypicFeature' in node.categories for node in nodes_by_qg_id['n01'].values())


@pytest.mark.slow
def test_cohd_expand_paired_concept_freq():
    actions_list = [
        "add_qnode(ids=UMLS:C0015967, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=paired_concept_freq, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_paired_concept_frequency_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "paired_concept_frequency" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.slow
def test_cohd_expand_observed_expected_ratio():
    actions_list = [
        "add_qnode(ids=DOID:10718, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=observed_expected_ratio, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_ln_observed_expected_ratio_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "ln_observed_expected_ratio" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.slow
def test_cohd_expand_chi_square():
    actions_list = [
        "add_qnode(ids=DOID:1588, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=chi_square, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:has_chi_square_pvalue_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "chi_square_pvalue" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "http://cohd.smart-api.info/" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


def test_dtd_expand_1():
    actions_list = [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.slow
def test_dtd_expand_2():
    actions_list = [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(categories=biolink:Disease, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0.8, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "probability_treats" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


def test_ngd_expand():
    actions_list = [
        "add_qnode(name=MONDO:0007156, key=n00)",
        "add_qnode(categories=biolink:Drug, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=NGD)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_chp_expand_1():
    actions_list = [
        "add_qnode(ids=ENSEMBL:ENSG00000162419, key=n00)",
        "add_qnode(categories=biolink:Drug, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=CHP, CHP_survival_threshold=500)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:paired_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "paired_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://github.com/di2ag/chp_client" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.external
def test_chp_expand_2():
    actions_list = [
        "add_qnode(ids=[ENSEMBL:ENSG00000124532,ENSEMBL:ENSG00000075975,ENSEMBL:ENSG00000104774], key=n00)",
        "add_qnode(categories=biolink:Drug, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=CHP, CHP_survival_threshold=500)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all([edges_by_qg_id[qedge_key][edge_key].predicate == "biolink:paired_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].original_attribute_name == "paired_with" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM:data_0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://github.com/di2ag/chp_client" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


@pytest.mark.external
def test_genetics_kp():
    actions_list = [
        "add_qnode(ids=NCBIGene:1803, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:gene_associated_with_condition)",
        "expand(kp=GeneticsKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_molepro_query():
    actions_list = [
        "add_qnode(ids=HGNC:9379, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=MolePro)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_exclude_edge_parallel():
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, key=e01)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_contraindicated_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["e01"])
    n01_nodes_contraindicated = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_contraindicated_edge)
    assert n01_nodes_contraindicated

    # Then exclude the contraindicated edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, exclude=true, key=e01)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_not, edges_by_qg_id_not = _run_query_and_do_standard_testing(actions_list)
    # None of the contraindicated n01 nodes should appear in the answer this time
    assert not n01_nodes_contraindicated.intersection(set(nodes_by_qg_id_not["n01"]))
    assert "e01" not in edges_by_qg_id_not


@pytest.mark.slow
def test_exclude_edge_perpendicular():
    n02_curies = ", ".join(["CHEMBL.COMPOUND:CHEMBL114655", "CHEMBL.COMPOUND:CHEMBL32800"])
    exclude_curies = ", ".join(["CHEMBL.COMPOUND:CHEMBL114655"])
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        f"add_qnode(categories=biolink:ChemicalSubstance, key=n02, ids=[{n02_curies}])",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        f"add_qnode(categories=biolink:Drug, key=nx0, ids=[{exclude_curies}], option_group_id=1)",
        "add_qedge(subject=n01, object=nx0, key=ex0, option_group_id=1)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_kryptonite_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["ex0"])
    n01_nodes_to_blow_away = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_kryptonite_edge)
    assert n01_nodes_to_blow_away

    # Then use a kryptonite edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        f"add_qnode(categories=biolink:ChemicalSubstance, key=n02, ids=[{n02_curies}])",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        f"add_qnode(categories=biolink:Drug, key=nx0, ids=[{exclude_curies}])",
        "add_qedge(subject=n01, object=nx0, key=ex0, exclude=true)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_not, edges_by_qg_id_not = _run_query_and_do_standard_testing(actions_list)
    assert not n01_nodes_to_blow_away.intersection(set(nodes_by_qg_id_not["n01"]))
    assert "ex0" not in edges_by_qg_id_not and "nx0" not in nodes_by_qg_id_not


@pytest.mark.slow
def test_exclude_edge_ordering():
    # This test makes sures that kryptonite qedges are expanded AFTER their adjacent qedges
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "expand(kp=RTX-KG2, edge_key=e00)",
        "expand(kp=RTX-KG2, edge_key=e01)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_a, edges_by_qg_id_a = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_b, edges_by_qg_id_b = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "expand(kp=RTX-KG2)",
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
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:not_a_real_edge_type, exclude=true, key=e01)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_option_group_query_one_hop():
    # Tests a simple one-hop query with an optional edge
    actions = [
        "add_qnode(key=n00, ids=DOID:3312)",
        "add_qnode(key=n01, categories=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:positively_regulates)",
        "add_qedge(key=e01, subject=n00, object=n01, predicates=biolink:correlated_with, option_group_id=1)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


@pytest.mark.slow
def test_option_group_query_no_results():
    # Tests query with optional path that doesn't have any matches in the KP (shouldn't error out)
    actions = [
        "add_qnode(key=n00, ids=DOID:3312)",
        "add_qnode(key=n01, ids=CHEBI:48607)",
        "add_qnode(key=n02, categories=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:related_to)",
        "add_qedge(key=e01, subject=n00, object=n02, option_group_id=1, predicates=biolink:overlaps)",
        "add_qedge(key=e02, subject=n02, object=n01, option_group_id=1, predicates=biolink:affects)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_category_and_predicate_format():
    actions_list = [
        "add_qnode(ids=UniProtKB:P42857, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:positively_regulates_entity_to_entity)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    for qnode_key, nodes in nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            assert all(category.startswith("biolink:") for category in node.categories)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            assert edge.predicate.startswith("biolink:")
            assert "," not in edge.predicate


def test_issue_1212():
    # If a qnode curie isn't recognized by synonymizer, shouldn't end up with results when using KG2c
    actions_list = [
        "add_qnode(ids=FAKE:Curie, categories=biolink:Drug, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=RTX-KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)


def test_issue_1314():
    # KG2 should return answers for "treated_by" (even though it only contains "treats" edges)
    actions_list = [
        "add_qnode(key=n0, ids=DRUGBANK:DB00394, categories=biolink:Drug)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e0, subject=n1, object=n0, predicates=biolink:treated_by)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_issue_1236_a():
    # Test that multiple KPs are used for expansion when no KP is specified in DSL
    actions_list = [
        "add_qnode(ids=NCBIGene:1803, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:gene_associated_with_condition)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)

    actions_list_kg2_only = [
        "add_qnode(ids=NCBIGene:1803, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:gene_associated_with_condition)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_kg2_only, edges_by_qg_id_kg2_only = _run_query_and_do_standard_testing(actions_list_kg2_only)

    assert len(nodes_by_qg_id["n01"]) > len(nodes_by_qg_id_kg2_only["n01"])


def test_issue_1236_b():
    actions_list = [
        "add_qnode(ids=DOID:14330, categories=biolink:Disease, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:condition_associated_with_gene)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_kg2_predicate_hierarchy_reasoning():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, categories=biolink:Drug, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:interacts_with)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:physically_interacts_with")
    assert any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:molecularly_interacts_with")
    assert not any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:related_to")


def test_issue_1373_pinned_curies():
    actions_list = [
        "add_qnode(ids=chembl.compound:CHEMBL2108129, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qnode(categories=biolink:Drug, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:physically_interacts_with)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert "CHEMBL.COMPOUND:CHEMBL2108129" not in nodes_by_qg_id["n02"]


@pytest.mark.external
def test_multiomics_clinical_risk_kp():
    actions_list = [
        "add_qnode(ids=DOID:14330, categories=biolink:Disease, key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:related_to)",
        "expand(kp=ClinicalRiskKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_wellness_kp():
    actions_list = [
        "add_qnode(ids=UniProtKB:O00533, categories=biolink:Protein, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=WellnessKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_drug_response_kp():
    actions_list = [
        "add_qnode(ids=NCBIGene:7157, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=DrugResponseKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_tumor_gene_mutation_kp():
    actions_list = [
        "add_qnode(ids=MONDO:0018177, key=n00)",
        "add_qnode(categories=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=TumorGeneMutationKP)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_many_kp_query():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_entity_to_entity_predicate_patch():
    actions_list = [
        "add_qnode(ids=NCBIGene:23221, categories=biolink:Gene, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0, predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=RTX-KG2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_expand.py'])
