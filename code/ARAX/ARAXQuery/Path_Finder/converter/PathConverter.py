import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GraphToKnowledgeGraphConverter import GraphToKnowledgeGraphConverter

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.pathfinder_analysis import PathfinderAnalysis
from openapi_server.models.path_binding import PathBinding


class PathConverter:

    def __init__(
            self,
            path,
            qnode_1_id,
            qnode_2_id,
            names,
            edge_extractor,
            score
    ):
        self.path = path
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.names = names
        self.edge_extractor = edge_extractor
        self.score = score

    def convert(self, response):
        knowledge_graph_src_dest = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, [self.path])

        response.envelope.message.knowledge_graph.edges.update(knowledge_graph_src_dest.edges)
        response.envelope.message.knowledge_graph.nodes.update(knowledge_graph_src_dest.nodes)

        response.envelope.message.results[0].analyses.append(
            PathfinderAnalysis(
                resource_id="infores:arax",
                path_bindings={
                    "p0": [PathBinding(id=self.names.auxiliary_graph_name)]
                },
                score=self.score
            )
        )

        if response.envelope.message.auxiliary_graphs is None:
            response.envelope.message.auxiliary_graphs = {}

        response.envelope.message.auxiliary_graphs[self.names.auxiliary_graph_name] = AuxiliaryGraph(
            edges=list(knowledge_graph_src_dest.edges.keys()),
            attributes=[]
        )
