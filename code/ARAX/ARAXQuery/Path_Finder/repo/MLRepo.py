import pickle
import sys
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from feature_extractor import get_neighbors_info
from feature_extractor import get_category
from feature_extractor import get_np_array_features
from repo.Repository import Repository
from repo.NodeDegreeRepo import NodeDegreeRepo
from repo.NGDRepository import NGDRepository
from model.Node import Node


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class MLRepo(Repository):

    def __init__(self, repo, degree_repo=NodeDegreeRepo(), ngd_repo=NGDRepository(),
                 node_synonymizer=NodeSynonymizer()):
        self.repo = repo
        self.degree_repo = degree_repo
        self.ngd_repo = ngd_repo
        self.node_synonymizer = node_synonymizer
        self.bst_loaded = None
        self.ancestors_by_id = None
        self.category_to_idx = None
        self.edge_category_to_idx = None
        self.sorted_category_list = None
        self.node_degree_category_to_idx = None

    def load_data(self):
        abs_path = os.path.dirname(os.path.abspath(__file__))
        with open(abs_path + '/node_degree_category_by_indices.pkl', "rb") as f:
            self.node_degree_category_to_idx = pickle.load(f)

        with open(abs_path + '/sorted_category_list.pkl', "rb") as f:
            self.sorted_category_list = pickle.load(f)

        with open(abs_path + '/edge_category_to_idx.pkl', "rb") as f:
            self.edge_category_to_idx = pickle.load(f)
        self.category_to_idx = {cat_name: idx for idx, cat_name in enumerate(self.sorted_category_list)}

        with open(abs_path + '/ancestors_by_indices.pkl', "rb") as f:
            self.ancestors_by_id = pickle.load(f)

        self.bst_loaded = xgb.Booster()
        self.bst_loaded.load_model(abs_path + '/pathfinder_xgboost_model')

    def get_neighbors(self, node, limit=-1):
        if limit <= 0:
            raise Exception(f"The limit:{limit} could not be negative or zero.")

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_get_neighbors = executor.submit(
                get_neighbors_info,
                node.id,
                self.ngd_repo,
                self.repo,
                self.degree_repo
            )
            future_load_data = executor.submit(self.load_data)

            content_by_curie, curie_category = future_get_neighbors.result()

        if content_by_curie is None:
            return []
        curie_category_onehot = get_category(curie_category.split(":")[-1], self.category_to_idx)

        feature_list = []
        curie_list = []
        curie_degree = []
        curie_category = []
        for key, value in content_by_curie.items():
            curie_list.append(key)
            curie_degree.append(value.get('degree_by_category', {}).get('biolink:NamedThing', 0))
            curie_category.append(value.get('category', ''))
            feature_list.append(
                get_np_array_features(
                    value,
                    self.category_to_idx,
                    self.edge_category_to_idx,
                    curie_category_onehot,
                    self.ancestors_by_id,
                    self.node_degree_category_to_idx
                )
            )

        feature_np = np.empty((len(feature_list), len(feature_list[0])), dtype=float)

        for i in range(len(feature_list)):
            feature_np[i] = feature_list[i]

        dtest = xgb.DMatrix(feature_np)

        scores = self.bst_loaded.predict(dtest)

        probabilities = sigmoid(scores)

        ranked_items = sorted(
            zip(curie_list, probabilities, curie_degree, curie_category),
            key=lambda x: x[1],
            reverse=True
        )

        return [Node(
            id=item[0],
            weight=float(item[1]),
            degree=item[2],
            category=item[3]
        ) for item in ranked_items[0:limit]]

    def get_node_degree(self, node_id):
        return self.degree_repo.get_node_degree(node_id)
