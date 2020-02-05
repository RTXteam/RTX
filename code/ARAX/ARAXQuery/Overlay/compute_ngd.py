# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import json
import ast
import re
import traceback
from response import Response
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

class ComputeNGD:

    #### Constructor
    def __init__(self, response, message, ngd_params):
        self.response = response
        self.message = message
        self.ngd_parameters = ngd_params

    def compute_ngd(self, default=float('inf')):
        """
        Iterate over all the edges in the knowledge graph, compute the normalized google distance and stick that info
        on the edge_attributes
        :return: response
        """
        self.response.debug(f"Computing NGD")
        self.response.info(f"Computing the normalized Google distance: weighting edges based on source/target node "
                           f"co-occurrence frequency in PubMed abstracts")

        self.response.warning(f"So far just a fixed value to make sure things go in the right place")
        name = "normalized Google distance"
        type = "float"
        value = default
        url = "TBD"

        # iterate over KG edges, add the information
        try:
            for edge in self.message.knowledge_graph.edges:
                # Make sure the edge_attributes are not None
                if not edge.edge_attributes:
                    edge.edge_attributes = []  # should be an array, but why not a list?

                ngd_edge_attribute = EdgeAttribute(type=type, name=name, value=0.5, url=url)
                edge.edge_attributes.append(ngd_edge_attribute)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.debug(f"Something went wrong adding the NGD edge attributes")
        else:
            self.response.info(f"NGD values successfully added to edges")

        return self.response