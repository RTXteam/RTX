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
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names,
            edge_extractor,
            score,
            blocked_curies,
            blocked_synonyms
    ):
        self.path = path
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.names = names
        self.edge_extractor = edge_extractor
        self.score = score
        self.block_curies = blocked_curies
        self.blocked_synonyms = blocked_synonyms

    def convert(self, response):
        knowledge_graph_src_dest = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, [self.path])

        if self.path_has_blocked_node(knowledge_graph_src_dest):
            return

        if len(self.path.links) > 2:
            essence = ""
            for i in range(1, len(self.path.links) - 1):
                if self.path.links[i].id in knowledge_graph_src_dest.nodes:
                    intermediate_node = knowledge_graph_src_dest.nodes[self.path.links[i].id]
                    if intermediate_node.name is not None:
                        essence = f"{essence}{intermediate_node.name}"
                if i != len(self.path.links) - 2:
                    essence = f"{essence} - "

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

    def path_has_blocked_node(self, kg):
        if len(self.path.links) > 2:
            for i in range(1, len(self.path.links) - 1):
                if self.path.links[i].id in self.block_curies:
                    return True
                if self.path.links[i].id in kg.nodes:
                    intermediate_node = kg.nodes[self.path.links[i].id]
                    if intermediate_node.name.lower() in self.blocked_synonyms:
                        return True
        return False
