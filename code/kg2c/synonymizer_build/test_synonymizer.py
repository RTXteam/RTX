"""
Usage:
    Run all tests: pytest -v test_synonymizer.py
    Run a single test: pytest -v test_synonymizer.py -k test_example
"""
import os
import sys
from typing import Set, Optional

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

print(f"Using synonymizer {pytest.synonymizer_name}")
synonymizer = NodeSynonymizer(sqlite_file_name=pytest.synonymizer_name)


def canonical_check(curie: str):
    canonical_info = synonymizer.get_canonical_curies(curie)
    print(f"Canonical info: {canonical_info}")
    assert canonical_info.get(curie)


def equivalent_nodes_check(curie: str,
                           trusted_equivalent_curies: Set[str],
                           unequivalent_curies: Optional[Set[str]] = None):
    equivalent_nodes = synonymizer.get_equivalent_nodes(curie)
    print(f"Equivalent nodes: {equivalent_nodes}")
    assert equivalent_nodes.get(curie)
    equivalent_node_ids = set(equivalent_nodes[curie])
    assert trusted_equivalent_curies.issubset(equivalent_node_ids)
    if unequivalent_curies:
        assert not unequivalent_curies.intersection(equivalent_node_ids)


def test_parkinsons():
    parkinsons_curie = "DOID:14330"
    synonymizer.print_cluster_table(parkinsons_curie, include_edges=False)
    canonical_check(parkinsons_curie)
    parkinsons_trusted_ids = {"MONDO:0005180", "MESH:D010300", "UMLS:C0030567", "DOID:14330"}
    other_parkinson_related_ids = {"CHV:0000033687", "MESH:C566017", "UMLS:C1469632", "HP:0002322",
                                   "CHV:0000040804", "UMLS:C0586392", "MONDO:0957576", "UMLS:C2775684",
                                   "MONDO:0009830", "MONDO:0017639", "NCIT:C54901", "CHEBI:48407"}
    equivalent_nodes_check(parkinsons_curie, parkinsons_trusted_ids, unequivalent_curies=other_parkinson_related_ids)


def test_acetaminophen():
    acetaminophen_curie = "CHEMBL.COMPOUND:CHEMBL112"
    synonymizer.print_cluster_table(acetaminophen_curie, include_edges=False)
    canonical_check(acetaminophen_curie)
    acetaminophen_trusted_ids = {"CHEMBL.COMPOUND:CHEMBL112", "PUBCHEM.COMPOUND:1983",
                                 "CHEBI:46195", "RXNORM:161", "DRUGBANK:DB00316",
                                 "UMLS:C0000970", "MESH:D000082", "DrugCentral:52",
                                 "UMLS:C0699142", "UMLS:C1360105"}  # Tylenol and a dosage form of acetaminophen
    other_acetaminophen_related_ids = {"CHEBI:135115", "MESH:C045626", "UMLS:C0722198", "RXNORM:1172562",
                                       "UMLS:C0720332", "RXNORM:217020", "UMLS:C1604287", "RXNORM:1299646"}
    equivalent_nodes_check(acetaminophen_curie, acetaminophen_trusted_ids,
                           unequivalent_curies=other_acetaminophen_related_ids)


def test_brca1():
    brca1_curie = "NCBIGene:672"
    synonymizer.print_cluster_table(brca1_curie, include_edges=False)
    canonical_check(brca1_curie)
    brca1_trusted_ids = {"NCBIGene:672", "HGNC:1100", "PR:P38398", "UMLS:C0376571",
                         "UMLS:C1528558", "UniProtKB:P38398"}
    brca2_ids = {"NCBIGene:675", "UniProtKB:P51587"}
    equivalent_nodes_check(brca1_curie, brca1_trusted_ids, unequivalent_curies=brca2_ids)


def test_adams_oliver():
    adams_oliver_curie = "MONDO:0007034"
    synonymizer.print_cluster_table(adams_oliver_curie, include_edges=False)
    canonical_check(adams_oliver_curie)
    adams_oliver_trusted_ids = {"MONDO:0007034", "DOID:0060227", "UMLS:C0265268", "MESH:C538225"}
    adams_oliver_subtypes = {"MONDO:0024506", "UMLS:C4551482", "MONDO:0013635", "OMIM:614219",
                             "MONDO:0013895", "OMIM:614814", "MONDO:0014124", "MONDO:0014459",
                             "MONDO:0014703", "OMIM:616589", "UMLS:C4225271"}
    equivalent_nodes_check(adams_oliver_curie, adams_oliver_trusted_ids, unequivalent_curies=adams_oliver_subtypes)


def test_lumbar_vertebra():
    lumbar_vertebra_curie = "UBERON:0002414"
    synonymizer.print_cluster_table(lumbar_vertebra_curie)
    canonical_check(lumbar_vertebra_curie)
    lumbar_vertebra_trusted_ids = {"UBERON:0002414", "FMA:9921", "MESH:D008159"}
    other_lumbar_related_ids = {"UMLS:C1518034", "UMLS:C0738840", "FMA:58287", "UBERON:0007716",
                                "UBERON:0004617", "UBERON:0005855", "UBERON:0002792"}
    equivalent_nodes_check(lumbar_vertebra_curie, lumbar_vertebra_trusted_ids,
                           unequivalent_curies=other_lumbar_related_ids)
