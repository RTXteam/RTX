#!/bin/env python3
"""
Usage:
    Run all tests: pytest -v test_ARAX_synonymizer.py
    Run a single test: pytest -v test_ARAX_synonymizer.py -k test_example_9
"""
import copy
import json
import os
import sys
import timeit

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

ATRIAL_FIBRILLATION_CURIE = "MONDO:0004981"
PARKINSONS_CURIE = "DOID:14330"
PARKINSONS_CURIE_2 = "MONDO:0005180"
IBUPROFEN_CURIE = "DRUGBANK:DB01050"
ACETAMINOPHEN_CURIE = "CHEMBL.COMPOUND:CHEMBL112"
ACETAMINOPHEN_CURIE_2 = "DRUGBANK:DB00316"
SNCA_CURIE = "NCBIGene:6622"
FAKE_CURIE = "NOTAREALCURIE!"

CERVICAL_RIB_NAME = "Cervical rib"
PARKINSONS_NAME = "Parkinson's disease"
WARFARIN_NAME = "Warfarin"
BRCA1_NAME = "BRCA1"
FAKE_NAME = "THISISNOTAREALNODENAME!"


# ------------------------------- LEGACY TESTS FROM ORIGINAL SYNONYMIZER ------------------------------------- #

def test_example_6b():
    synonymizer = NodeSynonymizer()

    print("==== Get all equivalent nodes in a KG for an input curie ============================")
    tests = [ "DOID:14330", "UMLS:C0031485", "FMA:7203", "MESH:D005199", "CHEBI:5855", "DOID:9281" ]

    t0 = timeit.default_timer()
    for test in tests:
        nodes = synonymizer.get_equivalent_nodes(test)
        print(f"{test} = " + str(nodes))
        print()
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


def test_example_9():
    synonymizer = NodeSynonymizer()

    print("==== Get canonical curies for a set of input curies ============================")
    curies = ["DOID:14330", "UMLS:C0031485", "FMA:7203", "MESH:D005199", "CHEBI:5855", "DOID:9281xxxxx",
              "MONDO:0005520"]
    names = ["phenylketonuria", "ibuprofen", "P06865", "HEXA", "Parkinson's disease", 'supernovas', "Bob's Uncle",
             'double "quotes"', None]

    combined_list = copy.copy(curies)
    combined_list.extend(names)

    t0 = timeit.default_timer()
    canonical_curies = synonymizer.get_canonical_curies(curies=curies, return_all_categories=True)
    print(f"Canonical curies for input normal curies is: \n{canonical_curies}")
    t1 = timeit.default_timer()
    print("Elapsed time: " + str(t1 - t0))
    canonical_curies2 = synonymizer.get_canonical_curies(names=names, return_all_categories=True)
    t2 = timeit.default_timer()
    print("Elapsed time: " + str(t2 - t1))


def test_example_10():
    synonymizer = NodeSynonymizer()
    print("==== Complex name query ============================")
    node_ids = ['CHEMBL.MECHANISM:potassium_channel,_inwardly_rectifying,_subfamily_j,_member_11_opener',
                'CHEMBL.MECHANISM:potassium_channel,_inwardly_rectifying,_subfamily_j,_member_8_opener',
                'CHEMBL.MECHANISM:endothelin_receptor,_et-a/et-b_antagonist',
                'CHEMBL.MECHANISM:amylin_receptor_amy1,_calcr/ramp1_agonist',
                'CHEMBL.MECHANISM:sulfonylurea_receptor_2,_kir6.2_opener',
                'CHEMBL.MECHANISM:sulfonylurea_receptor_1,_kir6.2_blocker',
                'CHEMBL.MECHANISM:amiloride-sensitive_sodium_channel,_enac_blocker',
                'CHEMBL.MECHANISM:hepatitis_c_virus_serine_protease,_ns3/ns4a_inhibitor',
                'CHEMBL.MECHANISM:1,3-beta-glucan_synthase_inhibitor',
                "CHEMBL.MECHANISM:3',5'-cyclic_phosphodiesterase_inhibitor",
                'CHEMBL.MECHANISM:dna_topoisomerase_i,_mitochondrial_inhibitor',
                'CHEMBL.MECHANISM:carbamoyl-phosphate_synthase_[ammonia],_mitochondrial_positive_allosteric_modulator',
                'CHEMBL.MECHANISM:parp_1,_2_and_3_inhibitor', 'CHEMBL.MECHANISM:c-jun_n-terminal_kinase,_jnk_inhibitor',
                'CHEMBL.MECHANISM:voltage-gated_potassium_channel,_kqt;_kcnq2(kv7.2)/kcnq3(kv7.3)_activator',
                'CHEMBL.MECHANISM:hla_class_ii_histocompatibility_antigen,_drb1-10_beta_chain_other',
                'CHEMBL.MECHANISM:hla_class_ii_histocompatibility_antigen,_drb1-15_beta_chain_modulator',
                'CHEMBL.MECHANISM:indoleamine_2,3-dioxygenase_inhibitor',
                'CHEMBL.MECHANISM:5,6-dihydroxyindole-2-carboxylic_acid_oxidase_other',
                'CHEMBL.MECHANISM:amine_oxidase,_copper_containing_inhibitor',
                'CHEMBL.MECHANISM:carnitine_o-palmitoyltransferase_1,_muscle_isoform_inhibitor',
                'CHEMBL.MECHANISM:troponin,_cardiac_muscle_positive_modulator',
                'CHEMBL.MECHANISM:isocitrate_dehydrogenase_[nadp],_mitochondrial_inhibitor']
    t0 = timeit.default_timer()
    canonical_curies = synonymizer.get_canonical_curies(node_ids)
    print(canonical_curies)
    t1 = timeit.default_timer()
    print(json.dumps(canonical_curies, sort_keys=True, indent=2))
    print("Elapsed time: " + str(t1 - t0))


def test_example_11():
    synonymizer = NodeSynonymizer()
    print("==== Get equivalent curies for a set of input curies ============================")
    curies = ["DOID:14330", "UMLS:C0031485", "UNICORN"]
    t0 = timeit.default_timer()
    canonical_curies = synonymizer.get_equivalent_nodes(curies=curies)
    t1 = timeit.default_timer()
    print(json.dumps(canonical_curies, sort_keys=True, indent=2))
    print("Elapsed time: " + str(t1 - t0))


def test_example_12():
    synonymizer = NodeSynonymizer()
    print("==== Get full information in nouveau normalizer format  ============================")
    entities = ["DOID:14330", "anemia", "aardvark"]
    t0 = timeit.default_timer()
    normalizer_results = synonymizer.get_normalizer_results(entities=entities)
    t1 = timeit.default_timer()
    print(json.dumps(normalizer_results, sort_keys=True, indent=2))
    print("Elapsed time: " + str(t1 - t0))


# ------------------------------------------ NEW TESTS ---------------------------------------------------- #

def test_get_canonical_curies_simple():
    curies = [ATRIAL_FIBRILLATION_CURIE, IBUPROFEN_CURIE, SNCA_CURIE]
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(curies)
    print(results)
    assert(len(results) == 3)
    for curie in curies:
        assert results.get(curie)
        assert {"preferred_name", "preferred_category", "preferred_curie"} == set(results[curie])
        assert results[curie]["preferred_curie"]
        assert results[curie]["preferred_category"]
        assert results[curie]["preferred_category"].startswith("biolink:")


def test_get_canonical_curies_single_curie():
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(ATRIAL_FIBRILLATION_CURIE)
    print(results)
    assert len(results) == 1
    assert ATRIAL_FIBRILLATION_CURIE in results
    assert results[ATRIAL_FIBRILLATION_CURIE]


def test_get_canonical_curies_unrecognized():
    curies = [ATRIAL_FIBRILLATION_CURIE, FAKE_CURIE]
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(curies)
    print(results)
    assert results.get(ATRIAL_FIBRILLATION_CURIE)
    assert FAKE_CURIE in results
    assert results[FAKE_CURIE] is None

    results = synonymizer.get_canonical_curies(FAKE_CURIE)
    print(results)
    assert len(results) == 1
    assert FAKE_CURIE in results
    assert results[FAKE_CURIE] is None


def test_get_canonical_curies_by_names():
    synonymizer = NodeSynonymizer()
    names = [CERVICAL_RIB_NAME, WARFARIN_NAME, FAKE_NAME]
    results = synonymizer.get_canonical_curies(names=names)
    print(results)
    assert len(results) == 3
    assert results[FAKE_NAME] is None
    for name in [CERVICAL_RIB_NAME, WARFARIN_NAME]:
        assert results.get(name)
        assert {"preferred_name", "preferred_category", "preferred_curie"} == set(results[name])
        assert results[name]["preferred_curie"]
        assert results[name]["preferred_category"]
        assert results[name]["preferred_category"].startswith("biolink:")


def test_get_canonical_curies_single_name():
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(names=CERVICAL_RIB_NAME)
    print(results)
    assert len(results) == 1
    assert CERVICAL_RIB_NAME in results
    assert results[CERVICAL_RIB_NAME]


def test_get_canonical_curies_by_names_and_curies():
    synonymizer = NodeSynonymizer()
    curies = [ACETAMINOPHEN_CURIE, SNCA_CURIE]
    names = [PARKINSONS_NAME, WARFARIN_NAME]
    results = synonymizer.get_canonical_curies(curies=curies, names=names)
    print(results)
    all_input_entities = set(curies + names)
    assert all_input_entities == set(results)
    for input_entity in all_input_entities:
        assert results[input_entity]


def test_get_canonical_curies_return_all_categories():
    curies = [ATRIAL_FIBRILLATION_CURIE, IBUPROFEN_CURIE, SNCA_CURIE]
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(curies=curies, names=WARFARIN_NAME, return_all_categories=True)
    print(results)
    assert(len(results) == 4)
    input_entities = curies + [WARFARIN_NAME]
    for input_entity in input_entities:
        assert results.get(input_entity)
        assert {"preferred_name", "preferred_category", "preferred_curie", "all_categories"} == set(results[input_entity])
        assert results[input_entity]["preferred_curie"]
        assert results[input_entity]["preferred_category"]
        assert results[input_entity]["preferred_category"].startswith("biolink:")
        assert results[input_entity]["all_categories"]
        for category, count in results[input_entity]["all_categories"].items():
            assert count > 0
            assert category.startswith("biolink:")


def test_get_equivalent_nodes():
    synonymizer = NodeSynonymizer()
    curies = [ACETAMINOPHEN_CURIE, PARKINSONS_CURIE]
    results = synonymizer.get_equivalent_nodes(curies)
    print(results)
    assert set(curies) == set(results)
    for curie in curies:
        assert results[curie]
        assert len(results[curie]) > 1
    assert ACETAMINOPHEN_CURIE_2 in results[ACETAMINOPHEN_CURIE]
    assert ACETAMINOPHEN_CURIE in results[ACETAMINOPHEN_CURIE]
    assert PARKINSONS_CURIE_2 in results[PARKINSONS_CURIE]
    assert PARKINSONS_CURIE in results[PARKINSONS_CURIE]


def test_get_equivalent_nodes_by_name():
    synonymizer = NodeSynonymizer()
    names = [PARKINSONS_NAME, WARFARIN_NAME]
    results = synonymizer.get_equivalent_nodes(names=names)
    print(results)
    assert set(names) == set(results)
    for name in names:
        assert results[name]
        assert len(results[name]) > 1
    assert PARKINSONS_CURIE in results[PARKINSONS_NAME]
    assert PARKINSONS_CURIE_2 in results[PARKINSONS_NAME]


def test_get_equivalent_nodes_by_curies_and_names():
    synonymizer = NodeSynonymizer()
    curies = [ACETAMINOPHEN_CURIE, FAKE_CURIE]
    names = [PARKINSONS_NAME, WARFARIN_NAME]
    results = synonymizer.get_equivalent_nodes(curies=curies, names=names)
    print(results)
    input_entities = curies + names
    assert set(input_entities) == set(results)
    assert results[FAKE_CURIE] is None
    for input_entity in input_entities:
        if input_entity != FAKE_CURIE:
            assert results[input_entity]
            assert len(results[input_entity]) > 1
    assert PARKINSONS_CURIE in results[PARKINSONS_NAME]
    assert PARKINSONS_CURIE_2 in results[PARKINSONS_NAME]
    assert ACETAMINOPHEN_CURIE in results[ACETAMINOPHEN_CURIE]
    assert ACETAMINOPHEN_CURIE_2 in results[ACETAMINOPHEN_CURIE]


def test_get_normalizer_results():
    synonymizer = NodeSynonymizer()
    input_entities = [PARKINSONS_CURIE, CERVICAL_RIB_NAME, IBUPROFEN_CURIE, FAKE_NAME]
    results = synonymizer.get_normalizer_results(input_entities)
    print(json.dumps(results, indent=2))
    assert len(results) == len(input_entities)
    assert results[FAKE_NAME] is None
    for input_entity in input_entities:
        if input_entity != FAKE_NAME:
            assert results[input_entity]["id"]
            assert {"identifier", "name", "category", "SRI_normalizer_name",
                    "SRI_normalizer_category", "SRI_normalizer_curie"} == set(results[input_entity]["id"])
            assert results[input_entity]["id"]["identifier"]
            assert results[input_entity]["id"]["category"]
            assert results[input_entity]["id"]["category"].startswith("biolink:")
            if results[input_entity]["id"]["SRI_normalizer_category"]:
                assert results[input_entity]["id"]["SRI_normalizer_category"].startswith("biolink:")

            assert results[input_entity]["categories"]
            for category, count in results[input_entity]["categories"].items():
                assert count > 0
                assert category.startswith("biolink:")

            assert results[input_entity]["nodes"]
            assert len(results[input_entity]["nodes"]) > 1
            for equivalent_node in results[input_entity]["nodes"]:
                assert {"identifier", "category", "label", "major_branch", "in_sri", "name_sri", "category_sri",
                        "in_kg2pre", "name_kg2pre", "category_kg2pre"} == set(equivalent_node)
                assert equivalent_node["identifier"]
                assert equivalent_node["category"]
                assert equivalent_node["category"].startswith("biolink:")
                if equivalent_node["category_sri"]:
                    assert equivalent_node["category_sri"].startswith("biolink:")
                if equivalent_node["category_kg2pre"]:
                    assert equivalent_node["category_kg2pre"].startswith("biolink:")


def test_improper_curie_prefix_capitalization():
    synonymizer = NodeSynonymizer()

    improper_curie = "NCBIGENE:1017"
    results = synonymizer.get_canonical_curies(improper_curie)
    assert results[improper_curie]
    assert len(results) == 1

    improper_curie = "NCBIGENE:1017"
    results = synonymizer.get_canonical_curies(improper_curie, return_all_categories=True)
    assert results[improper_curie]
    assert len(results) == 1

    improper_curie = "NCBIGENE:1017"
    results = synonymizer.get_equivalent_nodes(improper_curie)
    assert results[improper_curie]
    assert len(results) == 1

    improper_curie = "NCBIGENE:1017"
    results = synonymizer.get_normalizer_results(improper_curie)
    assert results[improper_curie]
    assert len(results) == 1


def test_approximate_name_based_matching():
    synonymizer = NodeSynonymizer()

    name_not_exactly_in_synonymizer = "Parkinsons disease"
    results = synonymizer.get_equivalent_nodes(names=name_not_exactly_in_synonymizer)
    assert results[name_not_exactly_in_synonymizer]
    assert len(results) == 1

    name_not_exactly_in_synonymizer_2 = "ATRIAL FIBRILLATION"
    results = synonymizer.get_canonical_curies(names=name_not_exactly_in_synonymizer_2)
    assert results[name_not_exactly_in_synonymizer_2]
    assert len(results) == 1

    name_not_exactly_in_synonymizer_2 = "ATRIAL FIBRILLATION"
    results = synonymizer.get_canonical_curies(names=name_not_exactly_in_synonymizer_2, return_all_categories=True)
    assert results[name_not_exactly_in_synonymizer_2]
    assert len(results) == 1

    name_not_exactly_in_synonymizer_2 = "ATRIAL FIBRILLATION"
    results = synonymizer.get_equivalent_nodes(names=name_not_exactly_in_synonymizer_2)
    assert results[name_not_exactly_in_synonymizer_2]
    assert len(results) == 1

    name_not_exactly_in_synonymizer_2 = "ATRIAL FIBRILLATION"
    results = synonymizer.get_normalizer_results(name_not_exactly_in_synonymizer_2)
    assert results[name_not_exactly_in_synonymizer_2]
    assert len(results) == 1


if __name__ == "__main__":
    pytest.main(['-v', 'test_ARAX_synonymizer.py'])
