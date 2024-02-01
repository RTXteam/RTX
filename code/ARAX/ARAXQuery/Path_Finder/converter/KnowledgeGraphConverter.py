import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.knowledge_graph import KnowledgeGraph


class KnowledgeGraphConverter:

    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()

    def convert(self, nodes, edges):
        for node in nodes:
            self.create_node(node)

        for edge in edges:
            self.create_edge(edge)

        return self.knowledge_graph

    def create_node(self, node):
        pass

    def create_edge(self, edge):
        pass
