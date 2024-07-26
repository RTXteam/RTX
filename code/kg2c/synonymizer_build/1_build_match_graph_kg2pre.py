import argparse
import logging
import os
import pathlib
import subprocess
import sys
from typing import Set

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # KG2c dir
import file_manager

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
KG2PRE_TSVS_DIR = f"{KG2C_DIR}/kg2pre_tsvs"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME = "primary_knowledge_source"


def strip_biolink_prefix(item: str) -> str:
    return item.replace("biolink:", "")


def create_match_nodes_kg2pre(kg2pre_version: str) -> Set[str]:
    logging.info(f"Creating KG2pre nodes table...")

    # Load KG2pre data into nodes table, including only the columns relevant to us
    nodes_tsv_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/nodes.tsv"
    nodes_tsv_header_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/nodes_header.tsv"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id", "name", "category"]
    nodes_df = pd.read_table(nodes_tsv_path,
                             names=node_column_names,
                             usecols=columns_to_keep,
                             index_col="id",
                             dtype={
                                 "id": str,
                                 "name": str,
                                 "category": "category"
                             })

    # Get rid of biolink prefixes (saves space, makes for easier processing)
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    nodes_df.category = strip_biolink_prefix_vectorized(nodes_df.category)

    logging.info(f"KG2pre nodes dataframe is:\n {nodes_df}")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/1_match_nodes_kg2pre.tsv", sep="\t")
    return set(nodes_df.index)


def create_match_edges_kg2pre(all_kg2pre_node_ids: Set[str], kg2pre_version: str):
    logging.info(f"Creating KG2pre edges table...")

    # Load KG2pre data into edges table, including only the columns relevant to us
    edges_tsv_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/edges.tsv"
    edges_tsv_header_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/edges_header.tsv"
    edges_header_df = pd.read_table(edges_tsv_header_path)
    columns_to_keep = ["id", "subject", "predicate", "object", PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME]
    edges_df_all_predicates = pd.read_table(edges_tsv_path,
                                            names=list(edges_header_df.columns),
                                            usecols=columns_to_keep,
                                            index_col="id",
                                            dtype={"id": str,
                                                   "subject": str,
                                                   "predicate": "category",
                                                   "object": str,
                                                   PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME: "category"})
    if PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME != "primary_knowledge_source":
        edges_df_all_predicates.rename(columns={PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME: "primary_knowledge_source"},
                                       inplace=True)

    # Filter down to only 'match' edges from non-semmeddb sources
    logging.info(f"Filtering down to only 'match' edges..")
    match_predicates = {"biolink:same_as", "biolink:exact_match", "biolink:close_match"}
    edges_df = edges_df_all_predicates[edges_df_all_predicates.predicate.isin(match_predicates)]
    edges_df = edges_df[edges_df.primary_knowledge_source != "infores:semmeddb"]

    # Get rid of any orphan edges (generally only happens with test builds)
    logging.info(f"Filtering out any orphan edges..")
    edges_df = edges_df[edges_df.subject.isin(all_kg2pre_node_ids)]
    edges_df = edges_df[edges_df.object.isin(all_kg2pre_node_ids)]

    # Get rid of biolink prefixes (saves space, makes for easier processing)
    logging.info(f"Stripping biolink prefixes...")
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    edges_df.predicate = strip_biolink_prefix_vectorized(edges_df.predicate)

    logging.info(f"Edges dataframe is:\n {edges_df}")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/1_match_edges_kg2pre.tsv", sep="\t")


def run(kg2pre_version: str, download_fresh: bool):
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Download a fresh copy of KG2pre data, if requested
    if download_fresh:
        file_manager.download_kg2pre_tsvs(kg2pre_version)

    # Verify the local KG2pre files match the requested version
    file_manager.check_kg2pre_tsvs_version(kg2pre_version)

    # Transform KG2pre data into 'match graph' format
    all_kg2pre_node_ids = create_match_nodes_kg2pre(kg2pre_version)
    create_match_edges_kg2pre(all_kg2pre_node_ids, kg2pre_version)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    args = arg_parser.parse_args()
    run(args.kg2pre_version, args.download_fresh)


if __name__ == "__main__":
    main()
