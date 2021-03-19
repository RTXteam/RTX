#!/bin/env python3
""" Estimates different NGD methods' (local 'fast' or backup eUtils methods) coverage of KG1/KG2 nodes
Usage: python estimate_coverage.py [--local] [--backup] [--all]
Note: The database "curie_to_pmids.sqlite" must exist in the directory this script is run from.
"""
import argparse
import collections
import json
import os
import sys
import traceback

from typing import Set, List, Dict

from neo4j import GraphDatabase
from sqlitedict import SqliteDict

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")


def _run_cypher_query(cypher_query: str, kg='KG2') -> List[Dict[str, any]]:
    rtxc = RTXConfiguration()
    if kg == 'KG2':
        rtxc.live = "KG2"
    try:
        driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
        with driver.session() as session:
            query_results = session.run(cypher_query).data()
        driver.close()
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        print(f"Encountered an error interacting with {kg} neo4j. {tb}")
        return []
    else:
        return query_results


def _get_random_node_ids(batch_size: int, kg='KG2') -> Set[str]:
    cypher_query = f"match (a) return a.id, rand() as r order by r limit {batch_size}"
    results = _run_cypher_query(cypher_query, kg)
    return {result['a.id'] for result in results} if results else set()


def estimate_percent_nodes_with_mesh_mapping_via_synonymizer(kg: str):
    print(f"Estimating the percent of {kg} nodes mappable to a MESH curie via NodeSynonymizer")
    percentages_with_mesh = []
    num_batches = 20
    batch_size = 4000
    for number in range(num_batches):
        print(f"  Batch {number + 1}")
        # Get random selection of node IDs from the KG
        random_node_ids = _get_random_node_ids(batch_size, kg)

        # Use synonymizer to get their equivalent curies and check for a MESH term
        print(f"    Getting equivalent curies for those random node IDs..")
        synonymizer = NodeSynonymizer()
        curie_synonym_info = synonymizer.get_equivalent_curies(list(random_node_ids))
        num_curies_with_mesh_term = 0
        for input_curie, synonym_curies in curie_synonym_info.items():
            if synonym_curies:
                if any(curie for curie in synonym_curies if curie.startswith('MESH')):
                    num_curies_with_mesh_term += 1
        percentage_with_mesh = (num_curies_with_mesh_term / len(random_node_ids)) * 100
        print(f"    {percentage_with_mesh}% of nodes had a synonym MESH term in this batch.")
        percentages_with_mesh.append(percentage_with_mesh)

    print(f"  Percentages for all batches: {percentages_with_mesh}.")
    average = sum(percentages_with_mesh) / len(percentages_with_mesh)
    print(f"Final estimate of {kg} nodes mappable to a MESH term via NodeSynonymizer: {round(average)}%")


def estimate_percent_nodes_covered_by_backup_method(kg: str):
    print(f"Estimating the percent of {kg} nodes mappable by the 'backup' NGD method (uses eUtils)")
    backup_ngd = NormGoogleDistance()
    synonymizer = NodeSynonymizer()
    percentages_mapped = []
    num_batches = 10
    batch_size = 10
    for number in range(num_batches):
        print(f"  Batch {number + 1}")
        # Get random selection of nodes from the KG
        query = f"match (a) return a.id, a.name, rand() as r order by r limit {batch_size}"
        results = _run_cypher_query(query, kg)
        canonical_curie_info = synonymizer.get_canonical_curies([result['a.id'] for result in results])
        recognized_curies = {input_curie for input_curie in canonical_curie_info if canonical_curie_info.get(input_curie)}

        # Use the back-up NGD method to try to grab PMIDs for each
        num_with_pmids = 0
        for curie in recognized_curies:
            # Try to map this to a MESH term using the backup method (the chokepoint)
            node_id = canonical_curie_info[curie].get('preferred_curie')
            node_name = canonical_curie_info[curie].get('preferred_name')
            node_type = canonical_curie_info[curie].get('preferred_type')
            try:
                pmids = backup_ngd.get_pmids_for_all([node_id], [node_name])
            except Exception:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                print(f"ERROR using back-up method: {tb}")
            else:
                if len(pmids) and ([pmid_list for pmid_list in pmids if pmid_list]):
                    num_with_pmids += 1
                    print(f"    Found {len(pmids[0])} PMIDs for {node_id}, {node_name}.")
                else:
                    print(f"    Not found. ({node_id}, {node_name})")
        percentage_with_pmids = (num_with_pmids / len(recognized_curies)) * 100
        print(f"    {percentage_with_pmids}% of nodes were mapped to PMIDs using backup method.")
        percentages_mapped.append(percentage_with_pmids)

    print(f"  Percentages for all batches: {percentages_mapped}.")
    average = sum(percentages_mapped) / len(percentages_mapped)
    print(f"Final estimate of backup method's coverage of {kg} nodes: {round(average)}%")


def estimate_percent_nodes_covered_by_ultrafast_ngd(kg: str):
    print(f"Estimating the percent of {kg} nodes covered by the local NGD system..")
    rtxc = RTXConfiguration()
    if kg == 'KG2':
        rtxc.live = "KG2"
    #curie_to_pmid_db = SqliteDict(f"./curie_to_pmids.sqlite")
    curie_to_pmids_path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    curie_to_pmid_db = SqliteDict(f"{curie_to_pmids_path}{os.path.sep}{rtxc.curie_to_pmids_path.sep('/')[-1]}")
    percentages_mapped = []
    num_batches = 20
    batch_size = 4000
    all_nodes_mapped_by_type = dict()
    for number in range(num_batches):
        # Get random selection of node IDs from the KG
        random_node_ids = _get_random_node_ids(batch_size, kg)

        # Use synonymizer to get their canonicalized info
        synonymizer = NodeSynonymizer()
        canonical_curie_info = synonymizer.get_canonical_curies(list(random_node_ids))
        recognized_curies = {input_curie for input_curie in canonical_curie_info if canonical_curie_info.get(input_curie)}

        # See if those canonical curies are in our local database
        num_mapped_to_pmids = 0
        for input_curie in recognized_curies:
            canonical_curie = canonical_curie_info[input_curie].get('preferred_curie')
            preferred_type = canonical_curie_info[input_curie].get('preferred_type')
            if preferred_type not in all_nodes_mapped_by_type:
                all_nodes_mapped_by_type[preferred_type] = {'covered': 0, 'not_covered': 0}
            if canonical_curie and canonical_curie in curie_to_pmid_db:
                num_mapped_to_pmids += 1
                all_nodes_mapped_by_type[preferred_type]['covered'] += 1
            else:
                all_nodes_mapped_by_type[preferred_type]['not_covered'] += 1
        percentage_mapped = (num_mapped_to_pmids / len(random_node_ids)) * 100
        percentages_mapped.append(percentage_mapped)

    average = sum(percentages_mapped) / len(percentages_mapped)
    print(f"Estimated coverage of {kg} nodes: {round(average)}%.")
    node_type_percentages_dict = dict()
    for node_type, coverage_info in all_nodes_mapped_by_type.items():
        num_covered = coverage_info['covered']
        num_total = coverage_info['covered'] + coverage_info['not_covered']
        percentage = round((num_covered / num_total) * 100)
        node_type_percentages_dict[node_type] = percentage
    for node_type, percentage in sorted(node_type_percentages_dict.items(), key=lambda item: item[1], reverse=True):
        print(f"  {node_type}: {percentage}%")


def report_on_curies_missed_by_local_ngd(kg: str):
    backup_ngd = NormGoogleDistance()
    synonymizer = NodeSynonymizer()
    #curie_to_pmid_db = SqliteDict(f"./curie_to_pmids.sqlite")
    rtxc = RTXConfiguration()
    if kg == 'KG2':
        rtxc.live = "KG2"
    curie_to_pmids_path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    curie_to_pmid_db = SqliteDict(f"{curie_to_pmids_path}{os.path.sep}{rtxc.curie_to_pmids_path.sep('/')[-1]}")
    batch_size = 50

    # Get random selection of nodes from the KG
    query = f"match (a) return a.id, a.name, rand() as r order by r limit {batch_size}"
    results = _run_cypher_query(query, kg)
    canonical_curie_info = synonymizer.get_canonical_curies([result['a.id'] for result in results])
    recognized_curies = {input_curie for input_curie in canonical_curie_info if canonical_curie_info.get(input_curie)}

    # Figure out which of these local ngd misses
    misses = set()
    for curie in recognized_curies:
        canonical_curie = canonical_curie_info[curie].get('preferred_curie')
        if canonical_curie not in curie_to_pmid_db:
            misses.add(curie)
    percent_missed = round((len(misses) / len(recognized_curies)) * 100)
    print(f"Local ngd missed {len(misses)} of {len(recognized_curies)} curies ({percent_missed}%)")

    # Try eUtils for each of the curies local ngd missed
    num_eutils_found = 0
    try:
        with open('misses_found_by_eutils.json', 'r') as file_to_add_to:
            found_dict = json.load(file_to_add_to)
    except Exception:
        found_dict = dict()
    for missed_curie in misses:
        # Try eUtils for this node
        node_id = canonical_curie_info[missed_curie].get('preferred_curie')
        node_name = canonical_curie_info[missed_curie].get('preferred_name')
        node_type = canonical_curie_info[missed_curie].get('preferred_type')
        try:
            pmids = backup_ngd.get_pmids_for_all([node_id], [node_name])
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            print(f"ERROR using back-up method: {tb}")
        else:
            if len(pmids) and ([pmid_list for pmid_list in pmids if pmid_list]):
                num_eutils_found += 1
                print(f"    Found {len(pmids[0])} PMIDs for {node_id}, {node_name}.")
                found_dict[node_id] = {'name': node_name, 'type': node_type}
            else:
                print(f"    Not found. ({node_id}, {node_name})")

    # Report some findings
    percent_found_by_eutils = round((num_eutils_found / len(misses)) * 100)
    print(f"Eutils found {num_eutils_found} out of {len(misses)} curies that local ngd missed ({percent_found_by_eutils}%)")
    found_types = [node_info['type'] for node_id, node_info in found_dict.items()]
    counter = collections.Counter(found_types)
    print(counter)

    # Save the data to a JSON file for access later
    with open('misses_found_by_eutils.json', 'w+') as output_file:
        json.dump(found_dict, output_file)


if __name__ == "__main__":
    # Load command-line arguments
    arg_parser = argparse.ArgumentParser(description="Estimate coverage of various NGD methods")
    arg_parser.add_argument("--backup", dest="backup", action="store_true", default=False)
    arg_parser.add_argument("--misses", dest="misses", action="store_true", default=False)
    args = arg_parser.parse_args()

    if args.backup:
        estimate_percent_nodes_covered_by_backup_method('KG2')
    elif args.misses:
        report_on_curies_missed_by_local_ngd('KG2')
    else:
        estimate_percent_nodes_covered_by_ultrafast_ngd('KG1')
        estimate_percent_nodes_covered_by_ultrafast_ngd('KG2')
