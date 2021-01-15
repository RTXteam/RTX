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

    def remove_nodes_by_category(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph matching the specified category")

        try:
            nodes_to_remove = set()
            #node_ids_to_remove = set()
            # iterate over the edges find the edges to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                if self.node_parameters['node_category'] in node.category:
                    nodes_to_remove.add(key)
                    #node_ids_to_remove.add(node.id)
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
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
            nodes_to_remove = set()
            #node_ids_to_remove = set()
            # iterate over the nodes find the nodes to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                node_dict = node.to_dict()
                if node_params['node_property'] in node_dict:
                    if isinstance(node_dict[node_params['node_property']], list):
                        if node_params['property_value'] in node_dict[node_params['node_property']]:
                            nodes_to_remove.add(key)
                        elif node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(key)
                    else:
                        if node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(key)
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
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
            for edge in self.message.knowledge_graph.edges.values():
                connected_node_ids.add(edge.subject)
                connected_node_ids.add(edge.object)

            # iterate over all nodes in KG
            nodes_to_remove = set()
            for key, node in self.message.knowledge_graph.nodes.items():
                if 'node_category' in node_parameters and node_parameters['node_category'] in node.category:
                    if node.id not in connected_node_ids:
                        nodes_to_remove.add(key)
                else:
                    if node.id not in connected_node_ids:
                        nodes_to_remove.add(key)

            # remove the orphaned nodes
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in node_indexes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing orphaned nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response
