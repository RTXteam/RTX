import numpy as np


def get_neighbors_info(curie, ngd_repo, plover_repo, degree_repo):
    curie_ngd_list = ngd_repo.get_curie_ngd(curie)
    curie_category, neighbors, edges = plover_repo.get_neighbors_with_edges(curie)
    if neighbors:
        neighbors_id = [curie for curie, _ in neighbors.items()]
        degrees_by_node = degree_repo.get_degrees_by_node(neighbors_id)
        node_pmids_length = ngd_repo.get_curies_pmid_length(neighbors_id)
        content_by_curie = {item: {'pmids': 0, 'ngd': None, 'category': None, 'edges': {}} for item in neighbors_id}
        for curie_, degree_by_category in degrees_by_node.items():
            content_by_curie[curie_]['degree_by_category'] = degree_by_category
        for curie_, num_of_pmids in node_pmids_length:
            content_by_curie[curie_]['pmids'] = num_of_pmids
        for ngd in curie_ngd_list:
            if ngd[0] in content_by_curie:
                content_by_curie[ngd[0]]['ngd'] = ngd[1]
        for node_id, value in neighbors.items():
            content_by_curie[node_id]['name'] = value['name']
            content_by_curie[node_id]['category'] = value['category']
        if edges:
            for node, categories in edges.items():
                for category, _ in categories:
                    if category not in content_by_curie[node]['edges']:
                        content_by_curie[node]['edges'][category] = 1
                    else:
                        content_by_curie[node]['edges'][category] = content_by_curie[node]['edges'][category] + 1

        return content_by_curie, curie_category
    return None, None


def get_np_array_features(
        value,
        category_to_idx,
        edge_category_to_idx,
        curie_category_onehot,
        ancestors_by_indices,
        degree_category_to_idx
):
    ngd_val = float(value["ngd"]) if value["ngd"] is not None else np.nan
    pmid_val = float(value["pmids"])
    cat_onehot = get_category(value["category"].split(":")[-1], category_to_idx)

    edge_categories = np.zeros(len(edge_category_to_idx), dtype=float)
    for category, count in value['edges'].items():
        if category:
            if category in edge_category_to_idx:
                edge_cat_idx = edge_category_to_idx[category]
                for ancestor in ancestors_by_indices[edge_cat_idx]:
                    edge_categories[ancestor] = 1

    node_degrees_feature = np.zeros(len(degree_category_to_idx), dtype=float)
    for category, count in value['degree_by_category'].items():
        if category in degree_category_to_idx:
            category_index = degree_category_to_idx[category]
            node_degrees_feature[category_index] = count

    return np.concatenate([[ngd_val, pmid_val], cat_onehot, edge_categories, curie_category_onehot, node_degrees_feature])


def get_category(cat_str, category_to_idx):
    cat_onehot = np.zeros(58, dtype=float)

    if cat_str:
        if cat_str in category_to_idx:
            cat_idx = category_to_idx[cat_str]
            cat_onehot[cat_idx] = 1.0
    return cat_onehot
