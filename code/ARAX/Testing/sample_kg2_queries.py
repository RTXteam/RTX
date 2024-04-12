"""
This script grabs and saves a sample of real queries sent to our live KG2 endpoints. It deduplicates all queries
submitted to KG2 instances over the last X hours and saves a random sample of N of those queries to individual
JSON files. It also saves a summary of metadata about the queries in the sample. All output files are saved in a subdir
called 'sample_kg2_queries'.
Usage: python sample_kg2_queries.py <last_n_hours_to_sample_from> <sample_size>
"""
import copy
import csv
import json
import os
import random
import sys

import argparse
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/")
from ARAX_query_tracker import ARAXQueryTracker
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_num_input_curies(query_message: dict) -> int:
    qg = query_message["message"]["query_graph"]
    num_qnodes_with_curies = sum([1 for qnode in qg["nodes"].values() if qnode.get("ids")])
    if num_qnodes_with_curies == 1:
        for qnode in qg["nodes"].values():
            if qnode.get("ids"):
                return len(qnode["ids"])
    return 1


def get_query_hash_key(query_message: dict) -> Optional[str]:
    qg = query_message["message"]["query_graph"]
    qedge = next(qedge for qedge in qg["edges"].values()) if qg.get("edges") else None
    if not qedge:  # Invalid query; skip it
        return None
    subj_qnode_key = qedge["subject"]
    obj_qnode_key = qedge["object"]

    # Craft the subject portion
    subj_qnode = qg["nodes"][subj_qnode_key]
    subj_ids_str = ",".join(sorted(subj_qnode.get("ids", [])))
    subj_categories_str = ",".join(sorted(subj_qnode.get("categories", [])))
    subj_hash_str = f"({subj_ids_str}; {subj_categories_str})"

    # Craft the edge portion
    predicates_hash_str = ",".join(sorted(qedge.get("predicates", [])))
    qualifier_hash_strs = []
    for qualifier_blob in qedge.get("qualifier_constraints", []):
        qualifier_set = qualifier_blob["qualifier_set"]
        qual_predicate, obj_qual_direction, obj_qual_aspect = "", "", ""
        for qualifier_item in qualifier_set:
            if qualifier_item.get("qualifier_type_id") == "biolink:qualified_predicate":
                qual_predicate = qualifier_item["qualifier_value"]
            elif qualifier_item.get("qualifier_type_id") == "biolink:object_direction_qualifier":
                obj_qual_direction = qualifier_item["qualifier_value"]
            elif qualifier_item.get("qualifier_type_id") == "biolink:object_aspect_qualifier":
                obj_qual_aspect = qualifier_item["qualifier_value"]
        qualifier_hash_strs.append(f"{qual_predicate}--{obj_qual_direction}--{obj_qual_aspect}")
    qualifier_hash_str = ",".join(sorted(qualifier_hash_strs))
    edge_hash_str = f"[{predicates_hash_str}; {qualifier_hash_str}]"

    # Craft the object portion
    obj_qnode = qg["nodes"][obj_qnode_key]
    obj_ids_str = ",".join(sorted(obj_qnode.get("ids", [])))
    obj_categories_str = ",".join(sorted(obj_qnode.get("categories", [])))
    obj_hash_str = f"({obj_ids_str}; {obj_categories_str})"

    return f"{subj_hash_str}--{edge_hash_str}-->{obj_hash_str}"


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("last_n_hours", help="Number of hours prior to the present to select the sample from")
    arg_parser.add_argument("sample_size", help="Number of KG2 queries to include in random sample")
    args = arg_parser.parse_args()

    qt = ARAXQueryTracker()

    last_n_hours = float(args.last_n_hours)
    sample_size = int(args.sample_size)

    print(f"Getting all queries in last {last_n_hours} hours")
    queries = qt.get_entries(last_n_hours=float(last_n_hours))
    print(f"Got {len(queries)} queries back (for all instance types)")

    # Filter down only to KG2 queries
    kg2_queries = [query for query in queries if query.instance_name == "kg2"]
    print(f"There were a total of {len(kg2_queries)} KG2 queries in the last {last_n_hours} hours")

    # Deduplicate queries
    print(f"Deduplicating KG2 queries..")
    node_synonymizer = NodeSynonymizer()
    deduplicated_queries = dict()
    for query in kg2_queries:
        # Canonicalize any input curies
        canonicalized_query = copy.deepcopy(query.input_query)
        for qnode in canonicalized_query["message"]["query_graph"]["nodes"].values():
            qnode_ids = qnode.get("ids")
            if qnode_ids:
                canonicalized_ids_dict = node_synonymizer.get_canonical_curies(qnode_ids)
                canonicalized_ids = set()
                for input_id, canonicalized_info in canonicalized_ids_dict.items():
                    if canonicalized_info:
                        canonicalized_ids.add(canonicalized_info["preferred_curie"])
                    else:
                        canonicalized_ids.add(input_id)  # Just send the ID as is if synonymizer doesn't recognize it
                qnode["ids"] = list(canonicalized_ids)

        # Figure out if we've seen this query before using hash keys
        hash_key = get_query_hash_key(canonicalized_query)
        if hash_key and hash_key not in deduplicated_queries:
            deduplicated_queries[hash_key] = {"query_id": query.query_id,
                                              "query_hash_key": hash_key,
                                              "start_datetime": query.start_datetime,
                                              "submitter": query.origin,
                                              "instance_name": query.instance_name,
                                              "domain": query.domain,
                                              "elapsed": query.elapsed,
                                              "message_code": query.message_code,
                                              "input_query": query.input_query,
                                              "input_query_canonicalized": canonicalized_query}
    print(f"After deduplication, there were {len(deduplicated_queries)} unique KG2 queries "
          f"in the last {last_n_hours} hours ({round(len(deduplicated_queries)/len(kg2_queries), 2)*100}%)")

    # Create a subdir to save sample queries/metadata if one doesn't already exist
    sample_subdir = f"{SCRIPT_DIR}/sample_kg2_queries"
    if not os.path.exists(sample_subdir):
        os.system(f"mkdir {sample_subdir}")

    # Grab a random sample of queries from the deduplicated set and save them to json files
    print(f"Saving a random sample of {sample_size} deduplicated KG2 queries..")
    random_selection = random.sample(list(deduplicated_queries), sample_size)
    for query_hash_key in random_selection:
        query_dict = deduplicated_queries[query_hash_key]
        with open(f"{sample_subdir}/query_{query_dict['query_id']}.json", "w+") as query_file:
            json.dump(query_dict, query_file, indent=2)

    # Save a summary of the sample of queries for easier analysis
    print(f"Saving a summary of the query sample..")
    summary_col_names = ["query_id", "submitter", "instance_name", "domain", "start_datetime", "elapsed",
                         "message_code", "query_hash_key"]
    with open(f"{sample_subdir}/sample_summary.tsv", "w+") as summary_file:
        tsv_writer = csv.writer(summary_file, delimiter="\t")
        tsv_writer.writerow(summary_col_names)
        for query_hash_key in random_selection:
            query_dict = deduplicated_queries[query_hash_key]
            row = [query_dict[col_name] for col_name in summary_col_names]
            tsv_writer.writerow(row)

    print(f"Done.")


if __name__ == "__main__":
    main()
