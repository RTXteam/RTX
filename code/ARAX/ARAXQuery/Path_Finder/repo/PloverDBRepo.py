import requests

from RTXConfiguration import RTXConfiguration
from .Repository import Repository
from ..model.Node import Node


class PloverDBRepo(Repository):

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
        rtx_config = RTXConfiguration()
        plover_url = rtx_config.plover_url
        response = requests.post(plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
        json = response.json()

        return [Node(i) for i in json['nodes']['n01'].keys()]
