# This class will overlay the clinical information we have on hand
#!/bin/env python3
import sys
import os
import traceback
import numpy as np
import itertools
from datetime import datetime

import random
import time
random.seed(time.time())

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
# FIXME:^ this should be pulled from a YAML file pointing to the parser
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../KnowledgeSources/COHD_local/scripts/")
from COHDIndex import COHDIndex
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../BiolinkHelper/")
from biolink_helper import BiolinkHelper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou


# TODO: boy howdy this can be modularized quite a bit. Since COHD and other clinical KP's will be adding edge attributes and/or edges, should pull out functions to easy their addition.


class OverlayClinicalInfo:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.parameters = params
        self.who_knows_about_what = {'COHD': ['small_molecule', 'phenotypic_feature', 'disease', 'drug',
                                                'biolink:SmallMolecule', 'biolink:PhenotypicFeature', 'biolink:Disease', 'biolink:Drug']}  # FIXME: replace this with information about the KP's, KS's, and their API's
        self.node_curie_to_type = dict()
        self.biolink_helper = BiolinkHelper()
        self.global_iter = 0
        try:
            self.cohdIndex = COHDIndex()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Internal Error encountered connecting to the local COHD database.")

    def decorate(self):
        """
        Main decorator: looks at parameters and figures out which subroutine to farm out to
        :param parameters:
        :return: response object
        """
        # First, make a dictionary between node curie and type to make sure we're only looking at edges we can handle
        self.response.info("Converting CURIE identifiers to human readable names")
        try:
            for key, node in self.message.knowledge_graph.nodes.items():
                self.node_curie_to_type[key] = node.categories  # WARNING: this is a list
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when converting names")
            return self.response

        parameters = self.parameters
        if 'paired_concept_frequency' in parameters:
            if parameters['paired_concept_frequency'] == 'true':
                self.paired_concept_frequency()
                # TODO: should I return the response and merge, or is it passed by reference and just return at the end?
        if 'associated_concept_freq' in parameters:
            if parameters['associated_concept_freq'] == 'true':
                #self.associated_concept_freq()  # TODO: make this function, and all the other COHD functions too
                pass
        if 'chi_square' in parameters:
            if parameters['chi_square'] == 'true':
                self.chi_square()  # TODO: make this function, and all the other COHD functions too
                pass
        if 'observed_expected_ratio' in parameters:
            if parameters['observed_expected_ratio'] == 'true':
                self.observed_expected_ratio()  # TODO: make this function, and all the other COHD functions too
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

    def make_edge_attribute_from_curies(self, subject_curie, object_curie, subject_name="", object_name="", default=0., name=""):
        """
        Generic function to make an edge attribute
        :subject_curie: CURIE of the subject node for the edge under consideration
        :object_curie: CURIE of the object node for the edge under consideration
        :subject_name: text name of the subject node (in case the KP doesn't understand the CURIE)
        :object: text name of the object node (in case the KP doesn't understand the CURIE)
        :default: default value of the edge attribute
        :name: name of the KP functionality you want to apply
        """
        try:
            # edge attributes
            name = name
            type = "EDAM:data_0951"
            url = "http://cohd.smart-api.info/"
            value = default

            node_curie_to_type = self.node_curie_to_type
            subject_type = node_curie_to_type[subject_curie]
            object_type = node_curie_to_type[object_curie]
            # figure out which knowledge provider to use  # TODO: should handle this in a more structured fashion, does there exist a standardized KP API format?
            KP_to_use = None
            for KP in self.who_knows_about_what:
                # see which KP's can label both subjects of information
                if self.in_common(self.biolink_helper.get_descendants(subject_type, include_mixins=False), self.who_knows_about_what[KP]) and self.in_common(self.biolink_helper.get_descendants(object_type, include_mixins=False), self.who_knows_about_what[KP]):
                    KP_to_use = KP

            if KP_to_use == 'COHD':
                self.response.debug(f"Querying Columbia Open Health data for info about {subject_name} and {object_name}")
                # convert CURIE to OMOP identifiers
                # subject_OMOPs = [str(x['omop_standard_concept_id']) for x in COHD.get_xref_to_OMOP(subject_curie, 1)]
                res = self.mapping_curie_to_omop_ids[subject_curie]
                if len(res) != 0:
                    subject_OMOPs = res
                else:
                    subject_OMOPs = []
                # object_OMOPs = [str(x['omop_standard_concept_id']) for x in COHD.get_xref_to_OMOP(object_curie, 1)]
                res = self.mapping_curie_to_omop_ids[object_curie]
                if len(res) != 0:
                    object_OMOPs = res
                else:
                    object_OMOPs = []
                # for domain in ["Condition", "Drug", "Procedure"]:
                #     subject_OMOPs.update([str(x['concept_id']) for x in COHD.find_concept_ids(subject_name, domain=domain, dataset_id=3)])
                #     object_OMOPs.update([str(x['concept_id']) for x in COHD.find_concept_ids(object_name, domain=domain, dataset_id=3)])
                #################################################
                # FIXME: this was the old way
                # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                # if subject_curie.split('.')[0] == 'CHEMBL':
                #     subject_OMOPs = [str(x['concept_id']) for x in
                #                     COHD.find_concept_ids(subject_name, domain="Drug", dataset_id=3)]
                # if object_curie.split('.')[0] == 'CHEMBL':
                #     object_OMOPs = [str(x['concept_id']) for x in
                #                     COHD.find_concept_ids(object_name, domain="Drug", dataset_id=3)]

                # uniquify everything
                # subject_OMOPs = list(set(subject_OMOPs))
                # object_OMOPs = list(set(object_OMOPs))

                # Decide how to handle the response from the KP
                if name == 'paired_concept_frequency':
                    # sum up all frequencies  #TODO check with COHD people to see if this is kosher
                    frequency = default
                    # for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs):
                    #     freq_data_list = self.cohdIndex.get_paired_concept_freq(omop1, omop2, 3) # use the hierarchical dataset
                    #     if len(freq_data_list) != 0:
                    #         freq_data = freq_data_list[0]
                    #         temp_value = freq_data['concept_frequency']
                    #         if temp_value > frequency:
                    #             frequency = temp_value
                    omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs)]
                    if len(omop_pairs) != 0:
                        res = self.cohdIndex.get_paired_concept_freq(concept_id_pair=omop_pairs, dataset_id=3)  # use the hierarchical dataset
                        if len(res) != 0:
                            maximum_concept_frequency = res[0]['concept_frequency']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                            frequency = maximum_concept_frequency
                    # decorate the edges
                    value = frequency

                elif name == 'observed_expected_ratio':
                    # should probably take the largest obs/exp ratio  # TODO: check with COHD people to see if this is kosher
                    # FIXME: the ln_ratio can be negative, so I should probably account for this, but the object model doesn't like -np.inf
                    value = float("-inf")  # FIXME: unclear in object model if attribute type dictates value type, or if value always needs to be a string

                    ###############################
                    # The following code was an experiment to see if it would speed things up, leaving it out for now since it's difficult to quantify if it does speed things up given the cacheing
                    #if len(subject_OMOPs) < len(object_OMOPs):
                    #    for omop1 in subject_OMOPs:
                    #        omop_to_ln_ratio = dict()
                    #        response = COHD.get_obs_exp_ratio(omop1, domain="", dataset_id=3)  # use the hierarchical dataset
                    #        if response:
                    #            for res in response:
                    #                omop_to_ln_ratio[str(res['concept_id_2'])] = res['ln_ratio']
                    #        for omop2 in object_OMOPs:
                    #            if omop2 in omop_to_ln_ratio:
                    #                temp_value = omop_to_ln_ratio[omop2]
                    #                if temp_value > value:
                    #                    value = temp_value
                    #else:
                    #    for omop1 in object_OMOPs:
                    #        omop_to_ln_ratio = dict()
                    #        response = COHD.get_obs_exp_ratio(omop1, domain="", dataset_id=3)  # use the hierarchical dataset
                    #        if response:
                    #            for res in response:
                    #                omop_to_ln_ratio[str(res['concept_id_2'])] = res['ln_ratio']
                    #        for omop2 in subject_OMOPs:
                    #            if omop2 in omop_to_ln_ratio:
                    #                temp_value = omop_to_ln_ratio[omop2]
                    #                if temp_value > value:
                    #                    value = temp_value
                    ###################################

                    # for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs):
                    #     #print(f"{omop1},{omop2}")
                    #     response = self.cohdIndex.get_obs_exp_ratio(omop1, concept_id_2=omop2, domain="", dataset_id=3)  # use the hierarchical dataset
                    #     # response is a list, since this function is overloaded and can omit concept_id_2, take the first element
                    #     if response and 'ln_ratio' in response[0]:
                    #         temp_val = response[0]['ln_ratio']
                    #         if temp_val > value:
                    #             value = temp_val
                    omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs)]
                    if len(omop_pairs) != 0:
                        res = self.cohdIndex.get_obs_exp_ratio(concept_id_pair=omop_pairs, domain="", dataset_id=3)  # use the hierarchical dataset
                        if len(res) != 0:
                            maximum_ln_ratio = res[0]['ln_ratio']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                            value = maximum_ln_ratio

                elif name == 'chi_square':
                    value = float("inf")
                    # for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs):
                    #     response = self.cohdIndex.get_chi_square(omop1, concept_id_2=omop2, domain="", dataset_id=3)  # use the hierarchical dataset
                    #     # response is a list, since this function is overloaded and can omit concept_id_2, take the first element
                    #     if response and 'p-value' in response[0]:
                    #         temp_val = response[0]['p-value']
                    #         if temp_val < value:  # looking at p=values, so lower is better
                    #             value = temp_val
                    omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(subject_OMOPs, object_OMOPs)]
                    if len(omop_pairs) != 0:
                        res = self.cohdIndex.get_chi_square(concept_id_pair=omop_pairs, domain="", dataset_id=3)  # use the hierarchical dataset
                        if len(res) != 0:
                            minimum_pvalue = res[0]['p-value']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                            value = minimum_pvalue

                # create the edge attribute
                edge_attribute = EdgeAttribute(attribute_type_id=type, original_attribute_name=name, value=str(value), value_url=url)  # populate the edge attribute # FIXME: unclear in object model if attribute type dictates value type, or if value always needs to be a string
                return edge_attribute
            else:
                return None
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when adding the edge attribute from {KP_to_use}.")

    def add_virtual_edge(self, name="", default=0.):
        """
        Generic function to add a virtual edge to the KG an QG
        :name: name of the functionality of the KP to use
        """
        parameters = self.parameters
        subject_curies_to_decorate = set()
        object_curies_to_decorate = set()
        curies_to_names = dict()  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
        # identify the nodes that we should be adding virtual edges for
        for key, node in self.message.knowledge_graph.nodes.items():
            if hasattr(node, 'qnode_keys'):
                if parameters['subject_qnode_key'] in node.qnode_keys:
                    subject_curies_to_decorate.add(key)
                    curies_to_names[key] = node.name  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
                if parameters['object_qnode_key'] in node.qnode_keys:
                    object_curies_to_decorate.add(key)
                    curies_to_names[key] = node.name  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
        added_flag = False  # check to see if any edges where added
        # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute

        ## call COHD api one time to save time
        curies_to_decorate = set()
        curies_to_decorate.update(subject_curies_to_decorate)
        curies_to_decorate.update(object_curies_to_decorate)
        self.mapping_curie_to_omop_ids = self.cohdIndex.get_concept_ids(curies_to_decorate)
        for (subject_curie, object_curie) in itertools.product(subject_curies_to_decorate, object_curies_to_decorate):
            # create the edge attribute if it can be
            edge_attribute = self.make_edge_attribute_from_curies(subject_curie, object_curie,
                                                                  subject_name=curies_to_names[subject_curie],
                                                                  object_name=curies_to_names[object_curie],
                                                                  default=default,
                                                                  name=name)
            if edge_attribute:
                added_flag = True
                # make the edge, add the attribute

                # edge properties
                now = datetime.now()
                edge_type = f"biolink:has_real_world_evidence_of_association_with"
                qedge_keys = [parameters['virtual_relation_label']]
                relation = parameters['virtual_relation_label']
                is_defined_by = "ARAX"
                defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                provided_by = "infores:arax"
                confidence = None
                weight = None  # TODO: could make the actual value of the attribute
                subject_key = subject_curie
                object_key = object_curie

                # now actually add the virtual edges in
                id = f"{relation}_{self.global_iter}"
                # ensure the id is unique
                # might need to change after expand is implemented for TRAPI 1.0
                while id in self.message.knowledge_graph.edges:
                    id = f"{relation}_{self.global_iter}.{random.randint(10**(9-1), (10**9)-1)}"
                self.global_iter += 1
                edge_attribute_list = [
                    edge_attribute,
                    EdgeAttribute(original_attribute_name="virtual_relation_label", value=relation, attribute_type_id="biolink:Unknown"),
                    #EdgeAttribute(original_attribute_name="is_defined_by", value=is_defined_by, attribute_type_id="biolink:Unknown"),
                    EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                    EdgeAttribute(original_attribute_name="provided_by", value=provided_by, attribute_type_id="biolink:aggregator_knowledge_source", attribute_source=provided_by, value_type_id="biolink:InformationResource"),
                    EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="biolink:computed_value", attribute_source="infores:arax-reasoner-ara", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
                    #EdgeAttribute(name="confidence", value=confidence, type="biolink:ConfidenceLevel"),
                    #EdgeAttribute(name="weight", value=weight, type="metatype:Float"),
                    #EdgeAttribute(name="qedge_ids", value=qedge_ids)
                ]
                # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key,
                #             object_key=object_key,
                #             is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                #             provided_by=provided_by,
                #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)
                edge = Edge(predicate=edge_type, subject=subject_key, object=object_key,
                                attributes=edge_attribute_list)
                edge.qedge_keys = qedge_keys
                self.message.knowledge_graph.edges[id] = edge
                if self.message.results is not None and len(self.message.results) > 0:
                    ou.update_results_with_overlay_edge(subject_knode_key=subject_key, object_knode_key=object_key, kedge_key=id, message=self.message, log=self.response)

        # Now add a q_edge the query_graph since I've added an extra edge to the KG
        if added_flag:
            edge_type = f"biolink:has_real_world_evidence_of_association_with"
            relation = parameters['virtual_relation_label']
            qedge_keys = [parameters['virtual_relation_label']]
            subject_qnode_key = parameters['subject_qnode_key']
            object_qnode_key = parameters['object_qnode_key']
            option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
                                                                      self.message.query_graph, self.response)
            # q_edge = QEdge(id=relation, type=edge_type, relation=relation,
            #                subject_key=subject_qnode_key, object_key=object_qnode_key,
            #                option_group_id=option_group_id)  # TODO: ok to make the id and type the same thing?
            q_edge = QEdge(predicates=edge_type, subject=subject_qnode_key,
                           object=object_qnode_key, option_group_id=option_group_id)
            q_edge.relation = relation
            self.message.query_graph.edges[relation]=q_edge

    def add_all_edges(self, name="", default=0.):
        curies_to_names = dict()
        all_curie_set = set()
        for key, node in self.message.knowledge_graph.nodes.items():
            curies_to_names[key] = node.name
            all_curie_set.add(key)
        self.mapping_curie_to_omop_ids = self.cohdIndex.get_concept_ids(all_curie_set)
        for edge in self.message.knowledge_graph.edges.values():
            if not edge.attributes:  # populate if not already there
                edge.attributes = []
            subject_curie = edge.subject
            object_curie = edge.object
            edge_attribute = self.make_edge_attribute_from_curies(subject_curie, object_curie,
                                                                  subject_name=curies_to_names[subject_curie],
                                                                  object_name=curies_to_names[object_curie],
                                                                  default=default,
                                                                  name=name)  # FIXME: Super hacky way to get around the fact that COHD can't map CHEMBL drugs
            if edge_attribute:  # make sure an edge attribute was actually created
                edge.attributes.append(edge_attribute)

    def paired_concept_frequency(self, default=0):
        """
        calulate paired concept frequency.
        Retrieves observed clinical frequencies of a pair of concepts.
        :return: response
        """
        parameters = self.parameters
        self.response.debug("Computing paired concept frequencies.")
        self.response.info("Overlaying paired concept frequencies utilizing Columbia Open Health Data. This calls an external knowledge provider and may take a while")

        # Now add the edges or virtual edges
        try:
            if 'virtual_relation_label' in parameters:
                self.add_virtual_edge(name="paired_concept_frequency", default=default)
            else:  # otherwise, just add to existing edges in the KG
                self.add_all_edges(name="paired_concept_frequency", default=default)

        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when overlaying clinical info")

    def observed_expected_ratio(self, default=0):
        """
        Returns the natural logarithm of the ratio between the observed count and expected count.
        Expected count is calculated from the single concept frequencies and assuming independence between the concepts.
        Results are returned as maximum over all ln_ratios matching to OMOP concept id.
        """
        parameters = self.parameters
        self.response.debug("Computing observed expected ratios.")
        self.response.info("Overlaying observed expected ratios utilizing Columbia Open Health Data. This calls an external knowledge provider and may take a while")

        # Now add the edges or virtual edges
        try:
            if 'virtual_relation_label' in parameters:
                self.add_virtual_edge(name="observed_expected_ratio", default=default)
            else:  # otherwise, just add to existing edges in the KG
                self.add_all_edges(name="observed_expected_ratio", default=default)

        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when overlaying clinical info")


    def chi_square(self, default=float("inf")):
        """
        Returns the chi-square statistic and p-value between pairs of concepts. Results are returned in descending order of the chi-square statistic. Note that due to large sample sizes, the chi-square can become very large.
        The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and assuming independence between concepts. P-value is calculated with 1 DOF.
        """
        parameters = self.parameters
        self.response.debug("Computing Chi square p-values.")
        self.response.info("Overlaying Chi square p-values utilizing Columbia Open Health Data. This calls an external knowledge provider and may take a while")

        # Now add the edges or virtual edges
        try:
            if 'virtual_relation_label' in parameters:
                self.add_virtual_edge(name="chi_square", default=default)
            else:  # otherwise, just add to existing edges in the KG
                self.add_all_edges(name="chi_square", default=default)

        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong when overlaying clinical info")
