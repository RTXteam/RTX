import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GraphToKnowledgeGraphConverter import GraphToKnowledgeGraphConverter

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.analysis import Analysis
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.result import Result


class PathConverter:

    def __init__(
            self,
            path,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            qnode_in_between_id,
            names,
            edge_extractor,
            score,
            descendants
    ):
        self.path = path
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.qnode_in_between_id = qnode_in_between_id
        self.names = names
        self.edge_extractor = edge_extractor
        self.score = score
        self.descendants = descendants

    def path_has_category_constraint(self, knowledge_graph_src_dest):
        if len(self.path.links) > 2:
            for i in range(1, len(self.path.links) - 1):
                if self.path.links[i].id in knowledge_graph_src_dest.nodes:
                    intermediate_node = knowledge_graph_src_dest.nodes[self.path.links[i].id]
                    for category in intermediate_node.categories:
                        if category in self.descendants:
                            return self.path.links[i].id
        return None

    def convert(self, response):
        knowledge_graph_src_dest = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, [self.path])

        category_constraint_id = None
        if self.descendants:
            category_constraint_id = self.path_has_category_constraint(knowledge_graph_src_dest)
            if category_constraint_id is None:
                return

        essence = "Direct path"
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

        analyses = Analysis(
            edge_bindings={
            },
            resource_id="infores:arax",
            support_graphs=[self.names.auxiliary_graph_name],
            score=self.score
        )

        if response.envelope.message.results is None:
            response.envelope.message.results = []

        node_bindings = {
            self.qnode_1_id: [NodeBinding(id=self.node_1_id, attributes=[])],
            self.qnode_2_id: [NodeBinding(id=self.node_2_id, attributes=[])]
        }
        if category_constraint_id:
            node_bindings[self.qnode_in_between_id] = [NodeBinding(id=category_constraint_id, attributes=[])]

        response.envelope.message.results.append(
            Result(
                id=self.names.result_name,
                analyses=[analyses],
                node_bindings= node_bindings,
                essence=essence
            )
        )

        if response.envelope.message.auxiliary_graphs is None:
            response.envelope.message.auxiliary_graphs = {}

        response.envelope.message.auxiliary_graphs[self.names.auxiliary_graph_name] = AuxiliaryGraph(
            edges=list(knowledge_graph_src_dest.edges.keys()),
            attributes=[]
        )
