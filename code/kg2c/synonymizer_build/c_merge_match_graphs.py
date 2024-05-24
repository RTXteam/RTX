import csv
import logging
import os
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
KG2PRE_RESOURCE_ID = "infores:rtx-kg2"
SRI_NN_RESOURCE_ID = "infores:sri-node-normalizer"
ROW_BATCH_SIZE = 1000000


def merge_edges():
    logging.info(f"Merging edges into one unified match graph..")
    # We don't actually have to merge individual edges; just tack SRI edges onto KG2 edges, record source
    with open(f"{SYNONYMIZER_BUILD_DIR}/3_merged_match_edges.tsv", "w+") as merged_edges_file:
        writer = csv.writer(merged_edges_file, delimiter="\t")
        merged_headers = ["id", "subject", "predicate", "object", "upstream_resource_id", "primary_knowledge_source"]
        writer.writerow(merged_headers)

        # First process and save KG2pre edges
        with open(f"{SYNONYMIZER_BUILD_DIR}/1_match_edges_kg2pre.tsv") as kg2pre_edges_file:
            reader = csv.reader(kg2pre_edges_file, delimiter="\t")
            kg2pre_headers = next(reader)
            write_edges_in_batches(reader, writer, KG2PRE_RESOURCE_ID, kg2pre_headers)

        # Then process and save SRI NN edges
        with open(f"{SYNONYMIZER_BUILD_DIR}/2_match_edges_sri.tsv") as sri_edges_file:
            reader = csv.reader(sri_edges_file, delimiter="\t")
            sri_headers = next(reader)
            write_edges_in_batches(reader, writer, SRI_NN_RESOURCE_ID, sri_headers)


def write_edges_in_batches(reader: csv.reader, writer: csv.writer, upstream_resource_id: str, source_headers: List[str]):
    id_col = source_headers.index("id")
    subject_col = source_headers.index("subject")
    predicate_col = source_headers.index("predicate")
    object_col = source_headers.index("object")
    primary_knowledge_source_col = source_headers.index("primary_knowledge_source") if "primary_knowledge_source" in source_headers else None

    node_ids_used_by_edges = set()
    row_batch = []
    row_count = 0
    for row in reader:
        # First record which nodes are involved in this edge
        node_ids_used_by_edges.add(row[subject_col])
        node_ids_used_by_edges.add(row[object_col])
        # Then convert the edge to 'merged' format
        primary_knowledge_source = row[primary_knowledge_source_col] if primary_knowledge_source_col is not None else None
        merged_row = [row[id_col], row[subject_col], row[predicate_col], row[object_col], upstream_resource_id, primary_knowledge_source]
        row_batch.append(merged_row)
        if len(row_batch) == ROW_BATCH_SIZE:
            row_count += ROW_BATCH_SIZE
            writer.writerows(row_batch)
            logging.info(f"Have written a total of {row_count:,} merged {upstream_resource_id} edges..")
            row_batch = []
    # Write any remaining rows in the final partial batch
    if row_batch:
        row_count += len(row_batch)
        writer.writerows(row_batch)
    logging.info(f"Done writing merged {upstream_resource_id} edges; there were {row_count:,} in total")


def merge_nodes():
    # Merge the KG2pre and SRI node sets
    logging.info(f"Merging nodes into one unified match graph..")

    with open(f"{SYNONYMIZER_BUILD_DIR}/3_merged_match_nodes.tsv", "w+") as merged_nodes_file:
        writer = csv.writer(merged_nodes_file, delimiter="\t")
        merged_headers = ["id", "cluster_id",
                          "category_kg2pre", "name_kg2pre",
                          "category_sri", "name_sri"]
        writer.writerow(merged_headers)

        # First load KG2pre nodes into memory (small enough to fit)
        with open(f"{SYNONYMIZER_BUILD_DIR}/1_match_nodes_kg2pre.tsv") as kg2pre_nodes_file:
            reader = csv.reader(kg2pre_nodes_file, delimiter="\t")
            kg2pre_headers = next(reader)
            kg2pre_id_col = kg2pre_headers.index("id")
            kg2pre_category_col = kg2pre_headers.index("category")
            kg2pre_name_col = kg2pre_headers.index("name")
            kg2pre_nodes_dict = {row[kg2pre_id_col]: row for row in reader}

        # Then go through SRI nodes, merge them as necessary with KG2pre nodes, and write them in batches
        with open(f"{SYNONYMIZER_BUILD_DIR}/2_match_nodes_sri.tsv") as sri_nodes_file:
            reader = csv.reader(sri_nodes_file, delimiter="\t")
            sri_headers = next(reader)
            sri_id_col = sri_headers.index("id")
            sri_category_col = sri_headers.index("category")
            sri_name_col = sri_headers.index("name")
            sri_cluster_id_col = sri_headers.index("cluster_id")
            row_batch = []
            num_sri_nodes_processed = 0
            for sri_row in reader:
                num_sri_nodes_processed += 1
                node_id = sri_row[sri_id_col]
                # Merge node if it's present in both KG2pre and SRI NN
                if node_id in kg2pre_nodes_dict:
                    kg2pre_row = kg2pre_nodes_dict[node_id]
                    merged_row = [node_id, sri_row[sri_cluster_id_col],
                                  kg2pre_row[kg2pre_category_col], kg2pre_row[kg2pre_name_col],
                                  sri_row[sri_category_col], sri_row[sri_name_col]]
                    del kg2pre_nodes_dict[node_id]
                # Otherwise this node is only in SRI NN; just transform it to 'merged' format
                else:
                    merged_row = [node_id, sri_row[sri_cluster_id_col],
                                  None, None,
                                  sri_row[sri_category_col], sri_row[sri_name_col]]

                row_batch.append(merged_row)

                # Write this batch if it's big enough
                if len(row_batch) == ROW_BATCH_SIZE:
                    row_batch = write_node_batch(writer, row_batch)
                    logging.info(f"Have written a total of {num_sri_nodes_processed:,} merged SRI nodes..")

        # Then take care of any KG2pre nodes that WEREN'T in SRI NN
        logging.info(f"Processing the {len(kg2pre_nodes_dict):,} KG2pre nodes that were not in SRI NN..")
        for remaining_node_id, kg2pre_row in kg2pre_nodes_dict.items():
            merged_row = [remaining_node_id, None,
                          kg2pre_row[kg2pre_category_col], kg2pre_row[kg2pre_name_col],
                          None, None]
            row_batch.append(merged_row)
        _ = write_node_batch(writer, row_batch)

        logging.info(f"Done writing merged nodes.")


def write_node_batch(writer: csv.writer, rows: list):
    logging.debug(f"Writing batch of {len(rows)} merged nodes..")
    writer.writerows(rows)
    return []


def run():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Merge KG2pre and SRI NN data
    merge_edges()
    merge_nodes()


def main():
    run()


if __name__ == "__main__":
    main()
