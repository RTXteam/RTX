import argparse
import ast
import json
import logging
import os
import pathlib
import sqlite3
import subprocess
from typing import Optional, Tuple, List

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])


def get_cluster_id(node_id: str, cursor) -> Optional[str]:
    answer = cursor.execute(f"SELECT cluster_id FROM nodes WHERE id = '{node_id}'")
    matching_row = answer.fetchone()
    if matching_row:
        cluster_id = matching_row[0]
        logging.debug(f"Cluster ID for {node_id} is {cluster_id}")
    else:
        logging.warning(f"No node with id '{node_id}' exists in the match graph")
        cluster_id = None
    return cluster_id


def get_member_ids(cluster_id: str, cursor) -> Tuple[List[str], List[str]]:
    answer = cursor.execute(f"SELECT member_ids, intra_cluster_edge_ids FROM clusters WHERE cluster_id = '{cluster_id}'")
    matching_row = answer.fetchone()
    if matching_row:
        member_ids = ast.literal_eval(matching_row[0])  # Lists are stored as strings in sqlite
        intra_cluster_edge_ids_str = "[]" if matching_row[1] == "nan" else matching_row[1]
        intra_cluster_edge_ids = ast.literal_eval(intra_cluster_edge_ids_str)  # Lists are stored as strings in sqlite
        logging.debug(f"Cluster {cluster_id} has member IDs {member_ids} and "
                      f"intra cluster edge IDs {intra_cluster_edge_ids}")
    else:
        logging.error(f"There is no cluster with ID {cluster_id}")
        member_ids, intra_cluster_edge_ids = [], []
    return member_ids, intra_cluster_edge_ids


def _load_records_into_dict(item_ids: List[str], table_name: str, cursor) -> List[dict]:
    ids_as_str = ", ".join([f"'{item_id}'" for item_id in item_ids])
    answer = cursor.execute(f"SELECT * FROM {table_name} WHERE id IN ({ids_as_str})")
    matching_rows = answer.fetchall()
    if matching_rows:
        column_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_names = [column_info[1] for column_info in column_info]
        matching_items_df = pd.DataFrame(matching_rows, columns=column_names)
        items_as_dicts = matching_items_df.to_dict(orient="records")
        return items_as_dicts
    else:
        return []


def get_graph(node_ids: List[str], edge_ids: List[str], cursor, hide_predicate: bool = False) -> dict:
    nodes_list = _load_records_into_dict(node_ids, "nodes", cursor)
    edges_list = _load_records_into_dict(edge_ids, "edges", cursor)

    cluster_graph = {"nodes": nodes_list, "edges": edges_list}
    if hide_predicate and "predicate" in cluster_graph["edges"][0]:
        for edge in cluster_graph["edges"]:
            edge["predicate_hidden"] = edge["predicate"]
            del edge["predicate"]

    # Choose one name (SRI or KG2) for each node
    for node in cluster_graph["nodes"]:
        node["name"] = node["name_sri"] if node.get("name_sri") else node["name_kg2pre"]

    logging.info(f"Cluster graph has {len(cluster_graph['nodes'])} nodes, {len(cluster_graph['edges'])} edges.")
    return cluster_graph


def compute_cluster_density(cluster_graph: any) -> float:
    num_nodes = len(cluster_graph["nodes"])
    total_possible_edges = (num_nodes * (num_nodes - 1)) / 2
    weighted_edge_count = sum([edge.get("weight", 1) for edge in cluster_graph["edges"]])
    if total_possible_edges:
        density = weighted_edge_count / total_possible_edges
    else:
        density = 1.0
    # TODO: Account for fact that we have a multigraph...
    return density


def convert_to_check_mark(some_bool: bool) -> str:
    return "X" if some_bool else ""


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("node_id")
    arg_parser.add_argument('--full', dest='full', action='store_true')
    args = arg_parser.parse_args()

    sqlite_path = f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite"
    cluster_graphs_path = f"{SYNONYMIZER_BUILD_DIR}/cluster_debug_graphs"
    if not pathlib.Path(cluster_graphs_path).exists():
        os.system(f"mkdir {cluster_graphs_path}")
    db_connection = sqlite3.connect(sqlite_path)
    cursor = db_connection.cursor()

    cluster_id = get_cluster_id(args.node_id, cursor)
    member_node_ids, intra_cluster_edge_ids = get_member_ids(cluster_id, cursor)
    cluster_graph = get_graph(member_node_ids, intra_cluster_edge_ids, cursor)
    cluster_rep = next(node for node in cluster_graph["nodes"] if node["id"] == cluster_id)

    # Print out the cluster edges in tabular format
    if args.full:
        column_names = ["id", "subject", "predicate", "object", "upstream_resource_id", "primary_knowledge_source", "weight"]
        cluster_edge_rows = [[edge["id"], edge["subject"], edge["predicate"], edge["object"],
                              edge["upstream_resource_id"],
                              edge["primary_knowledge_source"] if edge["primary_knowledge_source"] else "",
                              edge["weight"]]
                             for edge in cluster_graph["edges"]]
    else:
        column_names = ["subject", "predicate", "object", "upstream_resource_id", "primary_knowledge_source"]
        cluster_edge_rows = [[edge["subject"], edge["predicate"], edge["object"],
                              edge["upstream_resource_id"],
                              edge["primary_knowledge_source"] if edge["primary_knowledge_source"] else ""]
                             for edge in cluster_graph["edges"]]
    cluster_edges_df = pd.DataFrame(cluster_edge_rows, columns=column_names).sort_values(by="upstream_resource_id")
    print(f"\nCluster for {args.node_id} ({cluster_id}) has {cluster_edges_df.shape[0]} edges:")
    print(f"\n{cluster_edges_df.to_markdown(index=False)}\n")

    # Print out the cluster nodes in tabular format
    if args.full:
        column_names = ["id", "category", "major_branch", "name",
                        "in_SRI", "category_sri", "name_sri",
                        "in_KG2pre", "category_kg2pre", "name_kg2pre",
                        "is_cluster_rep"]
        cluster_node_rows = [[node["id"], node["category"], node["major_branch"], node["name"],
                              convert_to_check_mark(node["category_sri"] is not None),
                              node["category_sri"], node["name_sri"],
                              convert_to_check_mark(node["category_kg2pre"] is not None),
                              node["category_kg2pre"], node["name_kg2pre"],
                              convert_to_check_mark(node["id"] == cluster_id)]
                             for node in cluster_graph["nodes"]]
    else:
        column_names = ["id", "category", "name", "in_SRI", "in_KG2pre", "is_cluster_rep"]
        cluster_node_rows = [[node["id"], node["category"], node["name"],
                              convert_to_check_mark(node["category_sri"] is not None),
                              convert_to_check_mark(node["category_kg2pre"] is not None),
                              convert_to_check_mark(node["id"] == cluster_id)]
                             for node in cluster_graph["nodes"]]
    cluster_nodes_df = pd.DataFrame(cluster_node_rows, columns=column_names).sort_values(by="id")
    cluster_id_str = f" ({cluster_id})" if args.node_id != cluster_id else ""
    print(f"\nCluster for {args.node_id}{cluster_id_str} has {cluster_nodes_df.shape[0]} nodes:")
    print(f"\n{cluster_nodes_df.to_markdown(index=False)}\n")

    # Compute the density of this cluster
    density = compute_cluster_density(cluster_graph)
    print(f"With {len(cluster_graph['nodes'])} nodes and {len(cluster_graph['edges'])} edges, "
          f"density of cluster is: {density}\n")

    # Save the cluster graph in a JSON file
    cluster_file_path = f"{cluster_graphs_path}/{cluster_rep['name']}_{cluster_id}.json"
    with open(cluster_file_path, "w+") as cluster_file:
        json.dump(cluster_graph, cluster_file, indent=2)
    print(f"Cluster saved in Biolink format to: {cluster_file_path}\n")

    cursor.close()
    db_connection.close()


if __name__ == "__main__":
    main()
