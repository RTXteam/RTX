import requests
from .Repository import Repository
from ..model.Node import Node


class PloverDBRepo(Repository):

    def __init__(self):
        self.url = "https://kg2cploverdb.ci.transltr.io"
        self.headers = {
            'accept': 'application/json'
        }

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
        response = requests.post(self.url + endpoint, headers=self.headers, json=data)
        json = response.json()

        return [Node(i) for i in json['nodes']['n01'].keys()]
