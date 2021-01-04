# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np


class RemoveNodes:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.node_parameters = params

    def remove_nodes_by_type(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph matching the specified type")

        try:
            i = 0
            nodes_to_remove = set()
            node_ids_to_remove = set()
            # iterate over the edges find the edges to remove
            for node in self.message.knowledge_graph.nodes:
                if self.node_parameters['node_type'] in node.type:
                    nodes_to_remove.add(i)
                    node_ids_to_remove.add(node.id)
                i += 1
            self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            i = 0
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for edge in self.message.knowledge_graph.edges:
                if edge.source_id in node_ids_to_remove or edge.target_id in node_ids_to_remove:
                    edges_to_remove.add(i)
                i += 1
            # remove edges
            self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response

    def remove_nodes_by_property(self):
        """
        Iterate over all the nodes in the knowledge graph, remove any nodes matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph matching the specified property")
        node_params = self.node_parameters
        try:
            i = 0
            nodes_to_remove = set()
            node_ids_to_remove = set()
            # iterate over the nodes find the nodes to remove
            for node in self.message.knowledge_graph.nodes:
                node_dict = node.to_dict()
                if node_params['node_property'] in node_dict:
                    if isinstance(node_dict[node_params['node_property']], list):
                        if node_params['property_value'] in node_dict[node_params['node_property']]:
                            nodes_to_remove.add(i)
                        elif node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(i)
                    else:
                        if node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(i)
                i += 1
            self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            i = 0
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for edge in self.message.knowledge_graph.edges:
                if edge.source_id in node_ids_to_remove or edge.target_id in node_ids_to_remove:
                    edges_to_remove.add(i)
                i += 1
            # remove edges
            self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response

    def remove_orphaned_nodes(self):
        """
        Iterate over all the nodes/edges in the knowledge graph, remove any nodes not connected to edges (optionally matching the type provided)
        :return: response
        """
        self.response.debug(f"Removing orphaned nodes")
        self.response.info(f"Removing orphaned nodes")
        node_parameters = self.node_parameters

        try:
            # iterate over edges in KG to find all id's that connect the edges
            connected_node_ids = set()
            for edge in self.message.knowledge_graph.edges:
                connected_node_ids.add(edge.source_id)
                connected_node_ids.add(edge.target_id)

            # iterate over all nodes in KG
            node_indexes_to_remove = set()
            i = 0  # counter to keep track of where this node is in the message.knowledge_graph.nodes list
            for node in self.message.knowledge_graph.nodes:
                if 'node_type' in node_parameters and node_parameters['node_type'] in node.type:
                    if node.id not in connected_node_ids:
                        node_indexes_to_remove.add(i)
                else:
                    if node.id not in connected_node_ids:
                        node_indexes_to_remove.add(i)
                i += 1

            # remove the orphaned nodes
            self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in node_indexes_to_remove]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing orphaned nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response
