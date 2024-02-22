import sys
import os
import sqlite3

from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.NGDCalculator import calculate_ngd
from repo.Repository import Repository
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

    def __init__(self, repo):
        self.repo = repo

    def get_neighbors(self, node, limit=-1):

        neighbors = self.repo.get_neighbors(node, limit=limit)

        node_pmids = get_node_pmids(node.id)
        if node_pmids is None:
            if limit == -1:
                return neighbors
            else:
                return neighbors[0:min(limit, len(neighbors))]

        neighbors_to_pmids = get_neighbors_pmids([neighbor.id for neighbor in neighbors])
        if neighbors_to_pmids is None:
            if limit == -1:
                return neighbors
            else:
                return neighbors[0:min(limit, len(neighbors))]

        curie_pmids_dict = dict(neighbors_to_pmids)
        ngd_key_value = dict()
        node_pmids_set = set(node_pmids[0].strip('][').split(','))
        for key, value in curie_pmids_dict.items():
            second_element_pmids = value.strip('][').split(',')
            ngd_key_value[key] = calculate_ngd(node_pmids_set, set(second_element_pmids))

        sorted_neighbors_tuple = sorted(ngd_key_value.items(),
                                        key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))

        if limit == -1:
            sorted_neighbors = [Node(item[0], item[1]) for item in sorted_neighbors_tuple]
        else:
            sorted_neighbors = [Node(item[0], item[1]) for item in
                                sorted_neighbors_tuple[0:min(limit, len(sorted_neighbors_tuple))]]

        return sorted_neighbors
