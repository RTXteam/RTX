#!/bin/env python3
"""
Usage:
    Run all expand tests: pytest -v test_ARAX_expand.py
    Run a single test: pytest -v test_ARAX_expand.py -k test_branched_query
"""

import sys
import os
from typing import List, Dict, Tuple, Optional

import pytest

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
                                       error_code: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[Dict[str, Dict[str, Node]], Dict[str, Dict[str, Edge]]]:
    # Run the query
    araxq = ARAXQuery()
    assert actions or json_query  # Must provide some sort of query to run
    query_object = {"operations": {"actions": actions}} if actions else {"message": {"query_graph": json_query}}
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


@pytest.mark.slow
def test_720_multiple_qg_ids_in_different_results():
    actions_list = [
        "add_qnode(key=n00, ids=MONDO:0014324)",
        "add_qnode(key=n01, categories=biolink:Protein)",
        "add_qnode(key=n02, categories=biolink:ChemicalEntity)",
        "add_qnode(key=n03, categories=biolink:Protein)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "add_qedge(key=e01, subject=n01, object=n02, predicates=biolink:physically_interacts_with)",
        "add_qedge(key=e02, subject=n02, object=n03, predicates=biolink:physically_interacts_with)",
        "expand(kp=infores:rtx-kg2)",
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
        "expand(kp=infores:biothings-explorer)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_synonyms():
    actions_list = [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_key=n00, kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_single_node_query_with_no_results():
    actions_list = [
        "add_qnode(key=n00, ids=FAKE:curie)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_single_node_query_with_list():
    actions_list = [
        "add_qnode(key=n00, ids=[CHEMBL.COMPOUND:CHEMBL108, CHEMBL.COMPOUND:CHEMBL110])",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id['n00']) == 2


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
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_that_expands_same_edge_twice():
    actions_list = [
        "add_qnode(key=n00, ids=DOID:9065, categories=biolink:Disease)",
        "add_qnode(key=n01, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:treats)",
        "expand(kp=infores:rtx-kg2)",
        "expand(kp=infores:rtx-kg2)",
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
        "expand(edge_key=[e00,e01], kp=infores:rtx-kg2)",
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
        "expand(edge_key=e1, kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert not nodes_by_qg_id and not edges_by_qg_id


def test_curie_list_query():
    actions_list = [
        "add_qnode(ids=[DOID:6419, DOID:3717, DOID:11406], key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert len(nodes_by_qg_id["n00"]) >= 3


@pytest.mark.slow
def test_query_with_curies_on_both_ends():
    actions_list = [
        "add_qnode(ids=MONDO:0005393, key=n00)",  # Gout
        "add_qnode(ids=UMLS:C0018100, key=n01)",  # Antigout agents
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_query_with_intermediate_curie_node():
    actions_list = [
        "add_qnode(categories=biolink:Protein, key=n00, is_set=True)",
        "add_qnode(ids=HP:0005110, key=n01)",  # atrial fibrillation
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:treats)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:related_to)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_847_dont_expand_curie_less_edge():
    actions_list = [
        "add_qnode(key=n00, categories=biolink:Protein)",
        "add_qnode(key=n01, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, should_throw_error=True,
                                                                        error_code="InvalidQuery")


@pytest.mark.slow
def test_deduplication_and_self_edges():
    actions_list = [
        "add_qnode(ids=UMLS:C0004572, key=n00)",  # Babesia
        "add_qnode(key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
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
def test_873_consider_both_gene_and_protein():
    actions_list_protein = [
        "add_qnode(ids=DOID:9452, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_protein, edges_by_qg_id_protein = _run_query_and_do_standard_testing(actions_list_protein)
    actions_list_gene = [
        "add_qnode(ids=DOID:9452, key=n00)",
        "add_qnode(categories=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)",
    ]
    nodes_by_qg_id_gene, edges_by_qg_id_gene = _run_query_and_do_standard_testing(actions_list_gene)
    assert set(nodes_by_qg_id_protein['n01']) == set(nodes_by_qg_id_gene['n01'])


def test_987_override_node_categories():
    actions_list = [
        "add_qnode(name=DOID:8398, key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:has_phenotype, key=e00)",
        "expand(edge_key=e00, kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert all('biolink:PhenotypicFeature' in node.categories for node in nodes_by_qg_id['n01'].values())


@pytest.mark.external
def test_cohd_expand():
    actions_list = [
        "add_qnode(ids=MONDO:0005301, key=n00)",
        "add_qnode(categories=biolink:SmallMolecule, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:correlated_with)",
        "expand(edge_key=e00, kp=infores:cohd)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_dtd_expand_1():
    actions_list = [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=infores:arax-drug-treats-disease, DTD_threshold=0, DTD_slow_mode=True)",
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
        "expand(edge_key=e0, kp=infores:arax-drug-treats-disease, DTD_threshold=0, DTD_slow_mode=True)",
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
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:arax-normalized-google-distance)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_chp_expand_1():
    actions_list = [
        "add_qnode(ids=ENSEMBL:ENSG00000162419, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:connections-hypothesis)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_chp_expand_2():
    actions_list = [
        "add_qnode(ids=[ENSEMBL:ENSG00000124532,ENSEMBL:ENSG00000075975,ENSEMBL:ENSG00000104774], key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:connections-hypothesis)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_genetics_kp():
    actions_list = [
        "add_qnode(ids=NCBIGene:1803, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:gene_associated_with_condition)",
        "expand(kp=infores:genetics-data-provider)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_molepro_query():
    actions_list = [
        "add_qnode(ids=HGNC:9379, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:molepro)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_spoke_query():
    actions_list = [
        "add_qnode(ids=OMIM:603903, categories=biolink:PhenotypicFeature, key=n00)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:spoke)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_exclude_edge_parallel():
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:causes, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    contraindicated_pairs = {tuple(sorted([edge.subject, edge.object])) for edge in edges_by_qg_id["e00"].values()}
    assert contraindicated_pairs

    # Then exclude the contraindicated edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:causes, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_not, edges_by_qg_id_not = _run_query_and_do_standard_testing(actions_list)
    # None of the contraindicated n01 nodes should appear in the answer this time
    final_pairs = {tuple(sorted([edge.subject, edge.object])) for edge in edges_by_qg_id_not["e00"].values()}
    assert not contraindicated_pairs.intersection(final_pairs)
    assert "e01" not in edges_by_qg_id_not


@pytest.mark.slow
def test_exclude_edge_perpendicular():
    exclude_curies = ", ".join(['CHEMBL.COMPOUND:CHEMBL190', 'CHEMBL.COMPOUND:CHEMBL775'])
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01, is_set=true)",
        f"add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:causes)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:entity_positively_regulates_entity)",
        # 'Exclude' portion (just optional for now to get a baseline)
        f"add_qnode(categories=biolink:ChemicalEntity, key=nx0, option_group_id=1, ids=[{exclude_curies}])",
        "add_qedge(subject=n01, object=nx0, key=ex0, option_group_id=1, predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_kryptonite_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["ex0"])
    n01_nodes_to_blow_away = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_kryptonite_edge)
    assert n01_nodes_to_blow_away

    # Then use a kryptonite edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01, is_set=true)",
        f"add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:causes)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:entity_positively_regulates_entity)",
        # 'Exclude' portion
        f"add_qnode(categories=biolink:ChemicalEntity, key=nx0, ids=[{exclude_curies}])",
        "add_qedge(subject=n01, object=nx0, key=ex0, exclude=True, predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=infores:rtx-kg2)",
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
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2, edge_key=e00)",
        "expand(kp=infores:rtx-kg2, edge_key=e01)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_a, edges_by_qg_id_a = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_b, edges_by_qg_id_b = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes, exclude=true, key=e01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "expand(kp=infores:rtx-kg2)",
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
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:not_a_real_edge_type, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_option_group_query_one_hop():
    # Tests a simple one-hop query with an optional edge
    actions = [
        "add_qnode(key=n00, ids=DOID:3312)",
        "add_qnode(key=n01, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e00, subject=n01, object=n00, predicates=biolink:causes)",
        "add_qedge(key=e01, subject=n00, object=n01, predicates=biolink:affects, option_group_id=1)",
        "expand(kp=infores:rtx-kg2)",
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
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_category_and_predicate_format():
    actions_list = [
        "add_qnode(ids=UniProtKB:P42857, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:affects)",
        "expand(kp=infores:rtx-kg2)",
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
        "add_qnode(ids=FAKE:Curie, categories=biolink:ChemicalEntity, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)


def test_issue_1314():
    # KG2 should return answers for "treated_by" (even though it only contains "treats" edges)
    actions_list = [
        "add_qnode(key=n0, ids=DRUGBANK:DB00394, categories=biolink:ChemicalEntity)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e0, subject=n1, object=n0, predicates=biolink:treated_by)",
        "expand(kp=infores:rtx-kg2)",
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
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_kg2_only, edges_by_qg_id_kg2_only = _run_query_and_do_standard_testing(actions_list_kg2_only)

    assert len(nodes_by_qg_id["n01"]) > len(nodes_by_qg_id_kg2_only["n01"])


def test_issue_1236_b():
    actions_list = [
        "add_qnode(ids=DOID:14330, categories=biolink:Disease, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:condition_associated_with_gene)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_kg2_predicate_hierarchy_reasoning():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, categories=biolink:ChemicalEntity, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:affects)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:affects")
    assert any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:entity_positively_regulates_entity")
    assert not any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:related_to")


def test_issue_1373_pinned_curies():
    actions_list = [
        "add_qnode(ids=chembl.compound:CHEMBL2108129, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:physically_interacts_with)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(kp=infores:rtx-kg2)",
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
        "expand(kp=infores:biothings-multiomics-clinical-risk)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_wellness_kp():
    actions_list = [
        "add_qnode(ids=UniProtKB:O00533, categories=biolink:Protein, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:biothings-multiomics-wellness)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_drug_response_kp():
    actions_list = [
        "add_qnode(ids=NCBIGene:7157, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:SmallMolecule, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:associated_with_sensitivity_to)",
        "expand(kp=infores:biothings-multiomics-biggim-drug-response)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_multiomics_tumor_gene_mutation_kp():
    actions_list = [
        "add_qnode(ids=MONDO:0018177, key=n00)",
        "add_qnode(categories=biolink:Gene, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:biothings-tcga-mut-freq)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_many_kp_query():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL112, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:interacts_with)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, timeout=10)


def test_entity_to_entity_query():
    actions_list = [
        "add_qnode(ids=NCBIGene:375, categories=biolink:Gene, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0, predicates=biolink:entity_negatively_regulates_entity)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_1516_single_quotes_in_ids():
    actions = [
        "add_qnode(key=n0,ids=UniProtKB:P00491)",
        "add_qnode(key=n1)",
        "add_qedge(key=e01,subject=n0,object=n1)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_input_curie_remapping():
    actions = [
        "add_qnode(key=n0, ids=KEGG.COMPOUND:C02700)",
        "add_qnode(key=n1, categories=biolink:Protein)",
        "add_qedge(key=e01, subject=n0, object=n1)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    assert "KEGG.COMPOUND:C02700" in nodes_by_qg_id["n0"]
    assert "formylkynurenine" in nodes_by_qg_id["n0"]["KEGG.COMPOUND:C02700"].name.lower()


def test_constraint_validation():
    query = {
      "edges": {
        "e00": {
          "object": "n01",
          "predicates": ["biolink:physically_interacts_with"],
          "subject": "n00",
          "constraints": [{"id": "test_edge_constraint_1", "name": "test name edge", "operator": "<", "value": 1.0},
                          {"id": "test_edge_constraint_2", "name": "test name edge", "operator": ">", "value": 0.5}]
        }
      },
      "nodes": {
        "n00": {
          "categories": ["biolink:ChemicalEntity"],
          "ids": ["CHEMBL.COMPOUND:CHEMBL112"]
        },
        "n01": {
          "categories": ["biolink:Protein"],
          "constraints": [{"id": "test_node_constraint", "name": "test name node", "operator": "<", "value": 1.0}]
        }
      }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, should_throw_error=True,
                                                                        error_code="UnsupportedConstraint")


def test_canonical_predicates():
    actions = [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL945)",
        "add_qnode(key=n01, categories=biolink:BiologicalEntity)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:participates_in)",  # Not canonical
        "add_qnode(key=n02, categories=biolink:Disease)",
        "add_qedge(key=e01, subject=n00, object=n02, predicates=biolink:treats)",  # Canonical form
        "add_qnode(key=n03, categories=biolink:BiologicalEntity)",
        "add_qedge(key=e02, subject=n00, object=n03, predicates=biolink:has_participant)",  # Canonical form
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    e00_predicates = {edge.predicate for edge in edges_by_qg_id["e00"].values()}
    e01_predicates = {edge.predicate for edge in edges_by_qg_id["e01"].values()}
    e02_predicates = {edge.predicate for edge in edges_by_qg_id["e02"].values()}
    assert "biolink:has_participant" in e00_predicates and "biolink:participates_in" not in e00_predicates
    assert "biolink:treats" in e01_predicates and "biolink:treated_by" not in e01_predicates
    assert "biolink:has_participant" in e02_predicates and "biolink:participates_in" not in e02_predicates


@pytest.mark.slow
@pytest.mark.external
def test_curie_prefix_conversion_1537():
    actions = [
        "add_qnode(key=n0, ids=NCBIGene:60412, categories=biolink:Gene)",
        "add_qnode(key=n1, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:related_to)",
        "expand(kp=infores:connections-hypothesis)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


@pytest.mark.slow
@pytest.mark.external
def test_merging_node_attributes_1450():
    actions = [
        "add_qnode(key=n0, ids=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:treats)",
        "expand(kp=infores:biothings-explorer)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    num_attributes_a = len(nodes_by_qg_id["n0"]["CHEMBL.COMPOUND:CHEMBL112"].attributes)
    actions = [
        "add_qnode(key=n0, ids=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:treats)",
        "expand(kp=infores:rtx-kg2)",
        "expand(kp=infores:biothings-explorer)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    num_attributes_b = len(nodes_by_qg_id["n0"]["CHEMBL.COMPOUND:CHEMBL112"].attributes)
    assert num_attributes_a == num_attributes_b


@pytest.mark.external
def test_icees_dili():
    actions = [
        "add_qnode(key=n0, ids=NCIT:C28421, categories=biolink:PhenotypicFeature)",
        "add_qnode(key=n1, categories=biolink:NamedThing)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:correlated_with)",
        "expand(kp=infores:icees-dili)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


@pytest.mark.external
def test_icees_asthma():
    actions = [
        "add_qnode(key=n0, ids=NCIT:C28421, categories=biolink:PhenotypicFeature)",
        "add_qnode(key=n1, categories=biolink:NamedThing)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:correlated_with)",
        "expand(kp=infores:icees-asthma)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


@pytest.mark.slow
def test_almost_cycle_1565():
    actions_list = [
        "add_qnode(ids=MONDO:0010161, key=n0)",
        "add_qnode(categories=biolink:Gene, key=n1)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n2)",
        "add_qedge(subject=n1, object=n0, key=e0, predicates=biolink:related_to)",
        "add_qedge(subject=n1, object=n2, key=e1, predicates=biolink:related_to)",
        "add_qedge(subject=n0, object=n2, key=e2, predicates=biolink:related_to)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.slow
def test_fda_approved_query_simple():
    query = {
        "nodes": {
            "n0": {
                "ids": [
                    "MONDO:0000888"
                ]
            },
            "n1": {
                "categories": [
                    "biolink:ChemicalEntity"
                ],
                "constraints": [
                    {
                        "id": "biolink:highest_FDA_approval_status",
                        "name": "highest FDA approval status",
                        "operator": "==",
                        "value": "regular approval"
                    }
                ]
            }
        },
        "edges": {
            "e0": {
                "subject": "n1",
                "object": "n0",
                "predicates": [
                    "biolink:treats"
                ]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


@pytest.mark.slow
def test_fda_approved_query_workflow_a9_egfr_advanced():
    query_unconstrained = {
      "nodes": {
        "n0": {
          "categories": [
            "biolink:SmallMolecule"
          ]
        },
        "n1": {
          "ids": [
            "NCBIGene:1956"
          ]
        }
      },
      "edges": {
        "e0": {
          "subject": "n0",
          "object": "n1",
          "predicates": [
            "biolink:decreases_abundance_of",
            "biolink:decreases_activity_of",
            "biolink:decreases_expression_of",
            "biolink:decreases_synthesis_of",
            "biolink:increases_degradation_of",
            "biolink:disrupts",
            "biolink:entity_negatively_regulates_entity"
          ]
        }
      }
    }
    nodes_by_qg_id_unconstrained, edges_by_qg_id_unconstrained = _run_query_and_do_standard_testing(json_query=query_unconstrained)

    query_constrained = query_unconstrained
    fda_approved_constraint = {
        "id": "biolink:highest_FDA_approval_status",
        "name": "highest FDA approval status",
        "operator": "==",
        "value": "regular approval"
    }
    query_constrained["nodes"]["n0"]["constraints"] = [fda_approved_constraint]
    nodes_by_qg_id_constrained, edges_by_qg_id_constrained = _run_query_and_do_standard_testing(json_query=query_constrained)

    assert len(nodes_by_qg_id_constrained["n0"]) < len(nodes_by_qg_id_unconstrained["n0"])


def test_inverted_treats_handling():
    actions = [
        "add_qnode(key=n0, ids=MONDO:0005077)",
        "add_qnode(key=n1, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e0, subject=n0, object=n1, predicates=biolink:treats)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_expand.py'])
