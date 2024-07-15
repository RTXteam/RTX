import itertools
import logging
import os
import random
import string
import time
from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SCRIPT_DIR}/../"
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"
PREDICATE_WEIGHTS = {
    "same_as": 1.0,
    "close_match": 0.5,
    "has_similar_name": 0.1
}
BIO_RELATED_MAJOR_BRANCHES = {"BiologicalEntity", "GeneticOrMolecularBiologicalEntity", "DiseaseOrPhenotypicFeature",
                              "BiologicalProcessOrActivity", "OrganismalEntity"}
UNNECESSARY_CHARS_MAP = {ord(char): None for char in string.punctuation + string.whitespace}


def assign_edge_weights(edges_df: pd.DataFrame):
    # Assign weights to all match edges
    logging.info(f"Assigning edge weights...")
    edges_df["weight"] = edges_df.predicate.map(PREDICATE_WEIGHTS).astype(float)
    logging.info(f"Edges df with weights is now: \n{edges_df}")


def remove_self_edges(edges_df: pd.DataFrame):
    logging.info(f"Removing any self-edges (useless for us)..")
    return edges_df[edges_df.subject != edges_df.object]


def remove_close_match_edges(edges_df: pd.DataFrame):
    logging.info(f"Removing any close_match edges (don't work very well with label propagation clustering..)")
    return edges_df[edges_df.predicate != "close_match"]


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


def assign_major_category_branches(nodes_df: pd.DataFrame):
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

    # Assign each node its category branch
    logging.info(f"Assigning nodes to their major category branches..")
    nodes_df["major_branch"] = nodes_df.category.map(categories_to_major_branch)
    logging.info(f"After preliminary assignment, nodes DataFrame is: \n{nodes_df}")

    logging.info(f"For nodes whose major branch couldn't be determined, we'll consider their category "
                 f"(NamedThing or BiologicalEntity) to be their major branch..")
    # Note: NaN value is not equal to itself..
    nodes_df.major_branch = np.where(nodes_df.major_branch != nodes_df.major_branch, nodes_df.category, nodes_df.major_branch)

    logging.info(f"Nodes DataFrame after assigning major branches is: \n{nodes_df}")


def is_conflicting_category_edge_harsh(subject_id: str, object_id: str, upstream_resource_id: str, major_branch_map: Dict[str, any]) -> bool:
    """
    This is a harsh rule where nodes have to belong to exactly the same 'major branch'. This means
    that NamedThing nodes can only connect to NamedThing nodes, even though it could be valid for a NamedThing
    node to be in a cluster in which the other nodes belong to another major branch (since that must sort of be a subset
    of NamedThing). But it's difficult to fully eliminate paths between NamedThing nodes in a way that makes sense..
    so we'll go with this strict definition, at least to start.
    """
    if upstream_resource_id == "infores:sri-node-normalizer":
        # We don't get rid of conflicting category edges from the SRI; they can't lead to cluster merge errors, and
        #   we want to see them in the cluster graphs for debugging purposes
        return False
    else:
        return major_branch_map[subject_id] != major_branch_map[object_id]


def is_conflicting_category_edge_lenient(subject_id: str, object_id: str, major_branch_map: Dict[str, any]) -> bool:
    """
    Nodes have conflicting categories if their major branches aren't the same, with exceptions for NamedThing and
    BiologicalEntity. If a node has a major branch of NamedThing, it can be connected to any other node. If a node
    has a major branch of BiologicalEntity, it can be connected to NamedThing or any of our 'major branches' that are
    part of the BiologicalEntity branch ().
    """
    # TODO: This isn't entirely eliminating PATHS between nodes of different branches... better solution?
    major_branches = {major_branch_map[subject_id], major_branch_map[object_id]}
    if len(major_branches) == 1:
        return False
    elif "NamedThing" in major_branches:
        return False
    elif "BiologicalEntity" in major_branches and major_branches.issubset(BIO_RELATED_MAJOR_BRANCHES):
        return False
    else:
        return True


def remove_conflicting_category_edges(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> pd.DataFrame:
    # Remove every edge that links two nodes with conflicting major branches.
    logging.info(f"Creating helper map of node ID to major branch..")
    major_branch_map = dict(zip(nodes_df.index, nodes_df.major_branch))

    logging.info(f"Determining which edges have conflicting categories..")
    is_conflicting_category_edge_vectorized = np.vectorize(is_conflicting_category_edge_harsh, otypes=[bool])
    edges_df["is_conflicting_category_edge"] = is_conflicting_category_edge_vectorized(edges_df.subject, edges_df.object, edges_df.upstream_resource_id, major_branch_map)
    bad_edges_df = edges_df[edges_df.is_conflicting_category_edge]
    logging.info(f"Conflicting edges df is: \n{bad_edges_df}")
    bad_by_source_df = bad_edges_df.groupby(by="upstream_resource_id").size().to_frame("num_edges")
    logging.info(f"Bad edge counts grouped by source are: {bad_by_source_df}")
    logging.info(f"Saving the {bad_edges_df.shape[0]:,} conflicting category edges to TSV..")
    bad_edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_conflicting_category_edges.tsv", sep="\t")

    logging.info(f"Before filtering conflicting category edges, there are {edges_df.shape[0]:,} edges")
    logging.info(f"Filtering out conflicting category edges..")
    edges_df = edges_df[~edges_df.is_conflicting_category_edge]
    logging.info(f"After filtering conflicting category edges, there are {edges_df.shape[0]:,} edges")
    logging.info(f"Removing temporary conflicting edge column..")
    edges_df = edges_df.drop("is_conflicting_category_edge", axis=1)
    logging.info(f"Edges df is now: \n{edges_df}")

    return edges_df


def do_label_propagation(label_map: Dict[str, str], adj_list_weighted: Dict[str, Dict[str, float]],
                         nodes_to_label: Optional[List[str]] = None) -> Dict[str, str]:
    # Run label propagation, starting with whatever labels were provided
    node_ids = nodes_to_label if nodes_to_label else list(label_map.keys())
    logging.info(f"Starting label propagation; {len(node_ids)} nodes need labeling")
    iteration = 1
    done = False
    get_most_common_neighbor_label_vectorized = np.vectorize(get_most_common_neighbor_label, otypes=[str])
    while not done and iteration < 100:
        logging.info(f"Starting iteration {iteration} of label propagation..")
        # Put nodes into a new DF in a random order
        random.shuffle(node_ids)
        nodes_df_random = pd.DataFrame(node_ids, columns=["id"]).set_index("id")
        # Then update their current majority labels (changes to one node may impact others)
        logging.info(f"Updating current majority labels (updating label map as we go)..")
        nodes_df_random["current_label"] = get_most_common_neighbor_label_vectorized(nodes_df_random.index,
                                                                                     adj_list_weighted,
                                                                                     label_map,
                                                                                     update_label_map=True)
        # Then determine the majority label for each node, when considering the current labeling 'frozen'
        logging.info(f"Determining majority labels for nodes, considering current labeling to be 'frozen'..")
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
            if neighbor_label == neighbor_label:  # Means it's not NaN
                summed_label_weights[neighbor_label] += weight
            # TODO: How does this handle ties? Supposed to break ties in random fashion...
        most_common_label = max(summed_label_weights, key=summed_label_weights.get) if summed_label_weights else np.NaN
        if update_label_map:
            label_map[node_id] = most_common_label  # Important to update label_map itself...
        return most_common_label
    else:
        return label_map[node_id]  # Ensures orphan nodes always return something (their label will never change)


def create_name_sim_edges(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # Only create edges for what are close to exact matches for now
    logging.info(f"Starting to create name similarity edges..")

    logging.info(f"Excluding nodes without names..")
    nodes_with_names_df = nodes_df[nodes_df.name == nodes_df.name]
    logging.info(f"Nodes with names are: \n{nodes_with_names_df}")

    logging.info(f"Assigning nodes their simplified names...")
    nodes_with_names_df["name_simplified"] = nodes_with_names_df.name.apply(lambda name: name.lower().translate(UNNECESSARY_CHARS_MAP))
    logging.info(f"After adding simplified names, DataFrame is: \n{nodes_with_names_df}")

    logging.info(f"Filtering out nodes without any name matches..")
    nodes_with_name_matches_df = nodes_with_names_df[nodes_with_names_df.groupby(by="name_simplified").transform("size") > 1]
    logging.info(f"Nodes with name matches are: \n{nodes_with_name_matches_df}")

    logging.info(f"Grouping nodes by name matches..")
    nodes_grouped_df = nodes_with_name_matches_df.groupby(by="name_simplified")

    logging.info(f"Looping through groups and creating name sim edges..")
    edge_rows = []
    group_size_limit = 500
    for simplified_name, node_group_df in nodes_grouped_df:
        if node_group_df.size <= group_size_limit:
            node_ids = node_group_df.index.values
            node_pairs = itertools.combinations(node_ids, 2)
            group_edge_rows = [(f"NAMESIM:{'--'.join(node_pair)}", node_pair[0], "has_similar_name", node_pair[1], "infores:arax-node-synonymizer", None)
                               for node_pair in node_pairs]
            edge_rows += group_edge_rows
        else:
            # TODO: Maybe rather than skipping all, create name sime edges only for orphans? or nodes with few edges?
            logging.warning(f"{node_group_df.size} nodes have the same simplified name: {simplified_name}. Not creating name sim edges for these (too many).")

    logging.info(f"Tacking name sim edges onto existing edges DataFrame..")
    name_sim_edges_df = pd.DataFrame(edge_rows,
                                     columns=["id", "subject", "predicate", "object", "upstream_resource_id", "primary_knowledge_source"]).set_index("id")
    logging.info(f"Created a total of {name_sim_edges_df.shape[0]:,} name sim edges")
    edges_df = pd.concat([edges_df, name_sim_edges_df])
    logging.info(f"Edges DataFrame is now: \n{edges_df}")

    return edges_df


def cluster_match_graph(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # Do label propagation, where each node starts with its own ID as its label
    # TODO: Switch to modularity-based clustering, rather than label propagation..
    logging.info(f"Starting to cluster the match graph into groups of equivalent nodes...")

    logging.info(f"Determining which nodes need labeling..")
    # Note: A NaN value is not equal to itself
    non_sri_nodes_df = nodes_df[nodes_df.cluster_id != nodes_df.cluster_id]
    non_sri_node_ids = list(non_sri_nodes_df.index.values)
    logging.info(f"Nodes missing cluster ID (non-SRI nodes) are: \n{non_sri_nodes_df}")

    adj_list_weighted = get_weighted_adjacency_dict(edges_df)

    # First do label propagation without assigning node IDs as initial labels (this allows SRI cluster IDs
    # to be propagated as far as possible, rather than a KG2 node ID becoming a cluster ID and dominating, thus
    # preventing a small SRI cluster from being merged with the larger KG2 cluster
    logging.info(f"Starting run 1 of label propagation (using NaN as default starting labels)..")
    logging.info(f"Zipping node IDs with cluster IDs and converting to dictionary format..")
    label_map_initial_1 = dict(zip(nodes_df.index, nodes_df.cluster_id))
    label_map_1 = do_label_propagation(label_map_initial_1, adj_list_weighted,
                                       nodes_to_label=non_sri_node_ids)
    logging.info(f"Updating the nodes DataFrame with the cluster IDs determined by first label propagation run..")
    nodes_df.cluster_id = nodes_df.index.map(label_map_1)

    # Then do another run of label propagation where we use node IDs as initial labels (this allows nodes that are only
    # weakly clustered in an SRI cluster to be won over by a dominating KG2 cluster), and also to allow clustering of
    # nodes that are not connected at all to SRI nodes
    logging.info(f"Starting run 2 of label propagation (using node IDs as default starting labels)..")
    logging.info(f"Assigning node IDs as cluster labels for nodes that don't yet have one..")
    nodes_df.fillna(value={"cluster_id": nodes_df.index.to_series()}, inplace=True)
    logging.info(f"Nodes DataFrame after assigning initial cluster IDs is: \n{nodes_df}")
    logging.info(f"Zipping node IDs with cluster IDs and converting to dictionary format..")
    label_map_initial_2 = dict(zip(nodes_df.index, nodes_df.cluster_id))
    label_map_2 = do_label_propagation(label_map_initial_2, adj_list_weighted,
                                       nodes_to_label=non_sri_node_ids)
    logging.info(f"Updating the nodes DataFrame with the cluster IDs determined by second label propagation run..")
    nodes_df.cluster_id = nodes_df.index.map(label_map_2)

    logging.info(f"The final nodes DataFrame is: \n{nodes_df}")

    cluster_ids = set(nodes_df.cluster_id.values)
    logging.info(f"There are a total of {len(cluster_ids):,} different clusters "
                 f"(for a total of {len(nodes_df):,} nodes)")


def verify_clustering_output(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    # Make sure every node has a cluster ID filled out
    logging.info(f"Verifying every node has a cluster ID...")
    nodes_missing_cluster_id = list(nodes_df[nodes_df.cluster_id != nodes_df.cluster_id].index.values)  # NaN value is not equal to itself
    if nodes_missing_cluster_id:
        raise ValueError(f"{len(nodes_missing_cluster_id)} nodes are missing a cluster ID, even though "
                         f"clustering is finished: {nodes_missing_cluster_id}")

    # Make sure every node has a category (i.e., either SRI or KG2pre category..)
    logging.info(f"Verifying every node has a category...")
    nodes_missing_category = list(nodes_df[nodes_df.category != nodes_df.category].index.values)  # NaN value is not equal to itself
    if nodes_missing_category:
        raise ValueError(f"{len(nodes_missing_category)} nodes are missing a category "
                         f"(i.e., no SRI or KG2pre category).")

    # Make sure every node has a major branch
    logging.info(f"Verifying every node has a major_branch...")
    nodes_missing_major_branch = list(nodes_df[nodes_df.major_branch != nodes_df.major_branch].index.values)  # NaN value is not equal to itself
    if nodes_missing_major_branch:
        raise ValueError(f"{len(nodes_missing_major_branch)} nodes are missing a major branch assignment: "
                         f"{nodes_missing_major_branch}")


def load_merged_nodes() -> pd.DataFrame:
    logging.info(f"Loading merged match nodes into a Pandas DataFrame..")
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
    # TODO: May be faster to do this with df.duplicated()? Though this only takes like 40 seconds on full graph..
    unique_node_ids = set(nodes_df.index.values)
    all_rows_unique = sorted(list(unique_node_ids)) == sorted(list(nodes_df.index.values))
    if all_rows_unique:
        logging.info(f"Verified all node rows are unique")
    else:
        raise ValueError(f"merged_match_nodes.tsv contains duplicate rows!")

    # Choose a single name and category for each node
    logging.info(f"Assigning each node one category (favor SRI over KG2pre)..")
    # TODO: If SRI category is NamedThing and KG2pre one isn't, should we use KG2pre?
    # Note: If a category dtype is equal to itself, that means it must not be NaN..
    nodes_df["category"] = np.where(nodes_df.category_sri == nodes_df.category_sri, nodes_df.category_sri, nodes_df.category_kg2pre)
    logging.info(f"Assigning each node one name (favor SRI over KG2pre)..")
    nodes_df["name"] = np.where(nodes_df.name_sri == nodes_df.name_sri, nodes_df.name_sri, nodes_df.name_kg2pre)

    return nodes_df


def load_merged_edges() -> pd.DataFrame:
    logging.info(f"Loading merged match edges into a Pandas DataFrame..")
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


def run():
    logging.info(f"\n\n  ------------------- STARTING TO RUN SCRIPT {os.path.basename(__file__)} ------------------- \n")

    # Load match graph data
    nodes_df = load_merged_nodes()
    edges_df = load_merged_edges()

    # Do edge pre-processing
    edges_df = remove_self_edges(edges_df)
    edges_df = remove_close_match_edges(edges_df)
    edges_df = create_name_sim_edges(nodes_df, edges_df)
    assign_edge_weights(edges_df)

    # Remove edges between nodes with conflicting categories
    assign_major_category_branches(nodes_df)
    edges_df = remove_conflicting_category_edges(nodes_df, edges_df)

    # Cluster the graph into sets of equivalent nodes
    cluster_match_graph(nodes_df, edges_df)

    # Run some checks to make sure the output looks reasonable
    verify_clustering_output(nodes_df, edges_df)

    # Save our final nodes/edges tables, plus a simple TSV with the cluster labeling (for easy access)
    logging.info(f"Saving final nodes and edges tables..")
    nodes_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_match_nodes_preprocessed.tsv", sep="\t")
    edges_df.to_csv(f"{SYNONYMIZER_BUILD_DIR}/4_match_edges_preprocessed.tsv", sep="\t")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    run()


if __name__ == "__main__":
    main()
