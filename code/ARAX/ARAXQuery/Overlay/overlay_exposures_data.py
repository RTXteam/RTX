#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+.
"""
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
        virtual_edge_label = self.parameters.get('virtual_edge_label')
        nodes_by_qg_id = {node.id: node for node in self.message.knowledge_graph.nodes}

        # Figure out all the different edges we should query ICEES for
        edges_to_query = [edge for edge in knowledge_graph.edges if self._is_between_chemical_and_disease(edge, nodes_by_qg_id)]

        # Craft and send a query graph for each such edge
        for edge in edges_to_query:
            source_node = nodes_by_qg_id.get(edge.source_id)
            target_node = nodes_by_qg_id.get(edge.target_id)
            edge_query_graph = QueryGraph(nodes=[QNode(id='icees_n0', curie=source_node.id, type=source_node.type),
                                                 QNode(id='icees_n1', curie=target_node.id, type=target_node.type)],
                                          edges=[QEdge(id='icees_e0', source_id=edge.source_id, target_id=edge.target_id)])

            returned_kg = self._run_icees_query_temporary(edge_query_graph)  # NOTE: will eventually be done in separate file
            for returned_edge in returned_kg.edges:
                if not returned_edge.source_id == returned_edge.target_id:  # Exclude any self-edges
                    # Add the data as separate virtual edges in our message KG (if desired)
                    if virtual_edge_label:
                        returned_edge.type = virtual_edge_label
                        knowledge_graph.edges.append(returned_edge)
                    # Otherwise add the data as edge attributes on existing edges in our message KG
                    else:
                        edge.edge_attributes += returned_edge.edge_attributes

        # Add those edges to the KG, filtering out self-edges

        return self.response

    @staticmethod
    def _is_between_chemical_and_disease(edge, nodes_by_qg_id):
        chemical_types = {'chemical_substance', 'drug'}
        disease_types = {'disease', 'phenotypic_feature'}
        source_node = nodes_by_qg_id.get(edge.source_id)
        target_node = nodes_by_qg_id.get(edge.target_id)
        if set(source_node.type).intersection(chemical_types) and set(target_node.type).intersection(disease_types):
            return True
        elif set(source_node.type).intersection(disease_types) and set(target_node.type).intersection(chemical_types):
            return True
        else:
            return False
