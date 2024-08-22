import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.Repository import Repository
from repo.NodeDegreeRepo import NodeDegreeRepo
from repo.RedisConnector import RedisConnector
from repo.NGDRepository import NGDRepository
from model.Node import Node


class NGDSortedNeighborsRepo(Repository):

    def __init__(self, repo, degree_repo=NodeDegreeRepo(), redis_connector=RedisConnector(), ngd_repo=NGDRepository()):
        self.repo = repo
        self.degree_repo = degree_repo
        self.redis_connector = redis_connector
        self.ngd_repo = ngd_repo

    def get_neighbors(self, node, limit=-1):
        curie_ngd_list = self.ngd_repo.get_curie_ngd(node.id)
        ngd_by_curie_dict = {}
        if curie_ngd_list is not None:
            if limit != -1 and len(curie_ngd_list) >= limit:
                return [Node(curie, ngd_value) for curie, ngd_value in
                        curie_ngd_list[0:min(limit, len(curie_ngd_list))]]
            else:
                for curie, ngd in curie_ngd_list:
                    ngd_by_curie_dict[curie] = ngd

        neighbors = self.repo.get_neighbors(node, limit=limit)
        neighbors_ids = [neighbor.id for neighbor in neighbors]
        node_pmids_length = self.redis_connector.get_len_of_keys(neighbors_ids)
        node_pmids_length = [(key, length) for key, length in node_pmids_length if length > 0]

        curies_sorted_by_their_pmids_length = sorted(node_pmids_length, key=lambda x: (x[1]), reverse=True)

        nonzero_length_pmids_curie_with_none_ngd_value = []
        for curie, length in curies_sorted_by_their_pmids_length:
            if curie not in ngd_by_curie_dict:
                if limit == -1:
                    nonzero_length_pmids_curie_with_none_ngd_value.append((curie, None))
                elif len(ngd_by_curie_dict) + len(nonzero_length_pmids_curie_with_none_ngd_value) < limit:
                    nonzero_length_pmids_curie_with_none_ngd_value.append((curie, None))
                else:
                    break

        sorted_neighbors_tuple = sorted(ngd_by_curie_dict.items(),
                                        key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))

        sorted_neighbors_tuple.extend(nonzero_length_pmids_curie_with_none_ngd_value)

        if limit == -1:
            return [Node(item[0], item[1]) for item in sorted_neighbors_tuple]
        else:
            return [Node(item[0], item[1]) for item in
                    sorted_neighbors_tuple[0:min(limit, len(sorted_neighbors_tuple))]]

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
