import argparse
import logging
import os
import pathlib
import subprocess

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
KG2PRE_TSV_DIR = f"{KG2C_DIR}/kg2pre_tsvs"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])
PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME = "knowledge_source"


def strip_biolink_prefix(item: str) -> str:
    return item.replace("biolink:", "")


def download_kg2pre_tsvs():
    logging.info(f"Downloading KG2pre TSV source files to {KG2PRE_TSV_DIR}..")
    kg2pre_tarball_name = "kg2-tsv-for-neo4j.tar.gz"
    logging.info(f"Downloading {kg2pre_tarball_name} from the rtx-kg2 S3 bucket")
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2", f"s3://rtx-kg2/{kg2pre_tarball_name}", KG2C_DIR])
    logging.info(f"Unpacking {kg2pre_tarball_name}..")
    if not pathlib.Path(KG2PRE_TSV_DIR).exists():
        subprocess.check_call(["mkdir", KG2PRE_TSV_DIR])
    subprocess.check_call(["tar", "-xvzf", kg2pre_tarball_name, "-C", KG2PRE_TSV_DIR])


def create_nodes_table_kg2pre(kg2pre_version: str):
    logging.info(f"Creating KG2pre nodes table...")

    # Load KG2pre data into nodes table, including only the columns relevant to us
    nodes_tsv_path = f"{KG2PRE_TSV_DIR}/nodes.tsv"
    nodes_tsv_header_path = f"{KG2PRE_TSV_DIR}/nodes_header.tsv"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id", "name", "category"]
    nodes_df = pd.read_table(nodes_tsv_path, names=node_column_names, usecols=columns_to_keep, index_col="id")

    # Get rid of biolink prefixes (saves space, makes for easier processing)
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    nodes_df.category = strip_biolink_prefix_vectorized(nodes_df.category)

    # Make sure this is actually the KG2 version we are supposed to be using
    kg2pre_build_node_id = "RTX:KG2"
    if kg2pre_build_node_id in nodes_df.index:
        kg2pre_build_node = nodes_df.loc[kg2pre_build_node_id]
        kg2pre_build_node_name_chunks = kg2pre_build_node["name"].split(" ")  # Note: Using '.name' accessor here returns node ID for some reason...
        kg2pre_build_node_version = kg2pre_build_node_name_chunks[1].replace("KG", "")
        if kg2pre_build_node_version != kg2pre_version:
            raise ValueError(f"We appear to have the wrong KG2pre TSVs! Requested version was {kg2pre_version}, but the"
                             f" build node in the KG2pre TSVs says the version is {kg2pre_build_node_version}.")
    else:
        raise ValueError(f"No build node exists in the KG2pre TSVs! Cannot verify we have the correct KG2pre TSVs.")

    logging.info(f"KG2pre nodes dataframe is:\n {nodes_df}")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/match_nodes_kg2pre.tsv", sep="\t")


def create_edges_table_kg2pre():
    logging.info(f"Creating KG2pre edges table...")

    # Load KG2pre data into edges table, including only the columns relevant to us
    edges_tsv_path = f"{KG2PRE_TSV_DIR}/edges.tsv"
    edges_tsv_header_path = f"{KG2PRE_TSV_DIR}/edges_header.tsv"
    edges_header_df = pd.read_table(edges_tsv_header_path)
    edge_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in edges_header_df.columns]
    columns_to_keep = ["id", "subject", "predicate", "object", PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME]
    edges_df_all_predicates = pd.read_table(edges_tsv_path, names=edge_column_names, usecols=columns_to_keep, index_col="id")
    if PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME != "primary_knowledge_source":
        edges_df_all_predicates.rename(columns={PRIMARY_KNOWLEDGE_SOURCE_PROPERTY_NAME: "primary_knowledge_source"},
                                       inplace=True)

    # Filter down to only 'match' edges from non-semmeddb sources
    match_predicates = {"biolink:same_as", "biolink:exact_match", "biolink:close_match"}
    edges_df = edges_df_all_predicates[edges_df_all_predicates.predicate.isin(match_predicates)]
    edges_df = edges_df[edges_df.primary_knowledge_source != "infores:semmeddb"]

    # Get rid of biolink prefixes (saves space, makes for easier processing)
    strip_biolink_prefix_vectorized = np.vectorize(strip_biolink_prefix)
    edges_df.predicate = strip_biolink_prefix_vectorized(edges_df.predicate)

    logging.info(f"Edges dataframe is:\n {edges_df}")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/match_edges_kg2pre.tsv", sep="\t")


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    args = arg_parser.parse_args()

    # Download a fresh copy of KG2pre data, if requested
    if args.download_fresh:
        download_kg2pre_tsvs()

    # Transform KG2pre data into 'match graph' format
    create_nodes_table_kg2pre(args.kg2pre_version)
    create_edges_table_kg2pre()


if __name__ == "__main__":
    main()
