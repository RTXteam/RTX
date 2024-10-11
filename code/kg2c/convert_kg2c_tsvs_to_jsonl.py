"""
This script converts the KG2c TSV files into JSON lines format, and also filters out certain low-quality edges.

Usage: python convert_kg2c_tsvs_to_jsonl.py [--test]
"""
import argparse
import ast
import csv
import logging
import os
import sys
import time

import jsonlines
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import file_manager

KG2C_DIR = os.path.dirname(os.path.abspath(__file__))
KG2PRE_TSVS_DIR = f"{KG2C_DIR}/kg2pre_tsvs"
ARRAY_DELIMITER = "ǂ"
EMPTY_VALUES = {"", "{}", "[]", None}
ARRAY_COL_NAMES = {"all_names", "all_categories", "equivalent_curies", "publications", "kg2_ids"}
LITE_PROPERTIES = {"id", "name", "category", "all_categories",
                   "subject", "object", "predicate", "primary_knowledge_source"}
csv.field_size_limit(sys.maxsize)  # Required because some KG2c fields are massive

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler("build.log"),
                              logging.StreamHandler()])


def parse_value(value: any, col_name: str) -> any:
    if isinstance(value, str):
        if col_name in ARRAY_COL_NAMES:
            return value.split(ARRAY_DELIMITER)
        elif value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.isdigit():
            return int(value)
        elif col_name == "publications_info":
            return ast.literal_eval(value)
        else:
            return value
    else:
        return value


def convert_tsv_to_jsonl(tsv_path: str, header_tsv_path: str):
    """
    This method assumes the input TSV file names are in KG2c format (e.g., like nodes_c.tsv and nodes_c_header.tsv)
    """
    logging.info(f"Starting to process file {tsv_path} (header file is: {header_tsv_path})")

    jsonl_output_file_path_lite = tsv_path.replace('.tsv', '_lite.jsonl')
    jsonl_output_file_path = tsv_path.replace('.tsv', '.jsonl')
    logging.info(f"Output file path for lite version will be: {jsonl_output_file_path_lite}")
    logging.info(f"Output file path for full version will be: {jsonl_output_file_path}")

    # First load column names and remove the ':type' suffixes neo4j requires on column names
    header_df = pd.read_table(header_tsv_path)
    column_names = [col_name.split(":")[0] if not col_name.startswith(":") else col_name
                    for col_name in header_df.columns]
    node_column_indeces = {col_name: index for index, col_name in enumerate(column_names)}
    logging.info(f"All columns mapped to their indeces are: {node_column_indeces}")
    columns_to_keep = [col_name for col_name in column_names if not col_name.startswith(":")]
    logging.info(f"Non-neo4j-specific columns from TSV are: {columns_to_keep}")

    logging.info(f"Starting to convert rows in {tsv_path} to json lines..")
    with open(tsv_path, "r") as input_tsv_file:

        with jsonlines.open(jsonl_output_file_path, mode="w") as jsonl_writer:
            with jsonlines.open(jsonl_output_file_path_lite, mode="w") as jsonl_writer_lite:
                batch = []
                batch_lite = []
                num_rows_written = 0
                tsv_reader = csv.reader(input_tsv_file, delimiter="\t")
                for line in tsv_reader:
                    row_obj = dict()
                    for col_name in columns_to_keep:
                        raw_value = line[node_column_indeces[col_name]]
                        if raw_value not in EMPTY_VALUES:  # Skip empty values, not false ones
                            row_obj[col_name] = parse_value(raw_value, col_name)

                    # Skip this row if it's an edge we're required to filter out of KG2
                    is_low_quality_semmed_edge = (row_obj.get("primary_knowledge_source") == "infores:semmeddb"
                                                  and len(row_obj.get("publications", [])) < 4)
                    if not (is_low_quality_semmed_edge or row_obj.get("domain_range_exclusion")):
                        # Create both the 'lite' and 'full' files at the same time
                        batch.append(row_obj)
                        batch_lite.append({property_name: value for property_name, value in row_obj.items()
                                           if property_name in LITE_PROPERTIES})
                        if len(batch) == 1000000:
                            jsonl_writer.write_all(batch)
                            jsonl_writer_lite.write_all(batch_lite)
                            num_rows_written += len(batch)
                            batch = []
                            batch_lite = []
                            logging.info(f"Have written {num_rows_written} rows...")

                # Take care of writing the (potential) final partial batch
                if batch:
                    jsonl_writer.write_all(batch)
                    jsonl_writer_lite.write_all(batch_lite)

    logging.info(f"Done converting rows in {tsv_path} to json lines.")
    logging.info(f"Line counts of output files:")
    logging.info(os.system(f"wc -l {jsonl_output_file_path}"))
    logging.info(os.system(f"wc -l {jsonl_output_file_path_lite}"))


def run(is_test: bool):
    start = time.time()
    logging.info(f"Beginning to convert KG2c TSVs to json lines format (and filter out low-quality edges)..")
    nodes_tsv_path = f"{KG2C_DIR}/nodes_c.tsv{'_TEST' if is_test else ''}"
    nodes_header_tsv_path = f"{KG2C_DIR}/nodes_c_header.tsv{'_TEST' if is_test else ''}"
    convert_tsv_to_jsonl(nodes_tsv_path, nodes_header_tsv_path)
    edges_tsv_path = f"{KG2C_DIR}/edges_c.tsv{'_TEST' if is_test else ''}"
    edges_header_tsv_path = f"{KG2C_DIR}/edges_c_header.tsv{'_TEST' if is_test else ''}"
    convert_tsv_to_jsonl(edges_tsv_path, edges_header_tsv_path)
    logging.info(f"Conversion to json lines is complete. Took {round((time.time() - start) / 60)} minutes.")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--test', dest='is_test', action='store_true')
    args = arg_parser.parse_args()

    run(args.is_test)


if __name__ == "__main__":
    main()
