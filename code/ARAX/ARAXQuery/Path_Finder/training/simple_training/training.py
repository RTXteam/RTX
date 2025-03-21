import json
import logging
import os
import pickle
import sys

import numpy as np
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../BiolinkHelper/")
from biolink_helper import BiolinkHelper

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from feature_extractor import get_neighbors_info
from feature_extractor import get_category
from feature_extractor import get_np_array_features
from repo.NGDRepository import NGDRepository
from repo.PloverDBRepo import PloverDBRepo
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


def create_training_data():
    with open('./../data/training.json', 'r') as file:
        data = json.load(file)
    training = []
    for key, value in data.items():
        related_CURIE = set()

        batch_of_nodes = [k for k in value["indication_NER_aligned"].keys()]
        batch_of_nodes.extend([k for k in value["mechanistic_intermediate_nodes"].keys()])

        related_CURIE.add(key)
        related_CURIE.update(batch_of_nodes)

        for rel in related_CURIE:
            training.append((rel, related_CURIE))

    return training


def gather_data():
    edge_category_to_idx = {'biolink:related_to': 0, 'biolink:close_match': 1, 'biolink:subclass_of': 2,
                            'biolink:interacts_with': 3,
                            'biolink:treats_or_applied_or_studied_to_treat': 4, 'biolink:affects': 5,
                            'biolink:has_input': 6,
                            'biolink:causes': 7, 'biolink:disrupts': 8,
                            'biolink:preventative_for_condition': 9,
                            'biolink:predisposes_to_condition': 10, 'biolink:produces': 11,
                            'biolink:coexists_with': 12,
                            'biolink:precedes': 13, 'biolink:exacerbates_condition': 14,
                            'biolink:manifestation_of': 15,
                            'biolink:located_in': 16, 'biolink:diagnoses': 17, 'biolink:occurs_in': 18,
                            'biolink:has_participant': 19,
                            'biolink:in_clinical_trials_for': 20, 'biolink:treats': 21,
                            'biolink:contraindicated_in': 22,
                            'biolink:physically_interacts_with': 23, 'biolink:has_metabolite': 24,
                            'biolink:has_member': 25,
                            'biolink:has_part': 26, 'biolink:transcribed_from': 27, 'biolink:regulates': 28,
                            'biolink:gene_associated_with_condition': 29, 'biolink:translates_to': 30,
                            'biolink:enables': 31,
                            'biolink:actively_involved_in': 32, 'biolink:capable_of': 33,
                            'biolink:colocalizes_with': 34,
                            'biolink:in_taxon': 35, 'biolink:expressed_in': 36, 'biolink:gene_product_of': 37,
                            'biolink:directly_physically_interacts_with': 38, 'biolink:contributes_to': 39,
                            'biolink:applied_to_treat': 40,
                            'biolink:biomarker_for': 41, 'biolink:overlaps': 42, 'biolink:has_phenotype': 43,
                            'biolink:same_as': 44,
                            'biolink:has_output': 45, 'biolink:chemically_similar_to': 46,
                            'biolink:derives_from': 47,
                            'biolink:is_sequence_variant_of': 48, 'biolink:associated_with': 49,
                            'biolink:correlated_with': 50,
                            'biolink:disease_has_location': 51, 'biolink:exact_match': 52,
                            'biolink:temporally_related_to': 53,
                            'biolink:composed_primarily_of': 54, 'biolink:has_plasma_membrane_part': 55,
                            'biolink:has_not_completed': 56,
                            'biolink:develops_from': 57, 'biolink:has_increased_amount': 58,
                            'biolink:lacks_part': 59,
                            'biolink:has_decreased_amount': 60, 'biolink:opposite_of': 61,
                            'biolink:beneficial_in_models_for': 62,
                            'biolink:disease_has_basis_in': 63,
                            'biolink:indirectly_physically_interacts_with': 64}
    ancestors_by_indices = {}
    biolink_helper = BiolinkHelper()
    for key, value in edge_category_to_idx.items():
        ancestors = biolink_helper.get_ancestors(key)
        indices_of_ancestors = []
        for ancestor in ancestors:
            if ancestor in edge_category_to_idx:
                indices_of_ancestors.append(edge_category_to_idx[ancestor])
        ancestors_by_indices[value] = indices_of_ancestors

    training_data = create_training_data()
    i = 0
    logging.info(len(training_data))
    node_synonymizer = NodeSynonymizer()
    category_list = node_synonymizer.get_distinct_category_list()
    category_list_sorted = sorted(category_list)
    category_to_idx = {cat_name: idx for idx, cat_name in enumerate(category_list_sorted)}
    ngd_repo = NGDRepository()
    plover_repo = PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    group = []
    curie = []
    curies = []
    y = []
    x_list = []
    for key_nodes_pair in training_data:
        content_by_curie, curie_category = get_neighbors_info(key_nodes_pair[0], ngd_repo, plover_repo)
        if content_by_curie is None:
            continue
        curie_category_onehot = get_category(curie_category.split(":")[-1], category_to_idx)
        group.append(len(content_by_curie))
        curie.append(key_nodes_pair[0])
        logging.info(f"neighbors length: {len(content_by_curie)}")
        for key, value in content_by_curie.items():
            if key in key_nodes_pair[1]:
                y.append(1)
            else:
                y.append(0)

            curies.append(key)
            x_list.append(get_np_array_features(value, category_to_idx, edge_category_to_idx, curie_category_onehot,
                                                ancestors_by_indices))

        i = i + 1
        logging.info(f"training data counter: {i}")

    x = np.empty((len(x_list), 183), dtype=float)

    for i in range(len(x_list)):
        x[i] = x_list[i]

    np.save("X_data.npy", x)
    np.save("y_data.npy", y)
    with open("group.pkl", "wb") as f:
        pickle.dump(group, f)
    with open("curie.pkl", "wb") as f:
        pickle.dump(curie, f)
    with open("curies.pkl", "wb") as f:
        pickle.dump(curies, f)
    with open("ancestors_by_indices.pkl", "wb") as f:
        pickle.dump(ancestors_by_indices, f)


def train():
    x = np.load("X_data.npy")
    y = np.load("y_data.npy")
    with open("group.pkl", "rb") as f:
        group = pickle.load(f)
    dtrain = xgb.DMatrix(x, label=y)
    dtrain.set_group(group)
    params = {
        'objective': 'rank:pairwise',
        'eval_metric': 'ndcg',
        'eta': 0.1,
        'max_depth': 5
    }
    bst = xgb.train(params, dtrain, num_boost_round=100)
    bst.save_model("pathfinder_xgboost_model")


def feature_importance():
    bst_loaded = xgb.Booster()
    bst_loaded.load_model("model")
    importance_dict = bst_loaded.get_score(importance_type='cover')
    logging.info(importance_dict)

    from xgboost import plot_importance
    import matplotlib.pyplot as plt
    plot_importance(bst_loaded, importance_type='cover')
    plt.savefig("feature_importance_cover.png")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    gather_data()
    train()
