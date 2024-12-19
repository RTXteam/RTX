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

    def trapi_query(self, node, limit=-1):
        endpoint = "/query"
        data = {
            "message": {
                "query_graph": {
                    "edges": {
                        "e1": {
                            "object": "n1",
                            "subject": "n2"
                        }
                    },
                    "nodes": {
                        "n1": {
                            "ids": [
                                node.id
                            ]
                        },
                        "n2": {
                            "categories": ["biolink:NamedThing"]
                        }
                    }
                }
            }
        }
        result = []
        try:
            response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
            response.raise_for_status()
            json = response.json()
            result = []
            for node_id, node_attributes in json['message']['knowledge_graph']['nodes'].items():
                if node_id != node.id:
                    result.append(Node(id=node_id, category=node_attributes['categories'][0]))
            return result
        except requests.exceptions.RequestException as e:
            #  todo log here print(f"Request error: {e}")
            pass
        except Exception as e:
            #  todo log here print(f"Request error: {e}")
            pass
        return result

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
