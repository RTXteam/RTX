import json
import logging
import os
import pickle
import sys

import numpy as np
import xgboost as xgb

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from feature_extractor import get_neighbors_info
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
    training_data = create_training_data()
    i = 0
    logging.info(len(training_data))
    node_synonymizer = NodeSynonymizer()
    category_list = node_synonymizer.get_distinct_category_list()
    category_list_sorted = sorted(category_list)
    category_to_idx = {cat_name: idx for idx, cat_name in enumerate(category_list_sorted)}
    edge_category_to_idx = {}
    edge_category_counter = 0
    ngd_repo = NGDRepository()
    plover_repo = PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    group = []
    curie = []
    curies = []
    y = []
    x_list = []
    for key_nodes_pair in training_data:
        content_by_curie = get_neighbors_info(key_nodes_pair[0], ngd_repo, plover_repo)
        if content_by_curie is None:
            continue
        group.append(len(content_by_curie))
        curie.append(key_nodes_pair[0])
        logging.info(f"neighbors length: {len(content_by_curie)}")
        for key, value in content_by_curie.items():
            if key in key_nodes_pair[1]:
                y.append(1)
            else:
                y.append(0)

            for category, _ in value['edges'].items():
                if category not in edge_category_to_idx:
                    edge_category_to_idx[category] = edge_category_counter
                    edge_category_counter = edge_category_counter + 1
            curies.append(key)
            x_list.append(get_np_array_features(value, category_to_idx, edge_category_to_idx))

        i = i + 1
        logging.info(f"training data counter: {i}")

    len_edge_category_to_idx = len(edge_category_to_idx)
    number_of_features = 60 + len_edge_category_to_idx

    x = np.empty((len(x_list), number_of_features), dtype=float)

    for i in range(len(x_list)):
        features = x_list[i]
        len_features = len(features)
        if len_features < number_of_features:
            x[i] = np.concatenate([features, np.zeros((number_of_features - len_features), dtype=float)])
        else:
            x[i] = x_list[i]

    np.save("X_data.npy", x)
    np.save("y_data.npy", y)
    with open("group.pkl", "wb") as f:
        pickle.dump(group, f)
    with open("curie.pkl", "wb") as f:
        pickle.dump(curie, f)
    with open("curies.pkl", "wb") as f:
        pickle.dump(curies, f)
    with open("edge_categories.pkl", "wb") as f:
        pickle.dump(edge_category_to_idx, f)


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
