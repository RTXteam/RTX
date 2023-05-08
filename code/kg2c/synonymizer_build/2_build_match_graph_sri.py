import argparse
import json
import logging
import os
import pathlib
import subprocess
from typing import Set, Dict

import json_lines
import numpy as np
import pandas as pd
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
SRI_NN_DIR = f"{SYNONYMIZER_BUILD_DIR}/SRI_NN"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])
# NOTE: These below three variables need to be updated for new SRI NN builds..
SRI_NN_NODES_FILE_NAME = "KGX_NN_data-2023apr7_nodes.jsonl"
SRI_NN_EDGES_FILE_NAME = "KGX_NN_data-2023apr7_edges.jsonl"
SRI_NN_REMOTE_ROOT_PATH = "https://stars.renci.org/var/babel_outputs/2022dec2-2/kgx/"


def strip_biolink_prefix(item: str) -> str:
    return item.replace("biolink:", "")


def get_kg2pre_node_ids():
    logging.info(f"Grabbing KG2pre node IDs from KG2pre match graph..")
    kg2pre_nodes_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/1_match_nodes_kg2pre.tsv")
    kg2pre_node_ids = kg2pre_nodes_df.id.values
    return set(kg2pre_node_ids)


def get_sri_cluster_id_mappings(kg2pre_node_ids_set: Set[str]):
    kg2pre_node_ids = list(kg2pre_node_ids_set)
    logging.info(f"Starting to build SRI match graph based on {len(kg2pre_node_ids):,} KG2pre node IDs..")

    # Save the current version of SRI match graph, if it exists (as backup, in case the SRI NN API is down)
    logging.info(f"Saving backup copies of already existing SRI match graph TSV files..")
    sri_match_nodes_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv"
    sri_match_edges_file_path = f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv"
    if pathlib.Path(sri_match_nodes_file_path).exists():
        subprocess.check_call(["mv", sri_match_nodes_file_path, f"{sri_match_nodes_file_path}_PREVIOUS"])
    if pathlib.Path(sri_match_edges_file_path).exists():
        subprocess.check_call(["mv", sri_match_edges_file_path, f"{sri_match_edges_file_path}_PREVIOUS"])

    # Divide KG2pre node IDs into batches
    batch_size = 1000  # This is the suggested max batch size from Chris Bizon (in Translator slack..)
    logging.info(f"Dividing KG2pre node IDs into batches of {batch_size}")
    kg2pre_node_id_batches = [kg2pre_node_ids[batch_start:batch_start + batch_size]
                              for batch_start in range(0, len(kg2pre_node_ids), batch_size)]

    # Ask the SRI NodeNormalizer for normalized info for each batch of KG2pre IDs
    logging.info(f"Beginning to send {len(kg2pre_node_id_batches)} batches to SRI NN..")
    sri_node_id_to_cluster_id_map = dict()
    batch_size = 1000  # This is the preferred max batch size, according to Chris Bizon in Translator slack
    batch_num = 0
    num_failed_batches = 0
    num_unrecognized_nodes = 0
    for node_id_batch in kg2pre_node_id_batches:
        # Send the batch to the SRI NN RestAPI
        # Note: This is their development (non-ITRB) server, which seems to be faster for us..
        sri_nn_url = "https://nodenormalization-sri.renci.org/1.3/get_normalized_nodes"
        query_body = {"curies": node_id_batch,
                      "conflate": True}
        response = requests.post(sri_nn_url, json=query_body)

        # Extract the canonical identifiers and any other equivalent IDs from the response for this batch
        if response.status_code == 200:
            for kg2pre_node_id, normalized_info in response.json().items():
                # This means the SRI NN recognized the KG2pre node ID we asked for
                if normalized_info:
                    # Process this cluster if we haven't seen it before
                    cluster_id = normalized_info["id"]["identifier"]
                    if cluster_id not in sri_node_id_to_cluster_id_map:
                        for equivalent_node in normalized_info["equivalent_identifiers"]:
                            node_id = equivalent_node["identifier"]
                            sri_node_id_to_cluster_id_map[node_id] = cluster_id
                else:
                    # The SRI NN did not recognize the KG2pre node ID we asked for
                    num_unrecognized_nodes += 1
        else:
            logging.warning(f"Batch {batch_num} returned non-200 status ({response.status_code}): {response.text}")
            num_failed_batches += 1

        # Log our progress
        batch_num += 1
        if batch_num % 100 == 0:
            logging.info(f"Have processed {batch_num} of {len(kg2pre_node_id_batches)} batches..")

    # Save map of cluster IDs
    logging.info(f"Done getting SRI cluster ID mappings. Saving cluster ID map to JSON file..")
    with open(f"{SYNONYMIZER_BUILD_DIR}/2_sri_node_ids_to_cluster_ids.json", "w+") as cluster_id_file:
        json.dump(sri_node_id_to_cluster_id_map, cluster_id_file, indent=2)

    # Report some final stats
    logging.info(f"SRI NN API did not recognize {num_unrecognized_nodes:,} of {len(kg2pre_node_ids):,} "
                 f"KG2pre nodes ({round(num_unrecognized_nodes / len(kg2pre_node_ids), 2) * 100}%)")
    logging.info(f"Got cluster ID mappings for {len(sri_node_id_to_cluster_id_map):,} SRI nodes")
    if num_failed_batches:
        logging.warning(f"{num_failed_batches} requests to SRI NN API failed. Each failed request included "
                        f"{batch_size} KG2pre node IDs.")

    return sri_node_id_to_cluster_id_map


def create_match_nodes_sri(sri_node_id_to_cluster_id_map: Dict[str, str]) -> Set[str]:
    # Grab the KG2pre-related nodes from the SRI NN json lines file (which is huge - has ~600 million nodes in total)
    logging.info(f"Extracting relevant nodes from bulk SRI NN json lines file..")
    nodes_dict = dict()
    with json_lines.open(f"{SRI_NN_DIR}/{SRI_NN_NODES_FILE_NAME}") as jsonl_file:
        for line_obj in jsonl_file:
            node_id = line_obj["id"]
            if node_id in sri_node_id_to_cluster_id_map:  # Means it's part of a cluster involving KG2pre nodes
                cluster_id = sri_node_id_to_cluster_id_map[node_id]
                node_row = (node_id, line_obj.get("name"), line_obj["category"], cluster_id)
                nodes_dict[node_id] = node_row

    # Save our selected SRI nodes
    logging.info(f"Loading select SRI nodes into DataFrame..")
    nodes_df = pd.DataFrame(nodes_dict.values(), columns=["id", "name", "category", "cluster_id"])
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    nodes_df.category = strip_biolink_prefix_vectorized(nodes_df.category)
    logging.info(f"Saving SRI nodes to TSV..")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv", sep="\t", index=False)

    return set(nodes_dict)


def create_match_edges_sri(sri_node_ids: Set[str]):
    # Grab the KG2pre-related edges from the SRI NN json lines file (which is huge - has ~200 million edges)
    logging.info(f"Extracting relevant edges from bulk SRI NN json lines file..")
    edges_dict = dict()
    with json_lines.open(f"{SRI_NN_DIR}/{SRI_NN_EDGES_FILE_NAME}") as jsonl_file:
        for line_obj in jsonl_file:
            edge_subject = line_obj["subject"]
            edge_object = line_obj["object"]
            if edge_subject in sri_node_ids and edge_object in sri_node_ids:
                edge_id = f"SRI:{edge_subject}--{edge_object}"
                edge_row = (edge_id, edge_subject, line_obj["predicate"], edge_object)
                edges_dict[edge_id] = edge_row

    # Save our selected SRI edges
    logging.info(f"Loading select SRI edges into DataFrame..")
    edges_df = pd.DataFrame(edges_dict.values(), columns=["id", "subject", "predicate", "object"])
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    edges_df.predicate = strip_biolink_prefix_vectorized(edges_df.predicate)
    logging.info(f"Saving SRI edges to TSV..")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv", sep="\t", index=False)


def download_sri_nn_files():
    logging.info(f"Downloading SRI NN source files..")
    if not pathlib.Path(SRI_NN_DIR).exists():
        subprocess.check_call(["mkdir", SRI_NN_DIR])
    logging.info(f"Downloading SRI NN nodes file..")
    subprocess.check_call(["curl", "-L", f"{SRI_NN_REMOTE_ROOT_PATH}/{SRI_NN_NODES_FILE_NAME}.gz", "-o",
                           f"{SRI_NN_DIR}/{SRI_NN_NODES_FILE_NAME}.gz"])
    logging.info(f"Downloading SRI NN edges file..")
    subprocess.check_call(["curl", "-L", f"{SRI_NN_REMOTE_ROOT_PATH}/{SRI_NN_EDGES_FILE_NAME}.gz", "-o",
                           f"{SRI_NN_DIR}/{SRI_NN_EDGES_FILE_NAME}.gz"])
    logging.info(f"Unzipping SRI NN files..")
    subprocess.check_call(["gunzip", f"{SRI_NN_DIR}/{SRI_NN_NODES_FILE_NAME}.gz"])
    subprocess.check_call(["gunzip", f"{SRI_NN_DIR}/{SRI_NN_EDGES_FILE_NAME}.gz"])


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    args = arg_parser.parse_args()

    # Download a fresh copy of the bulk SRI NN data, if requested
    if args.download_fresh:
        download_sri_nn_files()

    # First grab the SRI cluster IDs ('preferred'/canonical curies) for all KG2pre nodes from SRI NN RestAPI
    kg2pre_node_ids = get_kg2pre_node_ids()
    sri_node_id_to_cluster_id_map = get_sri_cluster_id_mappings(kg2pre_node_ids)

    # Then build an SRI 'match graph' using the SRI NN bulk download
    sri_node_ids = create_match_nodes_sri(sri_node_id_to_cluster_id_map)
    create_match_edges_sri(sri_node_ids)


if __name__ == "__main__":
    main()
