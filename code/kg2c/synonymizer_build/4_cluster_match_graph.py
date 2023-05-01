import logging
import os
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler()])
PREDICATE_WEIGHTS = {
    "same_as": 1.0,
    "close_match": 0.5,
    "has_name_similarity": 0.2
}


def assign_edge_weights(edges_df: pd.DataFrame):
    # Assign weights to all match edges
    logging.info(f"Assigning edge weights...")
    edges_df["weight"] = edges_df.predicate.map(PREDICATE_WEIGHTS).astype(float)
    logging.info(f"Edges df with weights is now: \n{edges_df}")


def get_weighted_adjacency_dict(edges_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    logging.info(f"Creating weighted adjacency dict from edges data frame...")
    start = time.time()

    edges_df_ordered_pairs = edges_df.loc[:, ["weight"]]
    logging.info(f"First creating a new DataFrame with ordered node pairs..")
    edges_df_ordered_pairs["nodea"] = np.where(edges_df.subject < edges_df.object, edges_df.subject, edges_df.object)
    edges_df_ordered_pairs["nodeb"] = np.where(edges_df.subject < edges_df.object, edges_df.object, edges_df.subject)

    logging.info(f"Now grouping by node pair and summing weights..")
    grouped_df = edges_df_ordered_pairs.groupby(by=["nodea", "nodeb"]).sum()

    logging.info(f"Now converting the grouped node pair sums into nested adj dict format..")
    adj_list_weighted = defaultdict(lambda: defaultdict(float))
    add_node_pair_to_adj_list_vectorized = np.vectorize(add_node_pair_to_adj_list)
    add_node_pair_to_adj_list_vectorized(grouped_df.index.values, grouped_df.weight, adj_list_weighted)

    stop = time.time()
    logging.info(f"Creating weighted adjacency dict took {round(stop - start, 2)} seconds")

    return adj_list_weighted


def add_node_pair_to_adj_list(node_pair_tuple, summed_weight, adj_list_weighted: Dict[str, Dict[str, float]]):
    node_a = node_pair_tuple[0]
    node_b = node_pair_tuple[1]
    adj_list_weighted[node_a][node_b] = summed_weight
    adj_list_weighted[node_b][node_a] = summed_weight


def assign_major_category_branches(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    """
    We want to know which 'major branch' of the Biolink category tree each node belongs to, where a 'major branch'
    is a node at depth 1 in the category tree, with the exception of the BiologicalEntity branch: within that branch,
    the 'major branch' is considered the depth-2 ancestor. Plus, we modify the BiologicalEntity branch so that all
    gene- and protein-related categories are moved under a (made up) depth-2 ancestor called
    'GeneticOrMolecularBiologicalEntity'. See https://tree-viz-biolink.herokuapp.com/categories/er.
    So for our representation, nodes with a category of NamedThing or BiologicalEntity are effectively category-less
    nodes, because they don't fit into one of our 'major branches'. We need to assign them to a major branch,
    which we do using label propagation.
    """
    # Grab the map of categories --> major branches
    logging.info(f"Grabbing major branch info from tree-viz-biolink..")
    res = requests.get("https://tree-viz-biolink.herokuapp.com/major_branches/er/3.0.3")
    categories_to_major_branch = res.json()["category_to_major_branch"]

    # Assign each node its (modified) category branch - or None if it's a NamedThing/BiologicalEntity
    logging.info(f"Choosing between KG2pre and SRI categories (favor SRI over KG2pre)..")
    # TODO: If SRI category is NamedThing and KG2pre one isn't, use KG2pre?
    # Note: If a category dtype is equal to itself, that means it must not be NaN..
    nodes_df["category"] = np.where(nodes_df.category_sri == nodes_df.category_sri, nodes_df.category_sri, nodes_df.category_kg2pre)

    logging.info(f"Assigning nodes to their major category branches..")
    nodes_df["major_branch"] = nodes_df.category.map(categories_to_major_branch).astype("category")

    logging.info(f"Doing label propagation of major branches to NamedThing/BiologicalEntity nodes")
    adj_dict_weighted = get_weighted_adjacency_dict(edges_df)
    branch_label_map_partial = dict(zip(nodes_df.index, nodes_df.major_branch))
    nodes_missing_major_branch = [node_id for node_id, label in branch_label_map_partial.items() if not label]
    label_map = do_label_propagation(branch_label_map_partial, adj_dict_weighted, nodes_to_label=nodes_missing_major_branch)

    # Assign all nodes their new major branch (orphans will always remain unlabeled)
    nodes_df.major_branch = nodes_df.index.map(label_map).astype("category")


def remove_conflicting_category_edges(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> pd.DataFrame:
    # Remove every edge that links two nodes from different major category branches
    logging.info(f"Creating helper map of node ID to major branch..")
    major_branch_map = dict(zip(nodes_df.index, nodes_df.major_branch))

    logging.info(f"Determining which edges have conflicting categories..")
    bad_edges_df = edges_df[edges_df.apply(lambda row: major_branch_map.get(row.subject) != major_branch_map.get(row.object),
                                           axis=1)]
    logging.info(f"Saving the {bad_edges_df.shape[0]:,} conflicting category edges to TSV..")
    bad_edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_conflicting_category_edges.tsv")

    logging.info(f"Before filtering conflicting category edges, there are {edges_df.shape[0]:,} edges")
    logging.info(f"Filtering out conflicting category edges..")
    edges_df = edges_df[edges_df.apply(lambda row: major_branch_map.get(row.subject) == major_branch_map.get(row.object),
                                       axis=1)]
    logging.info(f"After filtering conflicting category edges, there are {edges_df.shape[0]:,} edges")

    # TODO: This isn't entirely eliminating paths between nodes of different branches... alternate solution?

    return edges_df


def do_label_propagation(label_map: Dict[str, str], adj_list_weighted: Dict[str, Dict[str, float]],
                         nodes_to_label: Optional[List[str]] = None) -> Dict[str, str]:
    # Run label propagation, starting with whatever labels were provided
    node_ids = nodes_to_label if nodes_to_label else list(label_map.keys())
    logging.info(f"Starting label propagation; {len(node_ids)} nodes need labeling")
    iteration = 1
    done = False
    while not done and iteration < 100:
        logging.info(f"Starting iteration {iteration} of label propagation..")
        # Put nodes into a new DF in a random order
        random.shuffle(node_ids)
        nodes_df_random = pd.DataFrame(node_ids, columns=["id"]).set_index("id")
        # Then update their current majority labels (changes to one node may impact others)
        get_most_common_neighbor_label_vectorized = np.vectorize(get_most_common_neighbor_label)
        nodes_df_random["current_label"] = get_most_common_neighbor_label_vectorized(nodes_df_random.index,
                                                                                     adj_list_weighted,
                                                                                     label_map,
                                                                                     update_label_map=True)
        # Then determine the majority label for each node, when considering the current labeling 'frozen'
        nodes_df_random["major_label"] = get_most_common_neighbor_label_vectorized(nodes_df_random.index,
                                                                                   adj_list_weighted,
                                                                                   label_map,
                                                                                   update_label_map=False)
        logging.info(f"After iteration {iteration}, nodes_df_random is: \n{nodes_df_random}")
        # Stop if all nodes have the label most prevalent among their neighbors
        if nodes_df_random["current_label"].equals(nodes_df_random["major_label"]):
            done = True
            logging.info(f"Label propagation reached convergence (in {iteration} iterations)")
        else:
            iteration += 1

    if not done:
        logging.info(f"Label propagation reached iteration limit ({iteration} iterations); unable to converge")
    return label_map


def get_most_common_neighbor_label(node_id: str, adj_list_weighted: dict, label_map: Dict[str, any], update_label_map: bool) -> any:
    weighted_neighbors = adj_list_weighted.get(node_id)
    if weighted_neighbors:
        summed_label_weights = defaultdict(float)
        for neighbor_id, weight in weighted_neighbors.items():
            neighbor_label = label_map[neighbor_id]
            summed_label_weights[neighbor_label] += weight
        # TODO: How does this handle ties? Supposed to break ties in random fashion...
        most_common_label = max(summed_label_weights, key=summed_label_weights.get)
        if update_label_map:
            label_map[node_id] = most_common_label  # Important to update label_map itself...
        return most_common_label
    else:
        return label_map[node_id]  # Ensures orphan nodes always return something (their label will never change)


def create_name_sim_edges(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # TODO: Create name similarity edges; use blocking to avoid n^2 situation (do in a second iteration)
    pass


def cluster_match_graph(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # TODO: Switch to modularity-based clustering, rather than label propagation..

    # Do label propagation, where each node starts with its own ID as its label
    logging.info(f"Starting to cluster the match graph into groups of equivalent nodes...")

    logging.info(f"Determining initial cluster labels and which nodes need labeling..")
    node_ids_missing_cluster_id = list(nodes_df[nodes_df.cluster_id != nodes_df.cluster_id].index.values)  # NaN value is not equal to itself
    initial_labels = np.where(nodes_df.cluster_id == nodes_df.cluster_id, nodes_df.cluster_id, nodes_df.index)
    label_map_initial = dict(zip(nodes_df.index, initial_labels))

    adj_list_weighted = get_weighted_adjacency_dict(edges_df)

    label_map = do_label_propagation(label_map_initial, adj_list_weighted, nodes_to_label=node_ids_missing_cluster_id)

    cluster_ids = set(nodes_df.cluster_id.values)
    logging.info(f"After clustering equivalent nodes, there are a total of {len(cluster_ids):,} clusters "
                 f"(for a total of {len(nodes_df):,} nodes)")

    logging.info(f"Updating the nodes DataFrame with the final cluster IDs..")
    nodes_df.cluster_id = nodes_df.index.map(label_map)


def verify_clustering_output(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # Make sure every node has a cluster ID filled out (note: a NaN value is not equal to itself)
    logging.info(f"Verifying every node has a cluster ID...")
    nodes_missing_cluster_id = list(nodes_df[nodes_df.cluster_id != nodes_df.cluster_id].index.values)
    if nodes_missing_cluster_id:
        raise ValueError(f"{len(nodes_missing_cluster_id)} nodes are missing a cluster ID, even though "
                         f"clustering is finished: {nodes_missing_cluster_id}")

    # Make sure every node has a category (i.e., either SRI or KG2pre category..)
    logging.info(f"Verifying every node has a category...")
    nodes_missing_category = list(nodes_df[nodes_df.category != nodes_df.category].index.values)
    if nodes_missing_category:
        raise ValueError(f"{len(nodes_missing_category)} nodes are missing a category "
                         f"(i.e., no SRI or KG2pre category): {nodes_missing_category}")


def load_merged_nodes() -> pd.DataFrame:
    logging.info(f"Loading match_nodes.tsv into a Pandas DataFrame..")
    nodes_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/3_merged_match_nodes.tsv",
                             index_col="id",
                             dtype={
                                 "id": str,
                                 "cluster_id": str,
                                 "category_kg2pre": "category",
                                 "name_kg2pre": str,
                                 "category_sri": "category",
                                 "name_sri": str,
                             })
    logging.info(f"Nodes DataFrame:\n {nodes_df}")
    # Make sure there's only one row per node (no duplicates)
    unique_node_ids = set(nodes_df.index.values)
    all_rows_unique = sorted(list(unique_node_ids)) == sorted(list(nodes_df.index.values))
    if all_rows_unique:
        logging.info(f"Verified all node rows are unique")
    else:
        raise ValueError(f"merged_match_nodes.tsv contains duplicate rows!")

    return nodes_df


def load_merged_edges() -> pd.DataFrame:
    logging.info(f"Loading match_edges.tsv into a Pandas DataFrame..")
    edges_df = pd.read_table(f"{SYNONYMIZER_BUILD_DIR}/3_merged_match_edges.tsv",
                             index_col="id",
                             dtype={
                                 "id": str,
                                 "subject": str,
                                 "predicate": "category",
                                 "object": str,
                                 "upstream_resource_id": "category",
                                 "primary_knowledge_source": "category"
                             })
    logging.info(f"Edges DataFrame:\n {edges_df}")
    return edges_df


def main():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Load match graph data
    nodes_df = load_merged_nodes()
    edges_df = load_merged_edges()

    # Do edge pre-processing
    assign_edge_weights(edges_df)
    create_name_sim_edges(nodes_df, edges_df)

    # Attempt to remove paths between nodes with conflicting categories
    assign_major_category_branches(nodes_df, edges_df)
    edges_df = remove_conflicting_category_edges(nodes_df, edges_df)

    # Cluster the graph into sets of equivalent nodes
    cluster_match_graph(nodes_df, edges_df)

    # Run some checks to make sure the output looks reasonable
    verify_clustering_output(nodes_df, edges_df)

    # Save our final nodes/edges tables, plus a simple TSV with the cluster labeling (for easy access)
    logging.info(f"Saving final nodes and edges tables..")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_match_nodes_preprocessed.tsv", sep="\t")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_match_edges_preprocessed.tsv", sep="\t")
    logging.info(f"Saving member_id --> cluster_id map to TSV file..")
    cluster_map_df = nodes_df[["cluster_id"]]
    cluster_map_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_cluster_member_map.tsv", sep="\t")


if __name__ == "__main__":
    main()
