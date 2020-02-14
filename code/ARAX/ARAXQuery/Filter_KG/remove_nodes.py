# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance as NGD


class RemoveNodes:

    #### Constructor
    def __init__(self, response, message, edge_params):
        self.response = response
        self.message = message
        self.node_parameters = nodes_params

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
            # iterrate over the edges find the edges to remove
            for node in self.message.knowledge_graph.nodes:
                if self.node_parameters['node_type'] in node.type:
                    nodes_to_remove.add(i)
                    node_ids_to_remove.add(node.id)
                i += 1
            self.message.knowledge_graph.nodes = [val for idx,val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            i = 0
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for edge in self.message.knowledge_graph.edges:
                if edge.source_id in node_ids_to_remove or edge.target_id in node_ids_to_remove:
                    edges_to_remove.add(i)
                i += 1
            # remove edges
            self.message.knowledge_graph.edges = [val for idx,val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response

  