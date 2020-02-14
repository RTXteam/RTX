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


class RemoveEdges:

    #### Constructor
    def __init__(self, response, message, edge_params):
        self.response = response
        self.message = message
        self.edge_parameters = edge_params

    def compute_ngd(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Edges")
        self.response.info(f"Removing edges from the knowledge graph")

        # iterate over KG edges, add the information
        try:
            for edge in self.message.knowledge_graph.edges:
                # Make sure the edge_attributes are not None
                if not edge.edge_attributes:
                    edge.edge_attributes = []  # should be an array, but why not a list?
                # now go and actually get the NGD
                source_curie = edge.source_id
                target_curie = edge.target_id
                source_name = node_curie_to_name[source_curie]
                target_name = node_curie_to_name[target_curie]
                ngd_value = NGD.get_ngd_for_all([source_curie, target_curie], [source_name, target_name])
                if np.isfinite(ngd_value):  # if ngd is finite, that's ok, otherwise, stay with default
                    value = ngd_value
                ngd_edge_attribute = EdgeAttribute(type=type, name=name, value=value, url=url)  # populate the NGD edge attribute
                edge.edge_attributes.append(ngd_edge_attribute)  # append it to the list of attributes
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.error(f"Something went wrong removing edges from the knowledge graph")
        else:
            self.response.info(f"Edges successfully removed")

        return self.response