#!/bin/env python3
"""
Usage:
    Run all expand tests: pytest -v test_ARAX_expand.py
    Run a single test: pytest -v test_ARAX_expand.py -k test_branched_query
"""
import sys
import os
from typing import List, Dict, Optional

import pytest
import yaml

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse
import Expand.expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.attribute import Attribute


def _run_query_and_do_standard_testing(actions: Optional[List[str]] = None, json_query: Optional[dict] = None,
                                       kg_should_be_incomplete=False, debug=False, should_throw_error=False,
                                       error_code: Optional[str] = None, timeout: Optional[int] = None,
                                       return_message: bool = False) -> tuple:
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
        print_nodes(nodes_by_qg_id)
        print_edges(edges_by_qg_id)
        print_counts_by_qgid(nodes_by_qg_id, edges_by_qg_id)
        print(response.show(level=ARAXResponse.DEBUG))

    # Run standard testing (applies to every test case)
    assert eu.qg_is_fulfilled(response.original_query_graph, dict_kg, enforce_required_only=True) or kg_should_be_incomplete or should_throw_error
    check_for_orphans(nodes_by_qg_id, edges_by_qg_id)
    check_property_format(nodes_by_qg_id, edges_by_qg_id)

    return (nodes_by_qg_id, edges_by_qg_id, message) if return_message else (nodes_by_qg_id, edges_by_qg_id)


def print_counts_by_qgid(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    print(f"KG counts:")
    if nodes_by_qg_id or edges_by_qg_id:
        for qnode_key, corresponding_nodes in sorted(nodes_by_qg_id.items()):
            print(f"  {qnode_key}: {len(corresponding_nodes)}")
        for qedge_key, corresponding_edges in sorted(edges_by_qg_id.items()):
            print(f"  {qedge_key}: {len(corresponding_edges)}")
    else:
        print("  KG is empty")


def print_nodes(nodes_by_qg_id: Dict[str, Dict[str, Node]]):
    for qnode_key, nodes in sorted(nodes_by_qg_id.items()):
        for node_key, node in sorted(nodes.items()):
            print(f"{qnode_key}: {node.categories}, {node_key}, {node.name}, {node.qnode_keys}, "
                  f"{node.query_ids if hasattr(node, 'query_ids') else ''}")


def print_edges(edges_by_qg_id: Dict[str, Dict[str, Edge]]):
    for qedge_key, edges in sorted(edges_by_qg_id.items()):
        for edge_key, edge in sorted(edges.items()):
            print(f"{qedge_key}: {edge_key}, {edge.subject}--{edge.predicate}->{edge.object}, {edge.qedge_keys}")


def check_for_orphans(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
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


def check_property_format(nodes_by_qg_id: Dict[str, Dict[str, Node]], edges_by_qg_id: Dict[str, Dict[str, Edge]]):
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


def get_primary_knowledge_source(edge: Edge) -> str:
    return next(source.resource_id for source in edge.sources if source.resource_role == "primary_knowledge_source")

def get_support_graphs_attribute(edge: Edge) -> any:
    sg_attrs = [attribute for attribute in edge.attributes if attribute.attribute_type_id == "biolink:support_graphs"]
    assert len(sg_attrs) <= 1
    return sg_attrs[0] if sg_attrs else None


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
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:treats_or_applied_or_studied_to_treat)",
        "expand(kp=infores:rtx-kg2)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


def test_771_continue_if_no_results_query():
    actions_list = [
        "add_qnode(ids=UniProtKB:P14136, key=n00)",
        "add_qnode(ids=NOTAREALCURIE, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, kg_should_be_incomplete=True)
    assert 'n01' not in nodes_by_qg_id
    assert 'e00' not in edges_by_qg_id


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
        "add_qedge(subject=n00, object=n01, predicates=biolink:has_phenotype, key=e00)",
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
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:treats_or_applied_or_studied_to_treat)",
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
                                                                        error_code="QueryGraphNoIds")


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


@pytest.mark.skip(reason="retire DTD")
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
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM-DATA:0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


# @pytest.mark.slow
@pytest.mark.skip(reason="retire DTD")
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
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].attribute_type_id == "EDAM-DATA:0951" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])
    assert all([edges_by_qg_id[qedge_key][edge_key].attributes[0].value_url == "https://doi.org/10.1101/765305" for qedge_key in edges_by_qg_id for edge_key in edges_by_qg_id[qedge_key]])


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
        "add_qnode(ids=NCBIGene:7157, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:molecularly_interacts_with)",
        "expand(kp=infores:spoke)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)


@pytest.mark.external
def test_spoke_query_2():
    actions_list = [
        "add_qnode(ids=NCBIGene:7157, categories=biolink:Gene, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:molecularly_interacts_with)",
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
        "add_qedge(subject=n01, object=n00, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:causes, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    contraindicated_pairs = {tuple(sorted([edge.subject, edge.object])) for edge in edges_by_qg_id["e01"].values()}
    assert contraindicated_pairs

    # Then exclude the contraindicated edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n01, object=n00, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
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
    exclude_curies = ", ".join(['GO:0006915'])
    # First run a query without any kryptonite edges to get a baseline
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01, is_set=true)",
        f"add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:causes)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:affects)",
        # 'Exclude' portion (just optional for now to get a baseline)
        f"add_qnode(categories=biolink:Pathway, key=nx0, option_group_id=1, ids=[{exclude_curies}])",
        "add_qedge(subject=n01, object=nx0, key=ex0, option_group_id=1, predicates=biolink:related_to)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    nodes_used_by_kryptonite_edge = eu.get_node_keys_used_by_edges(edges_by_qg_id["ex0"])
    n01_nodes_to_blow_away = set(nodes_by_qg_id["n01"]).intersection(nodes_used_by_kryptonite_edge)
    assert n01_nodes_to_blow_away
    assert len(n01_nodes_to_blow_away) < len(nodes_by_qg_id["n01"])

    # Then use a kryptonite edge and make sure the appropriate nodes are blown away
    actions_list = [
        "add_qnode(ids=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01, is_set=true)",
        f"add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n01, object=n00, key=e00, predicates=biolink:causes)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:affects)",
        # 'Exclude' portion
        f"add_qnode(categories=biolink:Pathway, key=nx0, ids=[{exclude_curies}])",
        "add_qedge(subject=n01, object=nx0, key=ex0, exclude=True, predicates=biolink:related_to)",
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
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes_to_condition, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2, edge_key=e00)",
        "expand(kp=infores:rtx-kg2, edge_key=e01)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_a, edges_by_qg_id_a = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes_to_condition, exclude=true, key=e01)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id_b, edges_by_qg_id_b = _run_query_and_do_standard_testing(actions_list)
    actions_list = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:predisposes_to_condition, exclude=true, key=e01)",
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
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
        "add_qedge(subject=n00, object=n01, predicates=biolink:treats_or_applied_or_studied_to_treat, key=e00)",
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
        "add_qedge(key=e0, subject=n1, object=n0, predicates=biolink:subject_of_treatment_application_or_study_for_treatment_by)",
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
    assert not any(edge for edge in edges_by_qg_id["e00"].values() if edge.predicate == "biolink:related_to")


@pytest.mark.skip(reason="Dev testing for domain range exclusion")
def test_domain_range_exclusion():
    actions_list = [
        "add_qnode(ids=UMLS:C1510438, key=n00)",
        "add_qnode(categories=biolink:Disease, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:diagnoses)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    assert False


@pytest.mark.slow
def test_issue_1373_pinned_curies():
    actions_list = [
        "add_qnode(ids=CHEMBL.COMPOUND:CHEMBL2108129, key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:related_to)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:related_to)",
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


def test_qualified_regulates_query():
    query = {
        "nodes": {
            "n0": {
                 "ids": ["NCBIGene:7157"]
            },
            "n1": {
                "categories": ["biolink:Gene"]
            }
        },
        "edges": {
            "e0": {
                "subject": "n0",
                "object": "n1",
                "qualifier_constraints": [
                    {"qualifier_set": [
                        {"qualifier_type_id": "biolink:qualified_predicate",
                         "qualifier_value": "biolink:causes"},
                        # {"qualifier_type_id": "biolink:object_direction_qualifier",
                        #  "qualifier_value": "decreased"}, # for RTX issue 2068
                        #                                   # see also RTX-KG2 issue 339
                        #                                   # Uncomment to test in KG2.8.5
                        {"qualifier_type_id": "biolink:object_aspect_qualifier",
                         "qualifier_value": "activity"}
                    ]}
                ],
                "attribute_constraints": [
                    {
                        "id": "knowledge_source",
                        "name": "knowledge source",
                        "value": ["infores:rtx-kg2"],
                        "operator": "==",
                        "not": False
                    }
                ]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


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


def test_constraint_validation():
    query = {
      "edges": {
        "e00": {
          "object": "n01",
          "predicates": ["biolink:physically_interacts_with"],
          "subject": "n00",
          "attribute_constraints": [{"id": "test_edge_constraint_1", "name": "test name edge", "operator": "<", "value": 1.0},
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


def test_edge_constraints():
    query = {
            "nodes": {
                "n00": {
                    "ids": ["CHEMBL.COMPOUND:CHEMBL112"]
                },
                "n01": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "e00": {
                    "object": "n00",
                    "subject": "n01",
                    "attribute_constraints": [
                        {
                            "id": "knowledge_source",
                            "name": "knowledge source",
                            "value": ["infores:rtx-kg2","infores:arax","infores:drugbank"],
                            "operator": "==",
                            "not": False
                        }
                    ]
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


def test_canonical_predicates():
    actions = [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL945)",
        "add_qnode(key=n01, categories=biolink:BiologicalEntity)",
        "add_qedge(key=e00, subject=n00, object=n01, predicates=biolink:participates_in)",  # Not canonical
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    e00_predicates = {edge.predicate for edge in edges_by_qg_id["e00"].values()}
    assert "biolink:has_participant" in e00_predicates and "biolink:participates_in" not in e00_predicates


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
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:treats_or_applied_or_studied_to_treat)",
        "expand(kp=infores:biothings-explorer)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    num_attributes_a = len(nodes_by_qg_id["n0"]["CHEMBL.COMPOUND:CHEMBL112"].attributes)
    actions = [
        "add_qnode(key=n0, ids=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e01, subject=n0, object=n1, predicates=biolink:treats_or_applied_or_studied_to_treat)",
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
                    "biolink:treats_or_applied_or_studied_to_treat"
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
            "biolink:related_to"
          ]
        }
      }
    }
    nodes_by_qg_id_unconstrained, edges_by_qg_id_unconstrained = _run_query_and_do_standard_testing(json_query=query_unconstrained, timeout=30)
    assert nodes_by_qg_id_unconstrained.get("n1")

    query_constrained = query_unconstrained
    fda_approved_constraint = {
        "id": "biolink:highest_FDA_approval_status",
        "name": "highest FDA approval status",
        "operator": "==",
        "value": "regular approval"
    }
    query_constrained["nodes"]["n0"]["constraints"] = [fda_approved_constraint]
    nodes_by_qg_id_constrained, edges_by_qg_id_constrained = _run_query_and_do_standard_testing(json_query=query_constrained, timeout=30)

    assert len(nodes_by_qg_id_constrained["n0"]) < len(nodes_by_qg_id_unconstrained["n0"])


def test_inverted_treats_handling():
    actions = [
        "add_qnode(key=n0, ids=MONDO:0005077)",
        "add_qnode(key=n1, categories=biolink:ChemicalEntity)",
        "add_qedge(key=e0, subject=n0, object=n1, predicates=biolink:treats_or_applied_or_studied_to_treat)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)


def test_xdtd_expand():
    query = {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats_or_applied_or_studied_to_treat"],
                    "knowledge_type": "inferred"
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id, message = _run_query_and_do_standard_testing(json_query=query, return_message=True)
    assert message.auxiliary_graphs
    for edge in edges_by_qg_id["t_edge"].values():
        inferred_edge = False
        for source in edge.sources:
            if source.resource_role == "primary_knowledge_source" and source.resource_id == "infores:arax":
                inferred_edge = True
        # Perform Tests only for inferred edges
        if inferred_edge:
            assert edge.attributes
            support_graph_attributes = [attribute for attribute in edge.attributes if attribute.attribute_type_id == "biolink:support_graphs"]
            ## some xdtd predictions don't have support_graphs, so skip them
            if len(support_graph_attributes) > 0:
                assert support_graph_attributes
                assert len(support_graph_attributes) == 1
                support_graph_attribute = support_graph_attributes[0]
                assert support_graph_attribute.value[0] in message.auxiliary_graphs


@pytest.mark.slow
def test_xdtd_different_categories():
    query = {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:Drug"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats_or_applied_or_studied_to_treat"],
                    "knowledge_type": "inferred"
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)
    query = {
        "nodes": {
            "disease": {
                "ids": ["MONDO:0015564"],
                "categories": ["biolink:Disease"]
            },
            "chemical": {
                "categories": ["biolink:Drug"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:treats_or_applied_or_studied_to_treat"],
                "knowledge_type": "inferred"
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)
    query = {
        "nodes": {
            "disease": {
                "ids": ["MONDO:0015564"],
                "categories": ["biolink:DiseaseOrPhenotypicFeature"]
            },
            "chemical": {
                "categories": ["biolink:ChemicalMixture"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:treats_or_applied_or_studied_to_treat"],
                "knowledge_type": "inferred"
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


def test_xdtd_multiple_categories():
    query = {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:Drug", "biolink:ChemicalMixture"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:treats_or_applied_or_studied_to_treat"],
                    "knowledge_type": "inferred"
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


def test_xdtd_different_predicates():
    query = {
            "nodes": {
                "disease": {
                    "ids": ["MONDO:0015564"]
                },
                "chemical": {
                    "categories": ["biolink:Drug", "biolink:ChemicalMixture"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:ameliorates_condition"],
                    "knowledge_type": "inferred"
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)


def test_xdtd_no_curies():
    query = {
            "nodes": {
                "disease": {
                },
                "chemical": {
                    "categories": ["biolink:Drug", "biolink:ChemicalMixture"],
                    "ids": ["CHEMBL:CHEMBL1234"]
                }
            },
            "edges": {
                "t_edge": {
                    "object": "disease",
                    "subject": "chemical",
                    "predicates": ["biolink:ameliorates_condition"],
                    "knowledge_type": "inferred"
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, should_throw_error=True)


@pytest.mark.skip
def test_xdtd_with_other_edges():
    query = {
        "nodes": {
            "disease": {
                "ids": ["UMLS:C4023597"]
            },
            "chemical": {
                "categories": ["biolink:Drug", "biolink:ChemicalMixture"]
            },
            "gene": {
                "categories": ["biolink:Gene", "biolink:Protein"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:affects"],
                "knowledge_type": "inferred"
            },
            "non_t_edge": {
                "object": "gene",
                "subject": "chemical"
            }
        }
    }
    # FIXME: this test is failing since the ability to mix inferred with lookup edges is not yet implemented
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, should_throw_error=True)


def test_xdtd_curie_not_in_db():
    query = {
        "nodes": {
            "disease": {
                "ids": ["MONDO:0021783"]  # this curie has probabilities but no paths in the XDTDdb
            },
            "chemical": {
                "categories": ["biolink:Drug", "biolink:ChemicalMixture"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:treats"],
                "knowledge_type": "inferred"
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, should_throw_error=False)


@pytest.mark.slow
def test_query_ids_mappings():
    query_curies = ["CHEMBL.COMPOUND:CHEMBL112", "DOID:14330"]
    actions_list = [
        f"add_qnode(ids=[{','.join(query_curies)}], key=n00)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00, predicates=biolink:related_to)",
        "expand()",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list, timeout=10)
    # Make sure we actually got some subclass child nodes from KPs
    assert len(nodes_by_qg_id["n00"]) > 2
    for node_key, node in nodes_by_qg_id["n00"].items():
        # Make sure pinned nodes have query_ids filled out
        assert node.query_ids or node_key in query_curies
        # Make sure subclass self-edges were added as appropriate
        for parent_query_id in node.query_ids:
            assert parent_query_id in nodes_by_qg_id["n00"]
    # Make sure unpinned nodes do not have query_ids specified
    for node_key, node in nodes_by_qg_id["n01"].items():
        assert not node.query_ids


@pytest.mark.external
def test_no_query_ids_issue():
    query = {
        "nodes": {
            "n1": {
                "categories": [
                    "biolink:GrossAnatomicalStructure"
                ],
                "ids": [
                    "UBERON:0009912",
                    "UBERON:0002535",
                    "UBERON:0000019",
                    "UBERON:0002365",
                    "UBERON:0000017",
                    "UBERON:0000970",
                    "UBERON:0001831",
                    "UBERON:0016410",
                    "UBERON:0001737",
                    "UBERON:0000945"
                ]
            },
            "n2": {
                "categories": [
                    "biolink:Gene"
                ]
            }
        },
        "edges": {
            "e1": {
                "subject": "n1",
                "object": "n2",
                "predicates": [
                    "biolink:expresses"
                ],
                "attribute_constraints": [
                    {
                        "id": "knowledge_source",
                        "name": "knowledge source",
                        "value": ["infores:connections-hypothesis"],
                        "operator": "==",
                        "not": False
                    }
                ]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, timeout=45)


@pytest.mark.slow
def test_subclass_answers_for_non_pinned_qnodes():
    query = {
            "nodes": {
                "n0": {
                    "categories": [
                        "biolink:Disease"
                    ],
                    "ids": [
                        "MONDO:0009061"
                    ]
                },
                "n1": {
                    "categories": [
                        "biolink:GrossAnatomicalStructure"
                    ]
                },
                "n2": {
                    "categories": [
                        "biolink:Gene"
                    ]
                },
                "n3": {
                    "categories": [
                        "biolink:Drug",
                        "biolink:SmallMolecule"
                    ]
                }
            },
            "edges": {
                "e0": {
                    "subject": "n0",
                    "object": "n1",
                    "predicates": [
                        "biolink:located_in"
                    ]
                },
                "e1": {
                    "subject": "n1",
                    "object": "n2",
                    "predicates": [
                        "biolink:expresses"
                    ]
                },
                "e2": {
                    "subject": "n3",
                    "object": "n2",
                    "predicates": [
                        "biolink:affects"
                    ]
                }
            }
        }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query, timeout=75)


def test_kp_list():
    actions = [
        "add_qnode(key=qg0, ids=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(key=qg1, categories=biolink:Protein)",
        "add_qedge(subject=qg1, object=qg0, key=qe0, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=qe0, kp=[infores:rtx-kg2, infores:molepro])",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions, timeout=30)


def test_missing_epc_attributes():
    actions = [
        "add_qnode(name=Parkinson's disease, key=n0)",
        "add_qnode(categories=biolink:Drug, key=n1)",
        "add_qedge(subject=n1, object=n0, key=e0, predicates=biolink:predisposes_to_condition)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions)
    for qedge_key, edges in edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            primary_knowledge_sources = {source.resource_id for source in edge.sources
                                         if source.resource_role == "primary_knowledge_source"}
            assert primary_knowledge_sources
            if "infores:semmeddb" in primary_knowledge_sources:
                assert edge.attributes
                publications = [attribute.value for attribute in edge.attributes
                                if attribute.attribute_type_id == "biolink:publications"]
                assert publications


def test_kg2_version():
    query = {
      "nodes": {
        "n00": {
          "ids": ["RTX:KG2c"]
        }
      },
      "edges": {}
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)

    # First grab KG2 version from the KG2c build node
    assert nodes_by_qg_id["n00"]
    assert len(nodes_by_qg_id["n00"]) == 1
    build_node = nodes_by_qg_id["n00"]["RTX:KG2c"]
    kg2c_build_node_version = build_node.name.replace("RTX-KG", "").strip("c")
    print(f"KG2 version from KG2c build node is: {kg2c_build_node_version}")

    # Then grab KG2 version from the OpenAPI spec
    code_dir = os.path.dirname(os.path.abspath(__file__)) + "/../../"
    kg2_openapi_yaml_path = f"{code_dir}/UI/OpenAPI/specifications/export/KG2/1.5.0/openapi.yaml"
    with open(kg2_openapi_yaml_path) as kg2_api_file:
        kg2_openapi_configuration = yaml.safe_load(kg2_api_file)
        kg2_openapi_version = kg2_openapi_configuration["info"]["version"]
    print(f"KG2 version from KG2 openapi.yaml file is: {kg2_openapi_version}")

    assert kg2c_build_node_version == kg2_openapi_version


def test_klat_attributes():
    actions_list = [
        "add_qnode(key=n0, ids=DRUGBANK:DB00394)",
        "add_qnode(key=n1, categories=biolink:Disease)",
        "add_qedge(key=e0, subject=n1, object=n0, predicates=biolink:treats_or_applied_or_studied_to_treat)",
        "expand(kp=infores:rtx-kg2)",
        "return(message=true, store=false)"
    ]
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(actions_list)
    for edge_key, edge in edges_by_qg_id["e0"].items():
        assert any(attribute.attribute_type_id == "biolink:knowledge_level" for attribute in edge.attributes)
        assert any(attribute.attribute_type_id == "biolink:agent_type" for attribute in edge.attributes)
        assert all(isinstance(attribute.value, str) for attribute in edge.attributes
                   if attribute.attribute_type_id in {"biolink:knowledge_level", "biolink:agent_type"})


def test_treats_patch_issue_2328_a():
    query = {
        "nodes": {
            "disease": {
                "ids": ["MONDO:0015564"]
            },
            "chemical": {
                "categories": ["biolink:ChemicalEntity"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:treats"],
                "knowledge_type": "inferred",
                "attribute_constraints": [
                    {
                        "id": "knowledge_source",
                        "name": "knowledge source",
                        "value": ["infores:rtx-kg2"],
                        "operator": "=="
                    }
                ]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, message = _run_query_and_do_standard_testing(json_query=query, return_message=True)
    assert edges_by_qg_id["t_edge"]
    # Make sure the KG2 edges, which are higher-level treats edges, are in the KG (used as support edges)
    creative_expand_treats_edges = [edge for edge_key, edge in message.knowledge_graph.edges.items()
                                    if edge_key.startswith("creative_expand")]
    support_edge_keys = set()
    for edge in creative_expand_treats_edges:
        aux_graph_keys = get_support_graphs_attribute(edge).value
        assert aux_graph_keys
        for aux_graph_key in aux_graph_keys:
            aux_graph = message.auxiliary_graphs[aux_graph_key]
            support_edge_keys.update(set(aux_graph.edges))
    support_edges = [message.knowledge_graph.edges[edge_key] for edge_key in support_edge_keys]

    assert any(source.resource_id == "infores:rtx-kg2" for edge in support_edges for source in edge.sources)
    assert not any(source.resource_id == "infores:semmeddb" for edge in support_edges for source in edge.sources)

def test_treats_patch_issue_2328_b():
    # Verify that the edge editing doesn't happen outside of inferred mode
    query = {
        "nodes": {
            "disease": {
                "ids": ["MONDO:0015564"]
            },
            "chemical": {
                "categories": ["biolink:ChemicalEntity"]
            }
        },
        "edges": {
            "t_edge": {
                "object": "disease",
                "subject": "chemical",
                "predicates": ["biolink:treats_or_applied_or_studied_to_treat", "biolink:applied_to_treat"],
                "attribute_constraints": [
                    {
                        "id": "knowledge_source",
                        "name": "knowledge source",
                        "value": ["infores:rtx-kg2"],
                        "operator": "=="
                    }
                ]
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id = _run_query_and_do_standard_testing(json_query=query)
    assert edges_by_qg_id["t_edge"]
    kg2_edges_treats_or = [edge for edge in edges_by_qg_id["t_edge"].values()
                           if any(source.resource_id == "infores:rtx-kg2" for source in edge.sources)]
    print(f"Answer includes {len(kg2_edges_treats_or)} edges from KG2")
    assert kg2_edges_treats_or
    assert any(edge for edge in kg2_edges_treats_or if edge.predicate == "biolink:treats_or_applied_or_studied_to_treat")
    assert any(edge for edge in kg2_edges_treats_or if edge.predicate == "biolink:applied_to_treat")


@pytest.mark.external
def test_creative_treats_predicate_alteration_2412():
    query = {
        "nodes": {
            "n00": {
                "ids": ["MONDO:0018958"]
            },
            "n01": {
                "categories": ["biolink:SmallMolecule"]
            }
        },
        "edges": {
            "e00": {
                "subject": "n01",
                "object": "n00",
                "predicates": ["biolink:treats"],
                "knowledge_type": "inferred"
            }
        }
    }
    nodes_by_qg_id, edges_by_qg_id, message = _run_query_and_do_standard_testing(json_query=query, return_message=True)

    # Make sure we appear to have creative expand treats edges
    assert edges_by_qg_id and edges_by_qg_id.get("e00")
    assert any(edge_key for edge_key in edges_by_qg_id["e00"] if edge_key.startswith("creative_expand"))
    primary_sources_e00 = {get_primary_knowledge_source(edge) for edge in edges_by_qg_id["e00"].values()}
    print(f"primary_knowledge_sources are: {primary_sources_e00}")
    assert "infores:arax" in primary_sources_e00

    # Make sure 'support' edges, like from ROBOKOP, are present in the KG
    primary_sources_all = {get_primary_knowledge_source(edge) for edges_dict in edges_by_qg_id.values()
                           for edge in edges_dict.values()}
    assert "infores:automat-robokop" in primary_sources_all

    # Make sure that creative expand treats edges have support graphs that actually exist
    for edge_key, edge in edges_by_qg_id["e00"].items():
        if get_primary_knowledge_source(edge) == "infores:arax":
            support_graph_attr = get_support_graphs_attribute(edge)
            assert support_graph_attr
            aux_graph_keys = eu.convert_to_set(support_graph_attr.value)
            assert aux_graph_keys.issubset(message.auxiliary_graphs)
            for aux_graph_key in aux_graph_keys:
                aux_graph = message.auxiliary_graphs[aux_graph_key]
                assert set(aux_graph.edges).issubset(message.knowledge_graph.edges)



if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_expand.py'])
