import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from converter.PathListToGraphConverter import PathListToGraphConverter
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph

class GraphToKnowledgeGraphConverter:

    def __init__(
            self,
            qnode_1_id,
            qnode_2_id,
            edge_extractor
    ):
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.edge_extractor = edge_extractor

    def convert(self, response, paths):
        nodes, edges = PathListToGraphConverter(self.qnode_1_id, self.qnode_2_id).convert(paths)

        pairs = []
        for _, edge in edges.items():
            pairs.append([nodes[edge[0]], nodes[edge[1]]])

        knowledge_graph = self.edge_extractor.get_edges(pairs, response)

        return KnowledgeGraph().from_dict(knowledge_graph)
