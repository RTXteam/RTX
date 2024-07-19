import sys
import os
import sqlite3
import math

from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.NGDCalculator import calculate_ngd
from repo.Repository import Repository
from repo.NodeDegreeRepo import NodeDegreeRepo
from repo.RedisConnector import RedisConnector
from model.Node import Node


def get_curie_to_pmids_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    ngd_filepath = os.path.sep.join(
        [*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    return f"{ngd_filepath}{os.path.sep}{RTXConfiguration().curie_to_pmids_path.split('/')[-1]}"


def get_node_pmids(node_id):
    query_to_find_pmids_for_node_id = f"SELECT pmids FROM curie_to_pmids WHERE curie == '{node_id}'"
    conn = sqlite3.connect(get_curie_to_pmids_path())
    cursor = conn.cursor()
    cursor.execute(query_to_find_pmids_for_node_id)
    node_pmids = cursor.fetchone()
    conn.close()
    return node_pmids


def get_neighbors_pmids(neighbors):
    chunk_size = 100000
    connection = sqlite3.connect(get_curie_to_pmids_path())
    base_query = "SELECT curie, pmids FROM curie_to_pmids WHERE curie IN ({})"
    results = []
    for i in range(0, len(neighbors), chunk_size):
        chunk = neighbors[i:i + chunk_size]
        placeholders = ', '.join('?' * len(chunk))
        query = base_query.format(placeholders)
        cursor = connection.cursor()
        cursor.execute(query, chunk)
        results.extend(cursor.fetchall())
    connection.close()
    return results


class NGDSortedNeighborsRepo(Repository):

    def __init__(self, repo, degree_repo=NodeDegreeRepo(), redis_connector=RedisConnector()):
        self.repo = repo
        self.degree_repo = degree_repo
        self.redis_connector = redis_connector

    def get_neighbors(self, node, limit=-1):

        neighbors = self.repo.get_neighbors(node, limit=limit)
        node_pmids_length = self.redis_connector.get_key_length(node.id)
        if node_pmids_length == 0:
            if limit == -1:
                return neighbors
            else:
                return neighbors[0:min(limit, len(neighbors))]

        neighbors_ids = [neighbor.id for neighbor in neighbors]
        curie_pmids_length_tuple = self.redis_connector.get_len_of_keys(neighbors_ids)
        non_zero_curie_pmids_length_tuple = [(key, length) for key, length in curie_pmids_length_tuple if length > 0]
        if len(non_zero_curie_pmids_length_tuple) == 0:
            if limit == -1:
                return neighbors
            else:
                return neighbors[0:min(limit, len(neighbors))]

        intersection_list = self.redis_connector.get_intersection_list(node.id, non_zero_curie_pmids_length_tuple)
        log_of_node_pmids_length = math.log(node_pmids_length)
        ngd_key_value = dict()
        for pmid_length_pair, intersection in zip(non_zero_curie_pmids_length_tuple, intersection_list):
            ngd_key_value[pmid_length_pair[0]] = calculate_ngd(log_of_node_pmids_length, pmid_length_pair[1], len(intersection))

        sorted_neighbors_tuple = sorted(ngd_key_value.items(),
                                        key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))

        if limit == -1:
            sorted_neighbors = [Node(item[0], item[1]) for item in sorted_neighbors_tuple]
        else:
            sorted_neighbors = [Node(item[0], item[1]) for item in
                                sorted_neighbors_tuple[0:min(limit, len(sorted_neighbors_tuple))]]

        return sorted_neighbors

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
