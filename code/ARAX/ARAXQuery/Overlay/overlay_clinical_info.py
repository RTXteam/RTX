# This class will overlay the clinical information we have on hand
#!/bin/env python3
import sys
import os
import traceback
import numpy as np
import itertools
from datetime import datetime
# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge import Edge
from swagger_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from QueryCOHD import QueryCOHD as COHD
# FIXME:^ this should be pulled from a YAML file pointing to the parser

# TODO: boy howdy this can be modularized quite a bit. Since COHD and other clinical KP's will be adding edge attributes and/or edges, should pull out functions to easy their addition.


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
        parameters = self.parameters
        who_knows_about_what = self.who_knows_about_what
        self.response.debug("Computing paired concept frequencies.")
        self.response.info("Overlaying paired concept frequencies utilizing Columbia Open Health Data. This calls an external knowledge provider and may take a while")
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

        def make_edge_attribute_from_curies(source_curie, target_curie, source_name="", target_name=""):
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
                # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                if source_curie.split('.')[0] == 'CHEMBL':
                    source_OMOPs = [str(x['concept_id']) for x in COHD.find_concept_ids(source_name, domain="Drug", dataset_id=3)]
                if target_curie.split('.')[0] == 'CHEMBL':
                    target_OMOPs = [str(x['concept_id']) for x in COHD.find_concept_ids(target_name, domain="Drug", dataset_id=3)]
                #print(source_OMOPs)
                #print(target_name)
                # sum up all frequencies
                frequency = default
                for (omop1, omop2) in itertools.product(source_OMOPs, target_OMOPs):
                    freq_data = COHD.get_paired_concept_freq(omop1, omop2, 3)  # us the hierarchical dataset
                    if freq_data and 'concept_frequency' in freq_data:
                        frequency += freq_data['concept_frequency']
                # decorate the edges
                name = "paired_concept_frequency"
                type = "float"
                value = frequency
                url = "http://cohd.smart-api.info/"
                edge_attribute = EdgeAttribute(type=type, name=name, value=value, url=url)  # populate the edge attribute
                return edge_attribute
            else:
                return None

        # Now iterate over all edges in the KG, looking for ones that COHD can handle, or add virtual edges if that's asked for
        try:
            if 'virtual_edge_type' in parameters.keys():  # then we should be adding virtual edges, and adding them to the query graph
                source_curies_to_decorate = set()
                target_curies_to_decorate = set()
                curies_to_names = dict()  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                # identify the nodes that we should be adding virtual edges for
                for node in self.message.knowledge_graph.nodes:
                    if hasattr(node, 'qnode_id'):
                        if node.qnode_id == parameters['source_qnode_id']:
                            source_curies_to_decorate.add(node.id)
                            curies_to_names[node.id] = node.name  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                        if node.qnode_id == parameters['target_qnode_id']:
                            target_curies_to_decorate.add(node.id)
                            curies_to_names[node.id] = node.name  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                added_flag = False  # check to see if any edges where added
                # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute
                for (source_curie, target_curie) in itertools.product(source_curies_to_decorate, target_curies_to_decorate):
                    # create the edge attribute if it can be
                    edge_attribute = make_edge_attribute_from_curies(source_curie, target_curie, source_name=curies_to_names[source_curie], target_name=curies_to_names[target_curie])  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                    if edge_attribute:
                        added_flag = True
                        # make the edge, add the attribute

                        # edge properties
                        iter = 0
                        now = datetime.now()
                        edge_type = parameters['virtual_edge_type']
                        relation = "COHD_paired_concept_frequency"
                        is_defined_by = "https://arax.rtx.ai/api/rtx/v1/ui/"
                        defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                        provided_by = "ARAX/RTX"
                        confidence = 1.0
                        weight = None  # TODO: could make the actual value of the attribute
                        source_id = source_curie
                        target_id = target_curie

                        # now actually add the virtual edges in
                        id = f"edge_type_{iter}"
                        iter += 1
                        edge = Edge(id=id, type=edge_type, relation=relation, source_id=source_id,
                                    target_id=target_id,
                                    is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                                    provided_by=provided_by,
                                    confidence=confidence, weight=weight, edge_attributes=[edge_attribute])
                        self.message.knowledge_graph.edges.append(edge)

                # Now add a q_edge the query_graph since I've added an extra edge to the KG
                if added_flag:
                    edge_type = parameters['virtual_edge_type']
                    relation = "COHD_paired_concept_frequency"
                    q_edge = QEdge(id=edge_type, type=edge_type, relation=relation,
                                   source_id=parameters['source_qnode_id'], target_id=parameters['target_qnode_id'])  # TODO: ok to make the id and type the same thing?
                    self.message.query_graph.edges.append(q_edge)

            else:  # otherwise, just add to existing edges in the KG
                # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                curies_to_names = dict()
                for node in self.message.knowledge_graph.nodes:
                    curies_to_names[node.id] = node.name
                for edge in self.message.knowledge_graph.edges:
                    if not edge.edge_attributes:  # populate if not already there
                        edge.edge_attributes = []
                    source_curie = edge.source_id
                    target_curie = edge.target_id
                    edge_attribute = make_edge_attribute_from_curies(source_curie, target_curie, source_name=curies_to_names[source_curie], target_name=curies_to_names[target_curie])  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                    if edge_attribute:  # make sure an edge attribute was actually created
                        edge.edge_attributes.append(edge_attribute)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when overlaying clinical info")
