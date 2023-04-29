import logging
import os
import pathlib
import sqlite3
import subprocess
from collections import defaultdict

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])


def save_cluster_data_for_debugging(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # Get sqlite set up
    sqlite_db_path = f"{SYNONYMIZER_BUILD_DIR}/5_clusters.sqlite"
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
    logging.info(f"Creating index on edge subject...")
    db_connection.execute("CREATE INDEX subject_index on edges (subject)")
    logging.info(f"Creating index on edge object...")
    db_connection.execute("CREATE INDEX object_index on edges (object)")
    db_connection.commit()

    # Create some helper maps for determining intra-cluster edges
    logging.info(f"Creating map of nodes to their edge IDs...")
    nodes_to_edges_map = defaultdict(set)
    for _, edge_row in edges_df.iterrows():
        nodes_to_edges_map[edge_row.subject].add(edge_row.id)
        nodes_to_edges_map[edge_row.object].add(edge_row.id)
    logging.info(f"Creating map of cluster IDs to member IDs...")
    grouped_df = nodes_df.groupby(by="cluster_id").id
    cluster_to_member_ids = grouped_df.apply(list).to_dict()

    # Figure out each clusters' intra-cluster edges
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
        table_rows.append([cluster_id, f"{member_ids}", f"{list(intra_cluster_edge_ids)}"])

    # Save a table of cluster info
    logging.info(f"Creating DataFrame of cluster info (cluster_id, member_ids, intra_cluster_edge_ids)")
    cluster_info_df = pd.DataFrame(table_rows, columns=["cluster_id", "member_ids", "intra_cluster_edge_ids"]).set_index("cluster_id")
    logging.info(f"Cluster info df is:\n{cluster_info_df}")
    logging.info(f"Dumping cluster info DataFrame to sqlite..")
    cluster_info_df.to_sql("cluster_info", db_connection)
    db_connection.execute("CREATE UNIQUE INDEX cluster_id_index on cluster_info (cluster_id)")
    db_connection.commit()
    logging.info(f"Done saving data in sqlite")

    db_connection.close()


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

    # Create a sqlite database for easy inspection/debugging of clusters
    save_cluster_data_for_debugging(nodes_df, edges_df)


if __name__ == "__main__":
    main()
