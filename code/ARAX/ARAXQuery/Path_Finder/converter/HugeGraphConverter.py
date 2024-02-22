import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GraphToKnowledgeGraphConverter import GraphToKnowledgeGraphConverter

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.analysis import Analysis
from openapi_server.models.edge_binding import EdgeBinding
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.result import Result
from openapi_server.models.attribute import Attribute


class HugeGraphConverter:

    def __init__(
            self,
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names
    ):
        self.paths = paths
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.names = names

    def convert(self, response):
        edge_with_support_graph = Edge(
            object=self.node_1_id,
            subject=self.node_2_id,
            predicate='biolink:related_to',
            attributes=[
                Attribute(
                    attribute_source="infores:arax",
                    attribute_type_id="biolink:support_graphs",
                    value=[
                        self.names.auxiliary_graph_name
                    ]
                )
            ]
        )
        edge_with_support_graph.qedge_keys = [self.names.q_edge_name]
        response.envelope.message.knowledge_graph.edges[self.names.kg_edge_name] = edge_with_support_graph

        knowledge_graph = GraphToKnowledgeGraphConverter(self.qnode_1_id, self.qnode_2_id).convert(response, self.paths)

        response.envelope.message.knowledge_graph.edges.update(knowledge_graph.edges)
        response.envelope.message.knowledge_graph.nodes.update(knowledge_graph.nodes)

        analyses = Analysis(
            edge_bindings={
                self.names.q_edge_name: [
                    EdgeBinding(id=self.names.kg_edge_name)
                ]
            }
        )

        if response.envelope.message.results is None:
            response.envelope.message.results = []

        essence = ''
        if self.names.essence != '':
            essence = knowledge_graph.nodes[self.names.main_node_id].name

        response.envelope.message.results.append(
            Result(
                id=self.names.result_name,
                analyses=[analyses],
                node_bindings={
                    self.qnode_1_id: [NodeBinding(id=self.node_1_id)],
                    self.qnode_2_id: [NodeBinding(id=self.node_2_id)]
                },
                essence=essence
            )
        )

        if response.envelope.message.auxiliary_graphs is None:
            response.envelope.message.auxiliary_graphs = {}
        response.envelope.message.auxiliary_graphs[self.names.auxiliary_graph_name] = AuxiliaryGraph(
            edges=list(knowledge_graph.edges.keys())
        )
