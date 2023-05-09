import argparse
import logging
import os
import re
from typing import Optional

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
KG2PRE_TSV_DIR = f"{KG2C_DIR}/kg2pre_tsvs"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])


def strip_tabs_and_newlines(some_string: Optional[str]) -> Optional[str]:
    if some_string and some_string == some_string:  # Catches Pandas NaN values..
        return re.sub("\s+", " ", some_string)
    else:
        return some_string


def dump_kg2pre_node_info(kg2pre_version: str):
    # Load KG2pre node data into a dataframe, including only the columns relevant to us
    nodes_tsv_path = f"{KG2PRE_TSV_DIR}/nodes.tsv"
    nodes_tsv_header_path = f"{KG2PRE_TSV_DIR}/nodes_header.tsv"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id", "name", "full_name", "category", ]
    nodes_df = pd.read_table(nodes_tsv_path,
                             names=node_column_names,
                             usecols=columns_to_keep,
                             index_col="id",
                             dtype={
                                 "id": str,
                                 "name": str,
                                 "full_name": str,
                                 "category": "category"
                             })

    # Strip any tabs and newlines from names
    strip_tabs_and_newlines_vectorized = np.vectorize(strip_tabs_and_newlines)
    nodes_df.name = strip_tabs_and_newlines_vectorized(nodes_df.name)
    nodes_df.full_name = strip_tabs_and_newlines_vectorized(nodes_df.full_name)

    # Make sure this is actually the KG2 version we are supposed to be using
    logging.info(f"Verifying that the KG2pre version in the KG2pre TSVs matches what was requested..")
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

    logging.info(f"Node info for autocomplete dataframe is:\n {nodes_df}")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/autocomplete_node_info.tsv", sep="\t", header=False,
                    columns=["name", "full_name", "category"])  # Makes sure they're in the right order


def main():
    logging.info(f"\n\n Starting to dump node info for autocomplete service... \n")
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    args = arg_parser.parse_args()

    # Transform KG2pre data into 'match graph' format
    dump_kg2pre_node_info(args.kg2pre_version)


if __name__ == "__main__":
    main()
