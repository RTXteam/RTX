# This class will overlay the clinical information we have on hand
#!/bin/env python3
import sys
import os
import traceback
import numpy as np
import itertools
# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from QueryCOHD import QueryCOHD as COHD
# FIXME:^ this should be pulled from a YAML file pointing to the parser


class OverlayClinicalInfo:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.parameters = params
        self.who_knows_about_what = {'COHD': ['chemical_substance', 'phenotypic_feature', 'disease']}  # FIXME: replace this with information about the KP's, KS's, and their API's

    def decorate(self):
        """
        Main decorator: looks at parameters and figures out which subroutine to farm out to
        :param parameters:
        :return: response object
        """
        parameters = self.parameters
        if 'paired_concept_freq' in parameters:
            if parameters['paired_concept_freq'] == 'true':
                self.paired_concept_freq()
                # TODO: should I return the response and merge, or is it passed by reference and just return at the end?
        if 'associated_concept_freq' in parameters:
            if parameters['associated_concept_freq'] == 'true':
                #self.associated_concept_freq()  # TODO: make this function, and all the other COHD functions too
                pass
        if 'chi_square' in parameters:
            if parameters['chi_square'] == 'true':
                #self.chi_square()  # TODO: make this function, and all the other COHD functions too
                pass
        if 'observed_expected_ratio' in parameters:
            if parameters['observed_expected_ratio'] == 'true':
                #self.observed_expected_ratio()  # TODO: make this function, and all the other COHD functions too
                pass
        if 'relative_frequency' in parameters:
            if parameters['relative_frequency'] == 'true':
                #self.associated_concept_freq()  # TODO: make this function, and all the other COHD functions too
                pass

        return self.response

    def in_common(self, list1, list2):
        """
        Helper function that returns true iff list1 and list2 have any elements in common
        :param list1: a list of strings (intended to be biolink node types)
        :param list2: another list of strings (intended to be biolink node types)
        :return: True/False if they share an element in common
        """
        if set(list1).intersection(set(list2)):
            return True
        else:
            return False


    def paired_concept_freq(self, default=0):
        """
        Iterate over all the edges, check if they're disease, phenotype, or chemical_substance, and do the decorating
        #TODO: since CURIES map to many OMOP ids, need to decide how to combine them. For now, add the frequencies
        :return: response
        """
        who_knows_about_what = self.who_knows_about_what
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
            self.response.error(f"Something went wrong when converting names")

        # Now iterate over all edges in the KG, looking for ones that COHD can handle
        try:
            for edge in self.message.knowledge_graph.edges:
                if not edge.edge_attributes:  # populate if not already there
                    edge.edge_attributes = []
                source_curie = edge.source_id
                target_curie = edge.target_id
                source_type = node_curie_to_type[source_curie]
                target_type = node_curie_to_type[target_curie]
                # figure out which knowledge provider to use  # TODO: should handle this in a more structured fashion, does there exist a standardized KP API format?
                KP_to_use = None
                for KP in self.who_knows_about_what:
                    # see which KP's can label both sources of information
                    if self.in_common(source_type, who_knows_about_what[KP]) and self.in_common(target_type, who_knows_about_what[KP]):
                            KP_to_use = KP
                if KP_to_use == 'COHD':
                    # convert CURIE to OMOP identifiers
                    source_OMOPs = [str(x['omop_standard_concept_id']) for x in COHD.get_xref_to_OMOP(source_curie, 2)]
                    target_OMOPs = [str(x['omop_standard_concept_id']) for x in COHD.get_xref_to_OMOP(target_curie, 2)]
                    # sum up all frequencies
                    frequncy = default
                    for (omop1, omop2) in itertools.product(source_OMOPs, target_OMOPs):
                        freq_data = COHD.get_paired_concept_freq(omop1, omop2, 3)
                        #self.response.debug(f"{omop1},{omop2}")
                        #self.response.debug(f"{freq_data}")  # just to see what we're getting from COHD
                        if freq_data and 'concept_frequency' in freq_data:
                            frequncy += freq_data['concept_frequency']
                    # decorate the edges
                    name = "paired_concept_frequency"
                    type = "float"
                    value = frequncy
                    url = "http://cohd.smart-api.info/"
                    edge_attribute = EdgeAttribute(type=type, name=name, value=value,
                                                      url=url)  # populate the edge attribute
                    edge.edge_attributes.append(edge_attribute)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when overlaying clinical info")
