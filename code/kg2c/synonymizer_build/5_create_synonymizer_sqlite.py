import logging
import os
import pathlib
import sqlite3
import subprocess
from collections import defaultdict

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])


def create_synonymizer_sqlite(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
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

    # Create some helper maps for determining intra-cluster edges and other cluster info
    logging.info(f"Creating helper map of node IDs to their edge IDs...")
    nodes_to_edges_map = defaultdict(set)
    for _, edge_row in edges_df.iterrows():
        nodes_to_edges_map[edge_row.subject].add(edge_row.id)
        nodes_to_edges_map[edge_row.object].add(edge_row.id)
    logging.info(f"Creating helper map of cluster IDs to member IDs...")
    grouped_df = nodes_df.groupby(by="cluster_id").id
    cluster_to_member_ids = grouped_df.apply(list).to_dict()
    logging.info(f"Creating helper map of node IDs to categories..")
    nodes_to_category_map = dict(zip(nodes_df.id, nodes_df.category))
    logging.info(f"Creating helper map of node IDs to names..")
    nodes_df["name"] = np.where(nodes_df.name_sri == nodes_df.name_sri, nodes_df.name_sri, nodes_df.name_kg2pre)  # NaN value is not equal to itself
    nodes_to_name_map = dict(zip(nodes_df.id, nodes_df.name))

    # Figure out each clusters' intra-cluster edges
    # TODO: Might be able to do this faster using vectorization? See label propagation function for ideas..
    logging.info(f"Determining each cluster's intra-cluster edge IDs...")
    table_rows = []
    for cluster_id, member_ids in cluster_to_member_ids.items():
        # Create a list of every member's edge IDs, including repeats
        member_edge_ids_with_repeats = []
        for member_id in member_ids:
            edge_ids = nodes_to_edges_map.get(member_id, [])
            member_edge_ids_with_repeats += edge_ids
        # Then take advantage of the fact that each edge ID could only possibly be listed once or twice to efficiently
        # determine which are intra-cluster (since each edge has 2 nodes, 1 OR both of which must be in this cluster)
        member_edge_ids_with_repeats.sort()
        intra_cluster_edge_ids = set()
        index = 0
        while index < len(member_edge_ids_with_repeats) - 1:
            current_edge_id = member_edge_ids_with_repeats[index]
            next_edge_id = member_edge_ids_with_repeats[index + 1]
            if current_edge_id == next_edge_id:
                intra_cluster_edge_ids.add(current_edge_id)
                index = index + 2
            else:
                index = index + 1
        table_rows.append([cluster_id, nodes_to_category_map[cluster_id], nodes_to_name_map[cluster_id],
                           f"{member_ids}", f"{list(intra_cluster_edge_ids)}"])

    # Save a table of cluster info
    logging.info(f"Creating DataFrame of clusters (cluster_id, member_ids, intra_cluster_edge_ids)")
    clusters_df = pd.DataFrame(table_rows, columns=["cluster_id", "category", "name", "member_ids", "intra_cluster_edge_ids"]).set_index("cluster_id")
    logging.info(f"Clusters df is:\n{clusters_df}")
    logging.info(f"Dumping clusters DataFrame to sqlite..")
    clusters_df.to_sql("clusters", db_connection)
    db_connection.execute("CREATE UNIQUE INDEX cluster_id_index on clusters (cluster_id)")
    db_connection.commit()
    logging.info(f"Done saving data in sqlite")

    db_connection.close()

    # Save some reports about the graph content
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


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    logging.info(f"Loading nodes and edges TSVs into DataFrames..")
    # Load the match graph into DataFrames
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
    logging.info(f"Loaded nodes DF is:\n{nodes_df}")
    logging.info(f"Loaded edges DF is:\n{edges_df}")

    # Create the final database that will be the backend of the NodeSynonymizer
    create_synonymizer_sqlite(nodes_df, edges_df)


if __name__ == "__main__":
    main()
