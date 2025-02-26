import sys
import os

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model.Node import Node


def get_neighbors_info(curie, node_synonymizer, ngd_repo, plover_repo):
    curie_ngd_list = ngd_repo.get_curie_ngd(curie)
    neighbors = plover_repo.get_neighbors(Node(id=curie))
    neighbors_id = [curie.id for curie in neighbors]
    node_pmids_length = ngd_repo.get_curies_pmid_length(neighbors_id)
    category_by_curie = node_synonymizer.get_curie_category(neighbors_id)
    content_by_curie = {item: {'pmids': 0, 'ngd': None, 'category': None} for item in neighbors_id}
    for curie, num_of_pmids in node_pmids_length:
        content_by_curie[curie]['pmids'] = num_of_pmids
    for ngd in curie_ngd_list:
        content_by_curie[ngd[0]]['ngd'] = ngd[1]
    for node, category in category_by_curie.items():
        content_by_curie[node]['category'] = category

    return content_by_curie


def get_np_array_features(value, category_to_idx):
    ngd_val = float(value["ngd"]) if value["ngd"] is not None else np.nan
    pmid_val = float(value["pmids"])
    cat_onehot = np.zeros(58, dtype=float)
    cat_str = value["category"]
    if cat_str:
        cat_idx = category_to_idx[cat_str]
        cat_onehot[cat_idx] = 1.0

    return np.concatenate([[ngd_val, pmid_val], cat_onehot])