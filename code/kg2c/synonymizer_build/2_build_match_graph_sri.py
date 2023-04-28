import itertools
import logging
import os
import pathlib
import subprocess
import sys
from typing import Set, List

import numpy as np
import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/BiolinkHelper/")
from biolink_helper import BiolinkHelper

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])

BH = BiolinkHelper()  # TODO: Eventually specify biolink version that this particular KG2 version uses.. or SRI ?
CATEGORY_LEAF_MAP = dict()


def strip_biolink_prefix(item: str) -> str:
    return item.replace("biolink:", "")


def get_kg2pre_node_ids():
    logging.info(f"Grabbing KG2pre node IDs from KG2pre match graph..")
    kg2pre_nodes_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/1_match_nodes_kg2pre.tsv")
    kg2pre_node_ids = kg2pre_nodes_df.id.values
    return set(kg2pre_node_ids)


def get_most_specific_category(categories: List[str]) -> str:
    # The SRI includes all ancestors of the category in the cluster's categories list; we want to remove those
    true_categories = BH.filter_out_mixins(categories)
    simplified_categories_set = set(true_categories).difference({"biolink:Entity"})
    categories_group_key = "--".join(sorted(list(simplified_categories_set)))

    # Figure out the leaf category for this group of categories if we haven't seen it before
    if categories_group_key not in CATEGORY_LEAF_MAP:
        relative_leaf_categories = set()
        for category in simplified_categories_set:
            descendants = BH.get_descendants(category, include_mixins=False, include_conflations=False)
            descendants_in_set = (set(descendants).intersection(simplified_categories_set)).difference({category})
            if not descendants_in_set:
                relative_leaf_categories.add(category)

        # Choose one category to assign to the cluster
        if len(relative_leaf_categories) == 1:
            most_specific_category = list(relative_leaf_categories)[0]
        elif len(relative_leaf_categories) > 1:
            chosen_category = sorted(list(relative_leaf_categories))[0]
            logging.warning(f"More than one category in an SRI cluster's category list are (relative) leaves: "
                            f"{relative_leaf_categories}. Will use {chosen_category}. Full categories list for the "
                            f"cluster was: {categories}")
            most_specific_category = chosen_category
        else:
            logging.warning(f"Could not determine most specific category for SRI cluster with categories: "
                            f"{categories}. Will consider this category group to be NamedThing.")
            most_specific_category = "biolink:NamedThing"
        CATEGORY_LEAF_MAP[categories_group_key] = most_specific_category

    # TODO: Add one-off for ['biolink:GenomicEntity']? (which is a mixin, I think..)

    return CATEGORY_LEAF_MAP[categories_group_key]


def create_sri_match_graph(kg2pre_node_ids_set: Set[str]):
    total_num_kg2pre_node_ids = len(kg2pre_node_ids_set)
    logging.info(f"Starting to build SRI match graph based on {total_num_kg2pre_node_ids:,} KG2pre node IDs..")

    # Save the current version of SRI match graph, if it exists (as backup, in case the SRI NN API is down)
    sri_match_nodes_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv"
    sri_match_edges_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv"
    if pathlib.Path(sri_match_nodes_file_path).exists():
        subprocess.check_call(["mv", sri_match_nodes_file_path, f"{sri_match_nodes_file_path}_PREVIOUS"])
    if pathlib.Path(sri_match_edges_file_path).exists():
        subprocess.check_call(["mv", sri_match_edges_file_path, f"{sri_match_edges_file_path}_PREVIOUS"])

    # Ask the SRI NodeNormalizer for normalized info for all KG2pre IDs, divided into batches
    sri_nodes = dict()
    sri_edges = set()
    kg2pre_node_ids_remaining = kg2pre_node_ids_set
    batch_size = 1000  # This is the preferred max batch size, according to Chris Bizon in Translator slack
    batch_num = 0
    num_failed_batches = 0
    num_unrecognized_nodes = 0
    while kg2pre_node_ids_remaining:
        # Grab the next batch of node IDs
        batch_node_ids = set(itertools.islice(kg2pre_node_ids_remaining, batch_size))
        kg2pre_node_ids_remaining -= batch_node_ids

        # Send the batch to the SRI NN RestAPI
        # Note: This is their development (non-ITRB) server, which seems to be faster for us..
        sri_nn_url = "https://nodenormalization-sri.renci.org/1.3/get_normalized_nodes"
        query_body = {"curies": list(batch_node_ids),
                      "conflate": True}
        response = requests.post(sri_nn_url, json=query_body)

        # Extract the canonical identifiers and any other equivalent IDs from the response for this batch
        if response.status_code == 200:
            for kg2pre_node_id, normalized_info in response.json().items():
                # This means the SRI NN recognized the KG2pre node ID we asked for
                if normalized_info:
                    cluster_id = normalized_info["id"]["identifier"]

                    # Process this cluster if we haven't seen it before
                    if cluster_id not in sri_nodes:
                        cluster_category = get_most_specific_category(normalized_info["type"])

                        # Add each cluster member to our overall nodes dict
                        member_ids = []
                        for equivalent_node in normalized_info["equivalent_identifiers"]:
                            node_id = equivalent_node["identifier"]
                            node_name = equivalent_node.get("label")
                            sri_nodes[node_id] = (node_id, node_name, cluster_category, cluster_id)
                            member_ids.append(node_id)
                        # Mark any of the non-preferred, equivalent nodes as processed, so we don't do repeat queries
                        kg2pre_node_ids_remaining = kg2pre_node_ids_remaining.difference(member_ids)

                        # Then create intra-cluster edges
                        if len(member_ids) > 1:
                            possible_node_id_combos = itertools.combinations(member_ids, 2)
                            for subject_node_id, object_node_id in possible_node_id_combos:
                                # Note: Order of subject/object shouldn't matter here, since this should be the only
                                # cluster with an edge between these two nodes
                                edge_id = f"SRINN:{subject_node_id}--{object_node_id}"
                                sri_edges.add((edge_id, subject_node_id, "same_as", object_node_id))
                else:
                    # The SRI NN did not recognize the KG2pre node ID we asked for
                    num_unrecognized_nodes += 1
        else:
            logging.warning(f"Batch {batch_num} returned non-200 status ({response.status_code}): {response.text}")
            num_failed_batches += 1

        # Log our progress
        batch_num += 1
        if batch_num % 100 == 0:
            logging.info(f"Have processed {batch_num} batches.. {len(kg2pre_node_ids_remaining):,} "
                         f"KG2pre node IDs remaining")

    # Load our nodes and edges dicts into DataFrames
    nodes_df = pd.DataFrame(sri_nodes.values(), columns=["id", "name", "category", "cluster_id"])
    edges_df = pd.DataFrame(sri_edges, columns=["id", "subject", "predicate", "object"])

    # Get rid of biolink prefixes (saves space, makes for easier processing)
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    nodes_df.category = strip_biolink_prefix_vectorized(nodes_df.category)

    logging.info(f"Final SRI NN match nodes df is: \n{nodes_df}")
    logging.info(f"Final SRI NN match edges df is: \n{edges_df}")
    logging.info(f"Saving SRI match graph to TSVs..")
    nodes_df.to_csv(sri_match_nodes_file_path, sep="\t", index=False)
    edges_df.to_csv(sri_match_edges_file_path, sep="\t", index=False)

    # Report some final stats
    logging.info(f"SRI NN API did not recognize {num_unrecognized_nodes:,} of {total_num_kg2pre_node_ids:,} "
                 f"KG2pre nodes ({round(num_unrecognized_nodes / total_num_kg2pre_node_ids, 2) * 100}%)")
    logging.info(f"Our SRI match graph includes {len(nodes_df):,} SRI clusters")
    if num_failed_batches:
        logging.warning(f"{num_failed_batches} requests to SRI NN API failed. Each failed request included "
                        f"{batch_size} KG2pre node IDs.")


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Transform SRI NN data into 'match graph' format, only including KG2-related nodes
    kg2pre_node_ids = get_kg2pre_node_ids()
    create_sri_match_graph(kg2pre_node_ids)


if __name__ == "__main__":
    main()
