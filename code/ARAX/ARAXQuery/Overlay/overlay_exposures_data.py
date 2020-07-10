#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It currently adds the data in
EdgeAttributes tacked onto existing edges.
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.edge_attribute import EdgeAttribute


class OverlayExposuresData:

    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def decorate(self):
        knowledge_graph = self.message.knowledge_graph
        nodes_by_qg_id = {node.id: node for node in self.message.knowledge_graph.nodes}
        log = self.response

        # Figure out all the different edges we should query ICEES for
        edges_to_query = [edge for edge in knowledge_graph.edges if self._is_relevant_edge(edge, nodes_by_qg_id)]
        if not edges_to_query:
            log.warning(f"Could not find any edges appropriate to query ICEES+ for")
            return self.response

        # Craft and send a query graph for each such edge
        num_edges_obtained_icees_data_for = 0
        for edge in edges_to_query:
            # TODO: Utilize NodeSynonymizer to try to grab curies ICEES likes better...
            source_node = nodes_by_qg_id.get(edge.source_id)
            target_node = nodes_by_qg_id.get(edge.target_id)
            edge_query_graph = QueryGraph(nodes=[QNode(id=source_node.id, curie=source_node.id, type=source_node.type),
                                                 QNode(id=target_node.id, curie=target_node.id, type=target_node.type)],
                                          edges=[QEdge(id=f"icees_{edge.id}", source_id=edge.source_id, target_id=edge.target_id)])
            log.debug(f"Sending query to ICEES+ for edge: {edge.source_id}--{edge.target_id}")
            returned_kg = self._get_exposures_data(edge_query_graph)
            if returned_kg:
                log.debug(f"Got exposures data back from ICEES+ for edge {edge.source_id}--{edge.target_id}")
                num_edges_obtained_icees_data_for += 1
                for returned_edge in returned_kg.edges:
                    # TODO: They provide edges in both directions (seem to have identical p-values)... should we only keep one direction?
                    if not returned_edge.source_id == returned_edge.target_id:  # Exclude self-edges
                        # Add the data as a new EdgeAttribute on the current edge
                        if edge.edge_attributes:
                            edge.edge_attributes += returned_edge.edge_attributes

        if num_edges_obtained_icees_data_for:
            log.info(f"Overlayed {num_edges_obtained_icees_data_for} edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any edges in the KG")

        return self.response

    @staticmethod
    def _get_exposures_data(query_graph):
        # Note: ICEES doesn't quite accept ReasonerStdAPI query graphs, so we transform to what works
        edges = [edge.to_dict() for edge in query_graph.edges]
        nodes = [{"node_id": node.id, "curie": node.curie, "type": node.type} for node in query_graph.nodes]
        icees_compatible_json = json.dumps({"message": {"knowledge_graph": {"edges": edges,
                                                                            "nodes": nodes}}})
        # TODO: Actually run the query using Query_ICEES.py, and load results into API model
        # TODO: Figure out how to represent their EdgeAttributes... they look like: "edge_attributes": [
        #             {
        #               "src_feature": "AlopeciaDx",
        #               "tgt_feature": "AvgDailyAcetaldehydeExposure_2",
        #               "p_value": 0.000003790881671012495
        #             }

        # Using this just for testing purposes! (until we have a working Query_ICEES.py plugged in)
        return KnowledgeGraph(nodes=[Node(id="SCTID:72164009", type=["disease"]),
                                     Node(id="CHEBI:15343", type=["chemical_substance"])],
                              edges=[Edge(id="icees_n00_n01",
                                          source_id="SCTID:72164009",
                                          target_id="CHEBI:15343",
                                          type="association",
                                          edge_attributes=[EdgeAttribute(name="AvgDailyAcetaldehydeExposure_2",
                                                                         value=0.000003790881671012495)]),
                                     Edge(id="icees_n00_n00",
                                          source_id="SCTID:72164009",
                                          target_id="SCTID:72164009",
                                          type="association",
                                          edge_attributes=[EdgeAttribute(name="AvgDailyAcetaldehydeExposure_2",
                                                                         value=0)])])

    @staticmethod
    def _is_relevant_edge(edge, nodes_by_qg_id):
        # TODO: Does every edge need to involve a drug/chemical_substance?
        exposures_node_types = {'chemical_substance', 'drug', 'disease', 'phenotypic_feature'}
        source_node = nodes_by_qg_id.get(edge.source_id)
        target_node = nodes_by_qg_id.get(edge.target_id)
        if set(source_node.type).intersection(exposures_node_types) and set(target_node.type).intersection(exposures_node_types):
            return True
        else:
            return False
