import math
from RedisConnector import RedisConnector
from NGDCalculator import calculate_ngd


class NGDSortedNeighborsRepo:

    def __init__(self, redis_connector=RedisConnector()):
        self.redis_connector = redis_connector

    def get_neighbors(self, key, neighbors, log_of_NGD_normalizer):
        node_pmids_length = self.redis_connector.get_key_length(key)
        curie_pmids_length_tuple = self.redis_connector.get_len_of_keys(neighbors)
        nonzero_pmid_length = [(curie, length) for curie, length in curie_pmids_length_tuple if length > 0]
        ngd_key_value = dict()
        if node_pmids_length != 0:
            intersection_list = self.redis_connector.get_intersection_list(key, nonzero_pmid_length)
            log_of_node_pmids_length = math.log(node_pmids_length)

            for pmid_length_pair, intersection in zip(nonzero_pmid_length, intersection_list):
                ngd = calculate_ngd(log_of_node_pmids_length, pmid_length_pair[1], len(intersection), log_of_NGD_normalizer)
                if ngd:
                    ngd_key_value[pmid_length_pair[0]] = ngd

        sorted_neighbors = sorted(ngd_key_value.items(),
                                  key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))

        return sorted_neighbors
