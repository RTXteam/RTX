import math
import os
import pickle
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Node import Node


class Path:

    def __init__(self, path_limit, links=None):
        if links is None:
            links = list()
        self.path_limit = path_limit
        self.links = links

    def __eq__(self, other):
        if isinstance(other, Path):
            return str(self) == str(other)
        return False

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        result = ""
        for link in self.links:
            result += str(link)
        return result

    def compute_weight(self):
        weight = 0
        degree_sum = 0
        for link in self.links:
            if link.weight == float('inf') or link.weight is None:
                return float('inf')
            degree_sum += link.degree
            weight += link.weight

        if degree_sum > 1:
            weight /= math.log(degree_sum, 10)

        return weight / len(self.links)

    def make_new_path(self, last_link):
        new_links = [Node(link.id, link.weight, link.name, link.degree, link.category) for link in self.links]
        new_links.append(last_link)
        return Path(self.path_limit - 1, new_links)

    def last(self):
        if len(self.links) == 0:
            raise Exception("Path is empty.")
        return self.links[-1]

    def path_src_to_id(self, id):
        new_links = []
        for link in self.links:
            new_links.append(Node(link.id, link.weight, link.name, link.degree, link.category))
            if link.id == id:
                break
        return Path(len(new_links) - 1, new_links)

    def path_id_to_dest(self, id):
        new_links = []
        for link in reversed(self.links):
            new_links.append(Node(link.id, link.weight, link.name, link.degree, link.category))
            if link.id == id:
                break
        new_links.reverse()
        return Path(len(new_links) - 1, new_links)

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(data):
        return pickle.loads(data)
