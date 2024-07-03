import os
import sys

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
        endpoint = "/query"
        data = {
            "edges": {
                "e00": {
                    "subject": "n00",
                    "object": "n01"
                }
            },
            "nodes": {
                "n00": {
                    "ids": [node.id]
                },
                "n01": {
                    "categories": ["biolink:NamedThing"]
                }
            },
            "include_metadata": True,
            "respect_predicate_symmetry": True
        }
        result = []
        try:
            response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
            response.raise_for_status()
            json = response.json()
            result = [Node(i) for i in json['nodes']['n01'].keys()]
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

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
