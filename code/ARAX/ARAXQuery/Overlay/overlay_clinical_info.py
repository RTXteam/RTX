# This class will overlay the clinical information we have on hand
#!/bin/env python3
import sys
import os
import traceback
import numpy as np

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from QueryCOHD import QueryCOHD as COHD


class OverlayClinicalInfo:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.parameters = params
        self.who_knows_about_what = {'COHD': ['chemical_substance', 'phenotypic_feature', 'disease']}  # FIXME: replace this with information about the KP's, KS's, and their API's

    def decorate(self, parameters):
        if 'paired_concept_freq' in parameters:
            if parameters['paired_concept_freq'] == 'true':
                self.paired_concept_freq()
                # TODO: should I return the response and merge, or is it passed by reference and just return at the end?
            if parameters['associated_concept_freq'] == 'true':
                #self.associated_concept_freq()
                pass
        return self.response




    def paired_concept_freq(self):
        """
        Iterate over all the edges, check if they're disease, phenotype, or chemical_substance, and do the decorating
        :return: response
        """
        self.response.debug("Computing paired concept frequencies.")
        self.response.info("Overlaying paired concept frequencies utilizing Columbia Open Health Data.")
        self.response.info("Converting CURIE identifiers to human readable names")
        node_curie_to_type = dict()
        try:
            for node in self.message.knowledge_graph.nodes:
                node_curie_to_type[node.id] = node.type  # WARNING: this is a list
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.debug(f"Something went wrong when converting names")

        # Now iterate over all edges in the KG, looking for ones that COHD can handle
        try:
            for edge in self.message.knowledge_graph.edges:
                if not edge.edge_attributes:  # populate if not already there
                    edge.edge_attributes = []
                source_curie = edge.source_id
                target_curie = edge.target_id
                source_type = node_curie_to_type[source_curie]
                target_type = node_curie_to_type[target_curie]

                # figure out which knowledge provider to use
                KP_to_use = None
                for KP in self.who_knows_about_what:
                    if source_type[0] in self.who_knows_about_what[KP]:  # FIXME: source type is a list, will need to look for non-zero intersection
                        if target_type[0] in self.who_knows_about_what[KP]: # FIXME: source type is a list, will need to look for non-zero intersection
                            KP_to_use = KP
                if KP_to_use == 'COHD':
                    # convert identifiers
                    # this will return a list of identifiers, go through and look at all pairs
                    # sum them up
                    # decorate the edge
                    name = "COHD paired concept frequency"
                    type = "float"
                    value = 0.25  # put the actual code in here
                    url = "http://cohd.smart-api.info/"
                    edge_attribute = EdgeAttribute(type=type, name=name, value=value,
                                                      url=url)  # populate the edge attribute
                    edge.edge_attributes.append(edge_attribute)

        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.debug(f"Something went wrong when querying the knowledge provider COHD")
