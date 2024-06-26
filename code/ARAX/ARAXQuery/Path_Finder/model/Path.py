import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Node import Node


class Path:

    def __init__(self, path_limit, links=None):
        if links is None:
            links = list()
        self.path_limit = path_limit
        self.links = links

    def __str__(self):
        return "_".join([link.id for link in self.links])

    def __eq__(self, other):
        if isinstance(other, Path):
            return str(self) == str(other)
        return False

    def __hash__(self):
        return hash(str(self))

    def compute_weight(self):
        weight = 0
        for link in self.links:
            if link.weight == float('inf') or link.weight is None:
                return float('inf')
            weight = weight + link.weight
        return weight

    def make_new_path(self, last_link):
        new_links = [Node(link.id, link.weight, link.name, link.degree) for link in self.links]
        new_links.append(last_link)
        return Path(self.path_limit - 1, new_links)

    def last(self):
        if len(self.links) == 0:
            raise Exception("Path is empty.")
        return self.links[-1]
