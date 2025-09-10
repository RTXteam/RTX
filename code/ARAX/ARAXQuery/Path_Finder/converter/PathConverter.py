import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GraphToKnowledgeGraphConverter import GraphToKnowledgeGraphConverter


class PathConverter:

    def __init__(
            self,
            path,
            qnode_1_id,
            qnode_2_id,
            aux_name,
            edge_extractor,
            score
    ):
        self.path = path
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.aux_name = aux_name
        self.edge_extractor = edge_extractor
        self.score = score

    def convert(self, response):
        knowledge_graph_src_dest = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, [self.path])

        analysis = {
            "resource_id": "infores:arax",
            "path_bindings": {
                "p0": [{"id": self.aux_name}]
            },
            "score": self.score
        }

        aux_graph = {
            "edges": list(knowledge_graph_src_dest["edges"].keys()),
            "attributes": []
        }

        return analysis, aux_graph, knowledge_graph_src_dest
