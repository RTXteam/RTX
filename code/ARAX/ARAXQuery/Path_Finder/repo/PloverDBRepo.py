import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../model")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../repo")
from Repository import Repository
from Node import Node


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

        # todo really bad
        degree = len(json['nodes']['n01'].keys())

        print(f"{node.id} degree: {degree}")

        if degree > 50000:
            return []

        return [Node(i) for i in json['nodes']['n01'].keys()]


if __name__ == "__main__":
    PloverDBRepo("https://kg2cploverdb.transltr.io").get_neighbors(Node("GO:0043402"))