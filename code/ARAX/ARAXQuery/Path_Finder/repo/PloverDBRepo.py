import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.Repository import Repository
from model.Node import Node


class PloverDBRepo(Repository):

    def __init__(self, plover_url):
        self.plover_url = plover_url

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
        response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
        json = response.json()

        return [Node(i) for i in json['nodes']['n01'].keys()]
