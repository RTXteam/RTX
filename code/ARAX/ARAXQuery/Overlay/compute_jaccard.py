#!/bin/env python3
# This class will add a virtual edge to the KG decorated with the Jaccard index value on it.
# relevant issue is #611
# will need to figure out DSL syntax to ensure that such edges will be added to the correct source target nodes
# Need to decide if this will be done *only* on the local KG, or if the computation is going to be done via our underlying Neo4j KG
# for now, just do the computation on the local KG
import sys
import os
import traceback
import numpy as np

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge_attribute import Edge

class ComputeNGD:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def compute_jaccard(self):
        message = self.message
        parameters = self.parameters
        self.response.debug(f"Computing Jaccard distance and adding this information as virtual edges")
        self.response.info(f"Computing Jaccard distance and adding this information as virtual edges")

        self.response.info("Getting all intermediate nodes connected to start node")
        # TODO: should I check that they're connected to the start node, or just assume that they are?
        # TODO: For now, assume that they are
        intermediate_nodes = set()
        for node in message.knowledge_graph.nodes:
                intermediate_nodes.add(node.id)  # add the intermediate node by it's identifier

        node_curie_to_name = dict()
        try:
            for node in self.message.knowledge_graph.nodes:
                node_curie_to_name[node.id] = node.name
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Something went wrong when converting names")
            self.response.error(tb, error_code=error_type.__name__)


        self.response.warning(f"Utilizing API calls to NCBI eUtils, so this may take a while...")
        name = "normalized Google distance"
        type = "float"
        value = self.ngd_parameters['default_value']
        url = "TBD"

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
            self.response.error(f"Something went wrong adding the NGD edge attributes")
        else:
            self.response.info(f"NGD values successfully added to edges")

        return self.response