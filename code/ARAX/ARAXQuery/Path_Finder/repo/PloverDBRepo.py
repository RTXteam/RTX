import os
import sys
import logging

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.Repository import Repository
from repo.NodeDegreeRepo import NodeDegreeRepo
from model.Node import Node


class PloverDBRepo(Repository):

    def __init__(self, plover_url, degree_repo=NodeDegreeRepo()):
        self.plover_url = plover_url
        self.degree_repo = degree_repo

    def get_neighbors(self, node, limit=-1):
        endpoint = "/get_neighbors"
        data = {"node_ids": [node.id], "categories": ["biolink:NamedThing"]}
        result = []
        try:
            response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
            response.raise_for_status()
            json = response.json()
            result = [Node(i) for i in json[node.id]]
        except requests.exceptions.RequestException as e:
            # log here print(f"Request error: {e}")
            pass
        except ValueError as e:
            # log here print(f"JSON decode error: {e}")
            pass
        except KeyError as e:
            # log here print(f"Key error: {e}")
            pass
        except Exception as e:
            pass
        return result

    def get_neighbors_with_edges(self, node_id_input, limit=-1):
        endpoint = "/query"
        data = {
            "edges": {
                "e": {
                    "subject": "n1",
                    "object": "n2"
                }
            },
            "nodes": {
                "n1": {
                    "ids": [
                        node_id_input
                    ]
                },
                "n2": {
                    "categories": [
                        "biolink:NamedThing"
                    ]
                }
            },
            "include_metadata": True,
            "respect_predicate_symmetry": True
        }
        try:
            response = requests.post(self.plover_url + endpoint,
                                     headers={'accept': 'application/json'}, json=data)
            response.raise_for_status()
            json = response.json()

            if len(json['nodes']['n1']) == 0 or len(json['nodes']['n2']) == 0:
                return None, None, None

            nodes = {}
            edges = {}
            for _, info in json['edges']['e'].items():
                if info[0] == node_id_input:
                    neighbor_id = info[1]
                elif info[1] == node_id_input:
                    neighbor_id = info[0]
                else:
                    continue
                nodes[neighbor_id] = json['nodes']['n2'][neighbor_id][1]
                edge_info = (info[2], info[3])
                if neighbor_id not in edges:
                    edges[neighbor_id] = [edge_info]
                else:
                    edges[neighbor_id].append(edge_info)
            return json['nodes']['n1'][node_id_input][1], nodes, edges
        except requests.exceptions.RequestException as e:
            logging.error("A requests error occurred: %s", e, exc_info=True)
            raise e
        except Exception as e:
            logging.error("An unexpected error occurred: %s", e, exc_info=True)
            raise e

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
