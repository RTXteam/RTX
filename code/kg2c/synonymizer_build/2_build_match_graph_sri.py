import argparse
import itertools
import json
import logging
import os
import pathlib
import subprocess
import sys
from typing import Set, Dict, List

import json_lines
import numpy as np
import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/BiolinkHelper/")
from biolink_helper import BiolinkHelper

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
SRI_NN_URL = "https://nodenormalization-sri.renci.org/get_normalized_nodes"
# Note: The above is the SRI NN development (non-ITRB) server, which seems to be faster for us


def strip_biolink_prefix(item: str) -> str:
    return item.replace("biolink:", "")


def get_kg2pre_node_ids():
    logging.info(f"Grabbing KG2pre node IDs from KG2pre match graph..")
    kg2pre_nodes_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/1_match_nodes_kg2pre.tsv")
    kg2pre_node_ids = kg2pre_nodes_df.id.values
    return set(kg2pre_node_ids)


def get_sri_edge_id(subject_id: str, object_id: str) -> str:
    return f"SRI:{subject_id}--{object_id}"


def determine_cluster_category(sri_types: List[str], category_map: Dict[str, str], bh: BiolinkHelper) -> str:
    # Temporary patch to pick best single category for cluster until this info is added to API response
    sri_types_hash = "-".join(sorted(sri_types))
    if sri_types_hash not in category_map:  # Only need to process this set if we haven't seen it before
        sri_types_set = set(bh.filter_out_mixins(sri_types))  # We want to assign a true category, not mixin
        leaves = set()
        for biolink_category in sri_types_set:
            descendants = set(bh.get_descendants(biolink_category,
                                                 include_mixins=False,
                                                 include_conflations=False)).difference({biolink_category})
            if not descendants.intersection(sri_types_set):
                # We've found a (in this context) 'leaf' category!
                leaves.add(biolink_category)
        if leaves:
            # Store this mapping for fast lookup later
            if len(leaves) == 1:
                chosen_category = list(leaves)[0]
            else:
                if "biolink:Gene" in leaves:
                    chosen_category = "biolink:Gene"
                elif "biolink:SmallMolecule" in leaves:
                    chosen_category = "biolink:SmallMolecule"
                elif "biolink:Protein" in leaves:
                    chosen_category = "biolink:Protein"
                elif "biolink:Drug" in leaves:
                    chosen_category = "biolink:Drug"
                else:
                    chosen_category = sorted(list(leaves))[0]
                logging.info(f"SRI clique has more than one leaf category. Original category list from SRI was: "
                             f"{sri_types}. Identified 'leaves' within that category subtree are: {leaves}."
                             f" Category chosen to represent all nodes in clique was: {chosen_category}.")
            category_map[sri_types_hash] = chosen_category
        else:
            raise ValueError(f"Failed to find the most specific category for a node from SRI! Must be a bug.")

    return category_map[sri_types_hash]


def create_sri_match_graph(kg2pre_node_ids_set: Set[str]):
    logging.info(f"Starting to build SRI match graph based on {len(kg2pre_node_ids_set):,} KG2pre node IDs..")

    # Save the previous version of SRI match graph, if it exists (as backup, in case the SRI NN API is down)
    logging.info(f"Saving backup copies of already existing SRI match graph TSV files..")
    sri_match_nodes_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv"
    sri_match_edges_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv"
    if pathlib.Path(sri_match_nodes_file_path).exists():
        os.system(f"mv {sri_match_nodes_file_path} {sri_match_nodes_file_path}_PREVIOUS")
    if pathlib.Path(sri_match_edges_file_path).exists():
        os.system(f"mv {sri_match_edges_file_path} {sri_match_edges_file_path}_PREVIOUS")

    # Divide KG2pre node IDs into batches
    kg2pre_node_ids = list(kg2pre_node_ids_set)
    batch_size = 1000  # This is the suggested max batch size from Chris Bizon (in Translator slack..)
    logging.info(f"Dividing KG2pre node IDs into batches of {batch_size}")
    kg2pre_node_id_batches = [kg2pre_node_ids[batch_start:batch_start + batch_size]
                              for batch_start in range(0, len(kg2pre_node_ids), batch_size)]

    # Ask the SRI NodeNormalizer for normalized info for each batch of KG2pre IDs
    logging.info(f"Beginning to send {len(kg2pre_node_id_batches)} batches of node IDs to SRI NN..")
    batch_num = 0
    num_unrecognized_nodes = 0
    sri_nodes_dict = dict()
    sri_edges_dict = dict()
    category_map = dict()
    bh = BiolinkHelper()
    for node_id_batch in kg2pre_node_id_batches:
        # Send the batch to the SRI NN RestAPI
        query_body = {"curies": node_id_batch,
                      "conflate": True,
                      "drug_chemical_conflate": True}
        response = requests.post(SRI_NN_URL, json=query_body)

        # Add nodes and edges to our SRI match graph based on the returned info
        if response.status_code == 200:
            for kg2pre_node_id, normalized_info in response.json().items():
                if normalized_info:  # This means the SRI NN recognized the KG2pre node ID we asked for
                    cluster_id = normalized_info["id"]["identifier"]
                    if cluster_id not in sri_nodes_dict:  # Process this cluster if we haven't seen it before
                        # Create nodes for all members of this cluster
                        cluster_nodes_dict = dict()
                        # TODO: Update once Gaurav adds per-identifier type info to the API https://github.com/TranslatorSRI/NodeNormalization/issues/281
                        cluster_category = determine_cluster_category(normalized_info["type"], category_map, bh)
                        for equivalent_node in normalized_info["equivalent_identifiers"]:
                            node_id = equivalent_node["identifier"]
                            node = (node_id, equivalent_node.get("label"), cluster_category, cluster_id)
                            cluster_nodes_dict[node_id] = node
                        sri_nodes_dict.update(cluster_nodes_dict)

                        # Create within-cluster edges (form a complete graph for the clique)
                        cluster_node_ids = list(cluster_nodes_dict.keys())
                        for node_pair in list(itertools.combinations(cluster_node_ids, 2)):
                            subject_id, object_id = node_pair
                            edge_id = get_sri_edge_id(subject_id, object_id)
                            edge = (edge_id, subject_id, "biolink:same_as", object_id)
                            sri_edges_dict[edge_id] = edge
                else:  # The SRI NN did not recognize the KG2pre node ID we asked for
                    num_unrecognized_nodes += 1
        else:
            raise ValueError(f"Batch #{batch_num} request to SRI failed; returned status code "
                             f"{response.status_code}: {response.text}")

        # Log our progress
        batch_num += 1
        if batch_num % 100 == 0:
            logging.info(f"Have processed {batch_num} of {len(kg2pre_node_id_batches)} batches..")

    # Report some final stats
    logging.info(f"SRI match graph contains {len(sri_nodes_dict)} nodes and {len(sri_edges_dict)} edges")
    logging.info(f"SRI NN API did not recognize {num_unrecognized_nodes:,} of {len(kg2pre_node_ids):,} "
                 f"KG2pre nodes ({round(num_unrecognized_nodes / len(kg2pre_node_ids), 2) * 100}%)")

    # Save the match graph to disk
    save_sri_nodes(sri_nodes_dict)
    save_sri_edges(sri_edges_dict)


def save_sri_nodes(nodes_dict: dict):
    logging.info(f"Loading select SRI nodes into DataFrame..")
    nodes_df = pd.DataFrame(nodes_dict.values(), columns=["id", "name", "category", "cluster_id"])
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    nodes_df.category = strip_biolink_prefix_vectorized(nodes_df.category)
    logging.info(f"Saving SRI nodes to TSV..")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv", sep="\t", index=False)


def save_sri_edges(edges_dict: dict):
    logging.info(f"Loading select SRI edges into DataFrame..")
    edges_df = pd.DataFrame(edges_dict.values(), columns=["id", "subject", "predicate", "object"])
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    edges_df.predicate = strip_biolink_prefix_vectorized(edges_df.predicate)
    logging.info(f"Saving SRI edges to TSV..")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv", sep="\t", index=False)


def run():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    kg2pre_node_ids = get_kg2pre_node_ids()
    create_sri_match_graph(kg2pre_node_ids)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    run()


if __name__ == "__main__":
    main()
