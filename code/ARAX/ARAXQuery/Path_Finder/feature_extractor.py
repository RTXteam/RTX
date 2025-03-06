import numpy as np


def get_neighbors_info(curie, ngd_repo, plover_repo):
    curie_ngd_list = ngd_repo.get_curie_ngd(curie)
    neighbors, edges = plover_repo.get_neighbors_with_edges(curie)
    if neighbors:
        neighbors_id = [curie for curie, _ in neighbors.items()]
        node_pmids_length = ngd_repo.get_curies_pmid_length(neighbors_id)
        content_by_curie = {item: {'pmids': 0, 'ngd': None, 'category': None, 'edges': {}} for item in neighbors_id}
        for curie, num_of_pmids in node_pmids_length:
            content_by_curie[curie]['pmids'] = num_of_pmids
        for ngd in curie_ngd_list:
            content_by_curie[ngd[0]]['ngd'] = ngd[1]
        for node, category in neighbors.items():
            content_by_curie[node]['category'] = category
        if edges:
            for node, categories in edges.items():
                for category, _ in categories:
                    if category not in content_by_curie[node]['edges']:
                        content_by_curie[node]['edges'][category] = 1
                    else:
                        content_by_curie[node]['edges'][category] = content_by_curie[node]['edges'][category] + 1

        return content_by_curie
    return None


def get_np_array_features(value, category_to_idx, edge_category_to_idx):
    ngd_val = float(value["ngd"]) if value["ngd"] is not None else np.nan
    pmid_val = float(value["pmids"])
    cat_onehot = np.zeros(58, dtype=float)
    cat_str = value["category"].split(":")[-1]
    if cat_str:
        cat_idx = category_to_idx[cat_str]
        cat_onehot[cat_idx] = 1.0

    edge_categories = np.zeros(len(edge_category_to_idx), dtype=float)
    for category, count in value['edges'].items():
        if category:
            edge_cat_idx = edge_category_to_idx[category]
            edge_categories[edge_cat_idx] = count

    return np.concatenate([[ngd_val, pmid_val], cat_onehot, edge_categories])
