import json
import logging
import os
import pathlib
import sqlite3
import subprocess
from collections import defaultdict
from typing import Dict, Set, List

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])


def load_final_nodes() -> pd.DataFrame:
    nodes_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/4_match_nodes_preprocessed.tsv",
                             dtype={
                                 "id": str,
                                 "cluster_id": str,
                                 "category": "category",
                                 "major_branch": "category",
                                 "category_kg2pre": "category",
                                 "name_kg2pre": str,
                                 "category_sri": "category",
                                 "name_sri": str
                             })
    logging.info(f"Loaded nodes DF is:\n{nodes_df}")
    return nodes_df


def load_final_edges() -> pd.DataFrame:
    edges_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/4_match_edges_preprocessed.tsv",
                             dtype={
                                 "id": str,
                                 "subject": str,
                                 "predicate": "category",
                                 "object": str,
                                 "upstream_resource_id": "category",
                                 "primary_knowledge_source": "category",
                                 "weight": float
                             })
    logging.info(f"Loaded edges DF is:\n{edges_df}")
    return edges_df


def convert_list_to_str(list_value: List[any]) -> str:
    return json.dumps(list_value)  # We want to convert to str for sqlite..


def create_synonymizer_sqlite(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> Dict[str, Set[str]]:
    # Get sqlite set up
    sqlite_db_path = f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite"
    if pathlib.Path(sqlite_db_path).exists():
        subprocess.check_call(["rm", sqlite_db_path])
    db_connection = sqlite3.connect(sqlite_db_path)

    # Save nodes table
    logging.info(f"Dumping nodes table to sqlite...")
    nodes_df.to_sql("nodes", con=db_connection, index=False)
    logging.info(f"Creating index on node ID...")
    db_connection.execute("CREATE UNIQUE INDEX node_id_index on nodes (id)")
    db_connection.commit()

    # Save edges table
    logging.info(f"Dumping edges table to sqlite...")
    edges_df.to_sql("edges", con=db_connection, index=False)
    logging.info(f"Creating index on edge ID...")
    db_connection.execute("CREATE UNIQUE INDEX edge_id_index on edges (id)")
    db_connection.commit()

    # Start compiling a clusters table
    logging.info(f"Beginning to create clusters DataFrame...")
    clusters_df = nodes_df[nodes_df.cluster_id == nodes_df.id]
    clusters_df = clusters_df[["cluster_id", "category", "name"]]

    # Then add member node IDs to each cluster row
    logging.info(f"Adding member node IDs to each cluster row...")
    logging.info(f"First grouping nodes by cluster id..")
    grouped_df = nodes_df.groupby(by="cluster_id").id
    logging.info(f"Now converting the grouped DataFrame into dictionary format..")
    cluster_to_member_ids = grouped_df.apply(list).to_dict()
    logging.info(f"Now mapping that dictionary to the clusters DataFrame...")
    clusters_df["member_ids"] = clusters_df.cluster_id.map(cluster_to_member_ids)
    logging.info(f"Now converting list member IDs to string representation...")
    convert_list_to_str_vectorized = np.vectorize(convert_list_to_str, otypes=[str])
    clusters_df.member_ids = convert_list_to_str_vectorized(clusters_df.member_ids)

    # Then add intra-cluster edge IDs to each cluster row
    logging.info(f"Adding intra-cluster edge IDs to each cluster row...")
    logging.info(f"First creating a map of nodes to cluster id...")
    nodes_to_cluster_id_map = dict(zip(nodes_df.id, nodes_df.cluster_id))
    logging.info(f"Now assigning edges their cluster subj/obj IDs..")
    edges_df["subject_cluster_id"] = edges_df.subject.map(nodes_to_cluster_id_map)
    edges_df["object_cluster_id"] = edges_df.object.map(nodes_to_cluster_id_map)
    logging.info(f"After tagging edges with subj/obj cluster IDs, edges df is: \n{edges_df}")
    logging.info(f"Filtering out any INTER-cluster edges..")
    intra_cluster_edges_df = edges_df[edges_df.subject_cluster_id == edges_df.object_cluster_id]
    logging.info(f"Grouping INTRA-cluster edges by their cluster IDs..")
    intra_cluster_edges_df_grouped = intra_cluster_edges_df.groupby(by="subject_cluster_id").id
    logging.info(f"Converting grouped clusters into dictionary format...")
    cluster_to_edge_ids = intra_cluster_edges_df_grouped.apply(list).to_dict()
    logging.info(f"Mapping cluster edge IDs onto clusters DataFrame...")
    clusters_df["intra_cluster_edge_ids"] = clusters_df.cluster_id.map(cluster_to_edge_ids)
    logging.info(f"Now converting list edge IDs to string representation...")
    clusters_df.intra_cluster_edge_ids = convert_list_to_str_vectorized(clusters_df.intra_cluster_edge_ids)
    logging.info(f"After filling out all columns, clusters DataFrame is: \n{clusters_df}")

    # Save a table of cluster info
    logging.info(f"Dumping clusters DataFrame to sqlite..")
    clusters_df.to_sql("clusters", db_connection)
    db_connection.execute("CREATE UNIQUE INDEX cluster_id_index on clusters (cluster_id)")
    db_connection.commit()
    logging.info(f"Done saving data in sqlite")

    db_connection.close()

    return cluster_to_member_ids


def write_graph_reports(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, cluster_to_member_ids: Dict[str, Set[str]]):
    logging.info(f"Writing some reports about the graph's content..")

    logging.info(f"First calculating the size of each node's cluster..")
    cluster_ids_to_sizes = {cluster_id: len(member_ids) for cluster_id, member_ids in cluster_to_member_ids.items()}
    nodes_df["cluster_size"] = nodes_df.cluster_id.map(cluster_ids_to_sizes)
    cluster_size_counts_df = nodes_df.groupby("cluster_size").size().to_frame("num_nodes")
    logging.info(f"Cluster size counts DataFrame is: \n{cluster_size_counts_df}")
    cluster_size_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_cluster_sizes.tsv", sep="\t")

    logging.info(f"Now saving report on cluster size but for only non-sri nodes..")
    logging.info(f"First locating which nodes from KG2 were not recognized by the SRI..")
    kg2_nodes_not_in_sri_df = nodes_df[nodes_df.category_sri != nodes_df.category_sri]
    logging.info(f"DataFrame of KG2 nodes that are not recognized by the SRI is: \n{kg2_nodes_not_in_sri_df}")
    logging.info(f"Grouping non-SRI nodes by cluster size..")
    cluster_size_counts_df_non_sri_nodes = kg2_nodes_not_in_sri_df.groupby("cluster_size").size().to_frame("num_nodes")
    logging.info(f"Cluster size counts DataFrame for KG2pre nodes not recognized by SRI is: \n{cluster_size_counts_df_non_sri_nodes}")
    cluster_size_counts_df_non_sri_nodes.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_cluster_sizes_non_sri_nodes.tsv", sep="\t")

    logging.info(f"Creating category count report..")
    category_counts_df = nodes_df.groupby("category").size().to_frame("num_nodes").sort_values(by=["num_nodes"], ascending=False)
    logging.info(f"Category counts DataFrame is: \n{category_counts_df}")
    category_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_category_counts.tsv", sep="\t")

    logging.info(f"Creating major branch report..")
    major_branch_counts_df = nodes_df.groupby("major_branch").size().to_frame("num_nodes").sort_values(by=["num_nodes"], ascending=False)
    logging.info(f"Major branch counts DataFrame is: \n{major_branch_counts_df}")
    major_branch_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_major_branch_counts.tsv", sep="\t")

    logging.info(f"Creating upstream resource report..")
    resource_counts_df = edges_df.groupby("upstream_resource_id").size().to_frame("num_edges").sort_values(by=["num_edges"], ascending=False)
    logging.info(f"Upstream resource counts DataFrame is: \n{resource_counts_df}")
    resource_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_upstream_resource_counts.tsv", sep="\t")

    logging.info(f"Creating primary knowledge source report..")
    ks_counts_df = edges_df.groupby("primary_knowledge_source").size().to_frame("num_edges").sort_values(by=["num_edges"], ascending=False)
    logging.info(f"Primary knowledge source counts DataFrame is: \n{ks_counts_df}")
    ks_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_primary_knowledge_source_counts.tsv", sep="\t")

    logging.info(f"Creating predicate report..")
    predicate_counts_df = edges_df.groupby("predicate").size().to_frame("num_edges").sort_values(by=["num_edges"], ascending=False)
    logging.info(f"Predicate counts DataFrame is: \n{predicate_counts_df}")
    predicate_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_predicate_counts.tsv", sep="\t")

    logging.info(f"Looking for any clusters that seem oversized..")
    nodes_in_oversized_clusters_df = nodes_df[nodes_df.cluster_size > 50]
    logging.info(f"DataFrame of nodes in clusters that seem oversized is: \n{nodes_in_oversized_clusters_df}")
    oversized_clusters_df = nodes_in_oversized_clusters_df[["cluster_id", "cluster_size"]].drop_duplicates().sort_values(by=["cluster_size"], ascending=False)
    logging.info(f"{oversized_clusters_df.shape[0]} clusters seem to be oversized: \n{oversized_clusters_df}")
    oversized_clusters_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_oversized_clusters.tsv", sep="\t", index=False)


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    logging.info(f"Loading nodes and edges TSVs into DataFrames..")
    # Load the match graph into DataFrames
    nodes_df = load_final_nodes()
    edges_df = load_final_edges()

    # Create the final database that will be the backend of the NodeSynonymizer
    cluster_to_member_ids = create_synonymizer_sqlite(nodes_df, edges_df)

    # Save some reports about the graph's content (meta-level)
    write_graph_reports(nodes_df, edges_df, cluster_to_member_ids)


if __name__ == "__main__":
    main()
