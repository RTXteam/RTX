import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.query_graph import QueryGraph


class QueryGraphConverter:

    def __init__(self):
        self.query_graph = QueryGraph()

    def convert(self, nodes, edges):
        for node in nodes:
            self.create_node(node)

        for edge in edges:
            self.create_edge(edge)

        return self.query_graph

    def create_node(self, node):
        pass

    def create_edge(self, edge):
        pass
