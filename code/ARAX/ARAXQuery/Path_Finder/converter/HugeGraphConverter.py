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
            paths_src_mid,
            paths_mid_dest,
            node_1_id,
            node_2_id,
            node_in_between_id,
            qnode_1_id,
            qnode_2_id,
            qnode_in_between_id,
            names,
            edge_extractor
    ):
        self.paths = paths
        self.paths_src_mid = paths_src_mid
        self.paths_mid_dest = paths_mid_dest
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.node_in_between_id = node_in_between_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.qnode_in_between_id = qnode_in_between_id
        self.names = names
        self.edge_extractor = edge_extractor

    def convert(self, response):
        (source_destination_knowledge_graph_edge,
         source_middle_knowledge_graph_edge,
         destination_middle_knowledge_graph_edge) = self.self_created_knowledge_graph_edges()

        response.envelope.message.knowledge_graph.edges[
            self.names.kg_src_dest_edge_name] = source_destination_knowledge_graph_edge
        response.envelope.message.knowledge_graph.edges[
            self.names.kg_src_mid_edge_name] = source_middle_knowledge_graph_edge
        response.envelope.message.knowledge_graph.edges[
            self.names.kg_mid_dest_edge_name] = destination_middle_knowledge_graph_edge

        knowledge_graph_src_dest = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, self.paths)

        response.envelope.message.knowledge_graph.edges.update(knowledge_graph_src_dest.edges)
        response.envelope.message.knowledge_graph.nodes.update(knowledge_graph_src_dest.nodes)

        knowledge_graph_src_mid = GraphToKnowledgeGraphConverter(
            self.qnode_1_id,
            self.qnode_in_between_id,
            self.edge_extractor).convert(response, self.paths_src_mid)

        response.envelope.message.knowledge_graph.edges.update(knowledge_graph_src_mid.edges)
        response.envelope.message.knowledge_graph.nodes.update(knowledge_graph_src_mid.nodes)

        knowledge_graph_mid_dest = GraphToKnowledgeGraphConverter(
            self.qnode_in_between_id,
            self.qnode_2_id,
            self.edge_extractor).convert(response, self.paths_mid_dest)

        response.envelope.message.knowledge_graph.edges.update(knowledge_graph_mid_dest.edges)
        response.envelope.message.knowledge_graph.nodes.update(knowledge_graph_mid_dest.nodes)

        analyses = Analysis(
            edge_bindings={
                self.names.q_src_dest_edge_name: [
                    EdgeBinding(id=self.names.kg_src_dest_edge_name, attributes=[]),
                ],
                self.names.q_src_mid_edge_name: [
                    EdgeBinding(id=self.names.kg_src_mid_edge_name, attributes=[]),
                ],
                self.names.q_mid_dest_edge_name: [
                    EdgeBinding(id=self.names.kg_mid_dest_edge_name, attributes=[]),
                ]
            },
            resource_id="infores:arax",
        )

        if response.envelope.message.results is None:
            response.envelope.message.results = []

        essence = ''
        if self.node_in_between_id in knowledge_graph_src_dest.nodes:
            essence = knowledge_graph_src_dest.nodes[self.node_in_between_id].name
        else:
            response.error("Could not find main node id name to fill essence variable!")

        response.envelope.message.results.append(
            Result(
                id=self.names.result_name,
                analyses=[analyses],
                node_bindings={
                    self.qnode_1_id: [NodeBinding(id=self.node_1_id, attributes=[])],
                    self.qnode_2_id: [NodeBinding(id=self.node_2_id, attributes=[])],
                    self.qnode_in_between_id: [NodeBinding(id=self.node_in_between_id, attributes=[])]
                },
                essence=essence
            )
        )

        if response.envelope.message.auxiliary_graphs is None:
            response.envelope.message.auxiliary_graphs = {}
        response.envelope.message.auxiliary_graphs[self.names.auxiliary_graph_name] = AuxiliaryGraph(
            edges=list(knowledge_graph_src_dest.edges.keys()),
            attributes=[]
        )
        response.envelope.message.auxiliary_graphs[f"{self.names.auxiliary_graph_name}_1"] = AuxiliaryGraph(
            edges=list(knowledge_graph_src_mid.edges.keys()),
            attributes=[]
        )
        response.envelope.message.auxiliary_graphs[f"{self.names.auxiliary_graph_name}_2"] = AuxiliaryGraph(
            edges=list(knowledge_graph_mid_dest.edges.keys()),
            attributes=[]
        )

    def self_created_knowledge_graph_edges(self):
        direct_edge_with_support_graph = Edge(
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
            ],
            sources=[
                {
                    "resource_id": "infores:arax",
                    "resource_role": "primary_knowledge_source",
                    "source_record_urls": None,
                    "upstream_resource_ids": None
                }
            ]
        )
        direct_edge_with_support_graph.qedge_keys = [self.names.q_src_dest_edge_name]
        source_to_middle_node_edge_with_support_graph = Edge(
            object=self.node_1_id,
            subject=self.node_in_between_id,
            predicate='biolink:related_to',
            attributes=[
                Attribute(
                    attribute_source="infores:arax",
                    attribute_type_id="biolink:support_graphs",
                    value=[
                        f"{self.names.auxiliary_graph_name}_1"
                    ]
                )
            ],
            sources=[
                {
                    "resource_id": "infores:arax",
                    "resource_role": "primary_knowledge_source",
                    "source_record_urls": None,
                    "upstream_resource_ids": None
                }
            ]
        )
        source_to_middle_node_edge_with_support_graph.qedge_keys = [self.names.q_src_mid_edge_name]
        middle_to_source_node_edge_with_support_graph = Edge(
            object=self.node_in_between_id,
            subject=self.node_2_id,
            predicate='biolink:related_to',
            attributes=[
                Attribute(
                    attribute_source="infores:arax",
                    attribute_type_id="biolink:support_graphs",
                    value=[
                        f"{self.names.auxiliary_graph_name}_2"
                    ]
                )
            ],
            sources=[
                {
                    "resource_id": "infores:arax",
                    "resource_role": "primary_knowledge_source",
                    "source_record_urls": None,
                    "upstream_resource_ids": None
                }
            ]
        )
        middle_to_source_node_edge_with_support_graph.qedge_keys = [self.names.q_mid_dest_edge_name]
        return direct_edge_with_support_graph, source_to_middle_node_edge_with_support_graph, middle_to_source_node_edge_with_support_graph
