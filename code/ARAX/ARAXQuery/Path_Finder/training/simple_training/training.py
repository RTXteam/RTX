import json
import logging
import os
import pickle
import sys

import numpy as np
import xgboost as xgb

from hyperparameter_tuning import tune_hyperparameters
from data_loader import load_data

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
from repo.NodeDegreeRepo import NodeDegreeRepo

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
    node_degree_repo = NodeDegreeRepo()
    degree_categories = node_degree_repo.get_degree_categories()
    sorted_degree_category = sorted(list(degree_categories))
    degree_category_to_idx = {cat_name: idx for idx, cat_name in enumerate(sorted_degree_category)}

    with open((os.path.dirname(os.path.abspath(__file__)) + '/edge_category_to_idx.pkl'), "rb") as f:
        edge_category_to_idx = pickle.load(f)
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
    sorted_category_list = sorted(category_list)
    category_to_idx = {cat_name: idx for idx, cat_name in enumerate(sorted_category_list)}
    ngd_repo = NGDRepository()
    plover_repo = PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    group = []
    curie = []
    curies = []
    y = []
    x_list = []
    for key_nodes_pair in training_data:
        content_by_curie, curie_category = get_neighbors_info(
            key_nodes_pair[0],
            ngd_repo,
            plover_repo,
            node_degree_repo
        )
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
            x_list.append(
                get_np_array_features(
                    value,
                    category_to_idx,
                    edge_category_to_idx,
                    curie_category_onehot,
                    ancestors_by_indices,
                    degree_category_to_idx
                )
            )

        i = i + 1
        logging.info(f"training data counter: {i}")

    x = np.empty((len(x_list), len(x_list[0])), dtype=float)

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
    with open("sorted_category_list.pkl", "wb") as f:
        pickle.dump(sorted_category_list, f)
    with open("node_degree_category_by_indices.pkl", "wb") as f:
        pickle.dump(degree_category_to_idx, f)


def train():
    x, y, group = load_data()

    dtrain = xgb.DMatrix(x, label=y)
    dtrain.set_group(group)
    params = {  # hyperparameters extracted from the last hyperparameter-tuning.log
        'objective': 'rank:pairwise',
        'eval_metric': 'ndcg',
        'eta': 0.24,
        'max_depth': 10,
        'subsample': 0.91,
        'colsample_bytree': 0.84,
        'min_child_weight': 8,
        'gamma': 3.87
    }
    bst = xgb.train(params, dtrain, num_boost_round=200)
    bst.save_model("pathfinder_xgboost_model")
    logging.info("Training finished")


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
    # tune_hyperparameters()
    train()
