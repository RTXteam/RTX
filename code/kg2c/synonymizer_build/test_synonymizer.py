"""
Usage:
    Run all tests: pytest -v test_synonymizer.py
    Run a single test: pytest -v test_synonymizer.py -k test_example
"""
import os
import sys
from typing import Set

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

print(f"Using synonymizer {pytest.synonymizer_name}")
synonymizer = NodeSynonymizer(sqlite_file_name=pytest.synonymizer_name)


def canonical_check(curie: str):
    canonical_info = synonymizer.get_canonical_curies(curie)
    print(f"Canonical info: {canonical_info}")
    assert canonical_info.get(curie)


def equivalent_nodes_check(curie: str, trusted_equivalent_curies: Set[str]):
    equivalent_nodes = synonymizer.get_equivalent_nodes(curie)
    print(f"Equivalent nodes: {equivalent_nodes}")
    assert equivalent_nodes.get(curie)
    equivalent_node_ids = set(equivalent_nodes[curie])
    assert trusted_equivalent_curies.issubset(equivalent_node_ids)


def test_parkinsons():
    parkinsons_curie = "DOID:14330"
    synonymizer.print_cluster_table(parkinsons_curie, include_edges=False)
    canonical_check(parkinsons_curie)
    parkinsons_trusted_ids = {"MONDO:0005180", "MESH:D010300", "UMLS:C0030567", "DOID:14330"}
    equivalent_nodes_check(parkinsons_curie, parkinsons_trusted_ids)


def test_acetaminophen():
    acetaminophen_curie = "CHEMBL.COMPOUND:CHEMBL112"
    synonymizer.print_cluster_table(acetaminophen_curie, include_edges=False)
    canonical_check(acetaminophen_curie)
    acetaminophen_trusted_ids = {"CHEMBL.COMPOUND:CHEMBL112", "PUBCHEM.COMPOUND:1983",
                                 "CHEBI:46195", "RXNORM:161", "DRUGBANK:DB00316",
                                 "UMLS:C0000970", "MESH:D000082", "DrugCentral:52"}
    equivalent_nodes_check(acetaminophen_curie, acetaminophen_trusted_ids)
