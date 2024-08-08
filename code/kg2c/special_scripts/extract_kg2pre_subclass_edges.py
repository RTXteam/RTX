import argparse
import logging
import os
import sys

import jsonlines
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # KG2c dir
import file_manager

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
KG2PRE_TSVS_DIR = f"{KG2C_DIR}/kg2pre_tsvs"


def extract_subclass_edges(kg2pre_version: str, is_test: bool):
    logging.info(f"Loading KG2pre edges table...")

    # Load KG2pre data into edges table, including only the columns relevant to us
    edges_tsv_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/edges.tsv{'_TEST' if is_test else ''}"
    edges_tsv_header_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}/edges_header.tsv{'_TEST' if is_test else ''}"
    edges_header_df = pd.read_table(edges_tsv_header_path)
    columns_to_keep = ["subject", "predicate", "object", "agent_type", "primary_knowledge_source"]
    edges_df_all_predicates = pd.read_table(edges_tsv_path,
                                            names=list(edges_header_df.columns),
                                            usecols=columns_to_keep,
                                            dtype={"subject": str,
                                                   "predicate": "category",
                                                   "object": str,
                                                   "agent_type": "category",
                                                   "primary_knowledge_source": "category"})

    # Filter down to only subclass edges from manual (or manually reviewed) sources
    logging.info(f"Filtering down to only subclass/superclass edges from manual (or manually reviewed) sources..")
    subclass_predicates = {"biolink:subclass_of", "biolink:superclass_of"}
    agent_types = {"manual_agent", "manual_validation_of_automated_agent"}
    edges_df = edges_df_all_predicates[edges_df_all_predicates.predicate.isin(subclass_predicates)]
    edges_df = edges_df[edges_df.agent_type.isin(agent_types)]

    # Drop agent type since we don't need that anymore
    edges_df.drop(columns=["agent_type"], inplace=True)

    logging.info(f"Manual subclass edges dataframe is:\n {edges_df}")
    subclass_edges_objs = edges_df.to_dict(orient="records")
    subclass_edges_jsonl_file_name = f"kg{kg2pre_version}pre_subclass_edges_manual_agent.jsonl{'_TEST' if is_test else ''}"
    subclass_edges_jsonl_path = f"{SCRIPT_DIR}/{subclass_edges_jsonl_file_name}"
    with jsonlines.open(subclass_edges_jsonl_path, mode="w") as writer:
        writer.write_all(subclass_edges_objs)
    file_manager.gzip_file(subclass_edges_jsonl_path)
    file_manager.upload_file_to_arax_databases_server(local_file_path=f"{subclass_edges_jsonl_path}.gz",
                                                      remote_file_name=f"{subclass_edges_jsonl_file_name}.gz",
                                                      kg2pre_version=kg2pre_version,
                                                      is_extra_file=True)


def run(kg2pre_version: str, download_fresh: bool, is_test: bool):
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Download a fresh copy of KG2pre data, if requested
    if download_fresh:
        file_manager.download_kg2pre_tsvs(kg2pre_version)

    # Verify the local KG2pre files match the requested version
    file_manager.check_kg2pre_tsvs_version(kg2pre_version)

    # Extract selected KG2pre subclass edges
    extract_subclass_edges(kg2pre_version, is_test)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    arg_parser.add_argument('--test', dest='is_test', action='store_true')
    args = arg_parser.parse_args()
    run(args.kg2pre_version, args.download_fresh, args.is_test)


if __name__ == "__main__":
    main()
