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
    answer = cursor.execute(f"SELECT * FROM clusters WHERE cluster_id = '{cluster_id}'")
    matching_row = answer.fetchone()
    if matching_row:
        member_ids = ast.literal_eval(matching_row[1])  # Lists are stored as strings in sqlite
        intra_cluster_edge_ids = ast.literal_eval(matching_row[2])  # Lists are stored as strings in sqlite
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


def get_node_name(node: any) -> Optional[str]:
    if node.get("name"):
        return node["name"]
    elif node.get("name_sri"):
        return node["name_sri"]
    else:
        return node.get("name_kg2pre")


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


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("node_id")
    args = arg_parser.parse_args()

    sqlite_path = f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite"
    cluster_graphs_path = f"{SYNONYMIZER_BUILD_DIR}/cluster_debug_graphs"
    if not pathlib.Path(cluster_graphs_path).exists():
        subprocess.check_call(["mkdir", cluster_graphs_path])
    db_connection = sqlite3.connect(sqlite_path)
    cursor = db_connection.cursor()

    cluster_id = get_cluster_id(args.node_id, cursor)
    member_node_ids, intra_cluster_edge_ids = get_member_ids(cluster_id, cursor)
    cluster_graph = get_graph(member_node_ids, intra_cluster_edge_ids, cursor)

    # Save the cluster graph in a JSON file
    cluster_rep = next(node for node in cluster_graph["nodes"] if node["id"] == cluster_id)
    cluster_file_path = f"{cluster_graphs_path}/{get_node_name(cluster_rep)}_{cluster_id}.json"
    with open(cluster_file_path, "w+") as cluster_file:
        json.dump(cluster_graph, cluster_file, indent=2)
    logging.info(f"Cluster saved in Biolink format to: {cluster_file_path}")

    density = compute_cluster_density(cluster_graph)
    logging.info(f"Density of cluster {cluster_id} is {density}")

    cursor.close()
    db_connection.close()


if __name__ == "__main__":
    main()
