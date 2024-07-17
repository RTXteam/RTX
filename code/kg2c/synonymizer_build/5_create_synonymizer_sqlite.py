import json
import logging
import os
import pathlib
import sqlite3
import string
import subprocess

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"

UNNECESSARY_CHARS_MAP = {ord(char): None for char in string.punctuation + string.whitespace}


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


def add_biolink_prefix(category: str) -> str:
    if category.startswith("biolink:"):
        return category
    else:
        return f"biolink:{category}"


def capitalize_curie_prefix(curie: str) -> str:
    curie_chunks = curie.split(":")
    curie_chunks[0] = curie_chunks[0].upper()
    return ":".join(curie_chunks)


def create_synonymizer_sqlite(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> pd.DataFrame:
    # Get sqlite set up
    sqlite_db_path = f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite"
    logging.info(f"Synonymizer will be saved to: {sqlite_db_path}")
    if pathlib.Path(sqlite_db_path).exists():
        os.system(f"rm {sqlite_db_path}")
    db_connection = sqlite3.connect(sqlite_db_path)

    # Add a column of simplified names (for better name-based lookup)
    logging.info(f"Assigning nodes their simplified names...")
    nodes_df["name_simplified"] = nodes_df.name.apply(lambda name: name.lower().translate(UNNECESSARY_CHARS_MAP) if name == name else np.nan)
    logging.info(f"After adding simplified names, DataFrame is: \n{nodes_df}")

    # Add a column of simplified IDs (prefixes in all caps)
    logging.info(f"Assigning nodes their simplified IDs...")
    nodes_df["id_simplified"] = nodes_df.id.apply(capitalize_curie_prefix)
    logging.info(f"After adding simplified ids, DataFrame is: \n{nodes_df}")
    # Report any duplicate nodes (if they exist it'll produce an error further on during index creation)
    duplicate_ids = {i: rows for i, rows in nodes_df.groupby(['id_simplified']) if len(rows) > 1}
    if duplicate_ids:
        duplicates_report_file_path = f"{SYNONYMIZER_BUILD_DIR}/5_duplicate_simplified_ids.json"
        logging.warning(f"Found {len(duplicate_ids)} simplified IDs that have duplicates. This shouldn't happen. "
                        f"Saving these to {duplicates_report_file_path}.")
        with open(duplicates_report_file_path, "w+") as duplicate_file:
            json.dump(duplicate_ids, duplicate_file, indent=2)

    # Save nodes table
    logging.info(f"Dumping nodes table to sqlite...")
    nodes_df.to_sql("nodes", con=db_connection, index=False)
    logging.info(f"Creating index on node ID...")
    db_connection.execute("CREATE UNIQUE INDEX node_id_index on nodes (id)")
    logging.info(f"Creating index on simplified node ID...")
    db_connection.execute("CREATE UNIQUE INDEX node_id_simplified on nodes (id_simplified)")
    logging.info(f"Creating index on node name...")
    db_connection.execute("CREATE INDEX node_name on nodes (name)")
    logging.info(f"Creating index on node name simplified...")
    db_connection.execute("CREATE INDEX node_name_simplified on nodes (name_simplified)")
    logging.info(f"Creating index on node cluster_id...")
    db_connection.execute("CREATE INDEX node_cluster_id on nodes (cluster_id)")
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
    logging.info(f"Now converting the grouped DataFrame into list format..")
    cluster_to_member_ids_df = grouped_df.apply(list).reset_index(name="member_ids")
    logging.info(f"Now zipping member IDs DataFrame with clusters DataFrame...")
    clusters_df = pd.merge(clusters_df, cluster_to_member_ids_df, how="inner", on="cluster_id")
    logging.info(f"After joining, clusters DataFrame is: \n{clusters_df}")
    logging.info(f"Now recording cluster sizes, before we convert member IDs list into string format...")
    clusters_df["cluster_size"] = clusters_df.member_ids.apply(len)
    logging.info(f"After finishing adding member IDs, clusters DataFrame is: \n{clusters_df}")

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
    logging.info(f"Now converting the grouped DataFrame into list format..")
    cluster_to_edge_ids_df = intra_cluster_edges_df_grouped.apply(list).reset_index(name="intra_cluster_edge_ids")
    cluster_to_edge_ids_df.rename(columns={"subject_cluster_id": "cluster_id"}, inplace=True)
    logging.info(f"Now zipping intra-cluster edge IDs DataFrame with clusters DataFrame...")
    clusters_df = pd.merge(clusters_df, cluster_to_edge_ids_df, how="left", on="cluster_id")
    logging.info(f"After finishing adding intra-cluster edge IDs, clusters DataFrame is: \n{clusters_df}")

    # Go through and choose 'best' cluster name for clusters whose preferred identifiers don't have a name
    logging.info(f"Choosing best name for clusters whose cluster rep has no name (from either SRI or KG2)")
    nodes_with_names_df = nodes_df[nodes_df["name"] == nodes_df["name"]]
    logging.info(f"DataFrame of nodes with names is: \n{nodes_with_names_df}")
    logging.info(f"Dropping all but one named node per cluster (first row is retained)..")
    one_named_node_per_cluster_df = nodes_with_names_df.drop_duplicates(subset=["cluster_id"])[["cluster_id", "name"]]
    one_named_node_per_cluster_df.rename(columns={"name": "name_chosen"}, inplace=True)
    logging.info(f"After dropping all but one named node per cluster, DataFrame of named nodes "
                 f"is:\n{one_named_node_per_cluster_df}")
    logging.info(f"Joining chosen cluster names with clusters DF..")
    clusters_df = pd.merge(clusters_df, one_named_node_per_cluster_df, how="left", on="cluster_id")
    logging.info(f"After joining, clusters DF is: \n{clusters_df}")
    # Use chosen name as cluster name for clusters lacking a name
    logging.info(f"Replacing missing cluster names with chosen names where appropriate..")
    clusters_df["name"] = np.where(clusters_df["name"] != clusters_df["name"], clusters_df.name_chosen, clusters_df["name"])
    logging.info(f"After filling missing names, clusters DF is: \n{clusters_df}")
    logging.info(f"Deleting temporary chosen name column..")
    clusters_df.drop(columns=["name_chosen"], inplace=True)
    logging.info(f"After dropping temporary column, clusters DF is: \n{clusters_df}")

    # Convert our list values into strings, for sqlite-compatible format
    logging.info(f"Now converting list member IDs to string representation...")
    clusters_df.member_ids = clusters_df.member_ids.apply(str)
    logging.info(f"Now converting intra-cluster edge IDs to string representation...")
    clusters_df.intra_cluster_edge_ids = clusters_df.intra_cluster_edge_ids.apply(str)
    logging.info(f"After converting list values to string format, clusters DF is: \n{clusters_df}")

    # Save a table of cluster info
    logging.info(f"Dumping clusters DataFrame to sqlite..")
    clusters_df.to_sql("clusters", db_connection)
    db_connection.execute("CREATE UNIQUE INDEX cluster_id_index on clusters (cluster_id)")
    db_connection.commit()
    logging.info(f"Done saving data in sqlite")

    db_connection.close()

    return clusters_df


def write_graph_reports(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, clusters_df: pd.DataFrame):
    logging.info(f"Writing some reports about the graph's content..")

    logging.info(f"First creating counts of different cluster sizes..")
    cluster_size_counts_df = clusters_df.groupby("cluster_size").size().to_frame("num_clusters")
    logging.info(f"Cluster size counts DataFrame is: \n{cluster_size_counts_df}")
    cluster_size_counts_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_cluster_sizes.tsv", sep="\t")

    logging.info(f"Saving table of KG2pre nodes not recognized by SRI NN..")
    logging.info(f"First locating which nodes from KG2 were not recognized by the SRI..")
    kg2_nodes_not_in_sri_df = nodes_df[nodes_df.category_sri != nodes_df.category_sri]
    add_biolink_prefix_vectorized = np.vectorize(add_biolink_prefix)
    kg2_nodes_not_in_sri_df.category = add_biolink_prefix_vectorized(kg2_nodes_not_in_sri_df.category)
    build_node_ids = {"RTX:KG2", "RTX:KG2c"}
    kg2_nodes_not_in_sri_df = kg2_nodes_not_in_sri_df[~kg2_nodes_not_in_sri_df.id.isin(build_node_ids)]
    logging.info(f"DataFrame of KG2 nodes that are not recognized by the SRI is: \n{kg2_nodes_not_in_sri_df}")
    kg2_nodes_not_in_sri_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/kg2_nodes_not_in_sri_nn.tsv", sep="\t",
                                   columns=["id", "cluster_id", "category", "name"], index=False)

    logging.info(f"Now creating report on cluster size but for only non-sri nodes..")
    logging.info(f"Adding cluster size column to non-SRI nodes DataFrame...")
    kg2_nodes_not_in_sri_df = pd.merge(kg2_nodes_not_in_sri_df, clusters_df, on="cluster_id", how="left")
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
    oversized_clusters_df = clusters_df[clusters_df.cluster_size > 50].sort_values(by=["cluster_size"], ascending=False)
    logging.info(f"{oversized_clusters_df.shape[0]} clusters seem to be oversized: \n{oversized_clusters_df}")
    oversized_clusters_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/5_report_oversized_clusters.tsv", sep="\t", index=False,
                                 columns=["cluster_id", "cluster_size", "category", "name"])


def run():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    logging.info(f"Loading nodes and edges TSVs into DataFrames..")
    # Load the match graph into DataFrames
    nodes_df = load_final_nodes()
    edges_df = load_final_edges()

    # Create the final database that will be the backend of the NodeSynonymizer
    clusters_df = create_synonymizer_sqlite(nodes_df, edges_df)

    # Save some reports about the graph's content (meta-level)
    write_graph_reports(nodes_df, edges_df, clusters_df)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    run()


if __name__ == "__main__":
    main()
