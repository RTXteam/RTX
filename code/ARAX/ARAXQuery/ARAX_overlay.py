#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
from response import Response
from collections import Counter
import traceback
import itertools

class ARAXOverlay:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'compute_ngd',
            'overlay_clinical_info',
            'compute_jaccard',
            'add_node_pmids',
            'predict_drug_treats_disease',
            'fisher_exact_test'
        }
        self.report_stats = True

    def report_response_stats(self, response):
        """
        Little helper function that will report the KG, QG, and results stats to the debug in the process of executing actions. Basically to help diagnose problems
        """
        message = self.message
        if self.report_stats:
            # report number of nodes and edges, and their type in the QG
            if hasattr(message, 'query_graph') and message.query_graph:
                response.debug(f"Query graph is {message.query_graph}")
            if hasattr(message, 'knowledge_graph') and message.knowledge_graph and hasattr(message.knowledge_graph, 'nodes') and message.knowledge_graph.nodes and hasattr(message.knowledge_graph, 'edges') and message.knowledge_graph.edges:
                response.debug(f"Number of nodes in KG is {len(message.knowledge_graph.nodes)}")
                # This works for KG1 and KG2
                response.debug(f"Number of nodes in KG by type is {Counter([x.type[0] for x in message.knowledge_graph.nodes])}")  # type is a list, just get the first one
                # don't really need to worry about this now
                #response.debug(f"Number of nodes in KG by with attributes are {Counter([x.type for x in message.knowledge_graph.nodes])}")
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(f"Number of edges in KG by type is {Counter([x.type for x in message.knowledge_graph.edges])}")
                response.debug(f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges if x.edge_attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges:
                    if x.edge_attributes:
                        for attr in x.edge_attributes:
                            attribute_names.append(attr.name)
                response.debug(f"Number of edges in KG by attribute {Counter(attribute_names)}")
        return response

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        description_list = []
        for action in self.allowable_actions:
            description_list.append(getattr(self, '_' + self.__class__.__name__ + '__' + action)(describe=True))
        return description_list


    # Write a little helper function to test parameters
    def check_params(self, allowable_parameters):
        """
        Checks to see if the input parameters are allowed
        :param input_parameters: input parameters supplied to ARAXOverlay.apply()
        :param allowable_parameters: the allowable parameters
        :return: None
        """
        for key, item in self.parameters.items():
            if key not in allowable_parameters:
                self.response.error(
                    f"Supplied parameter {key} is not permitted. Allowable parameters are: {list(allowable_parameters.keys())}",
                    error_code="UnknownParameter")
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in allowable_parameters[key]]) or any([type(x) == int for x in allowable_parameters[key]]):  # if it's a float or int, just accept it as it is
                    return
                elif key == "virtual_relation_label" and type(item) == str:
                    return
                else:  # otherwise, it's really not an allowable parameter
                    self.response.error(
                        f"Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}",
                        error_code="UnknownValue")

    # helper function to check if all virtual edge parameters have been properly provided
    def check_virtual_edge_params(self, allowable_parameters):
        parameters = self.parameters
        if any([x in ['virtual_relation_label', 'source_qnode_id', 'target_qnode_id'] for x in parameters.keys()]):
            if not all([x in parameters.keys() for x in ['virtual_relation_label', 'source_qnode_id', 'target_qnode_id']]):
                self.response.error(f"If any of of the following parameters are provided ['virtual_relation_label', 'source_qnode_id', 'target_qnode_id'], all must be provided. Allowable parameters include: {allowable_parameters}")
            elif parameters['source_qnode_id'] not in allowable_parameters['source_qnode_id']:
                self.response.error(f"source_qnode_id value is not valid. Valid values are: {allowable_parameters['source_qnode_id']}")
            elif parameters['target_qnode_id'] not in allowable_parameters['target_qnode_id']:
                self.response.error(f"target_qnode_id value is not valid. Valid values are: {allowable_parameters['target_qnode_id']}")


    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters, response=None):

        #### Define a default response
        if response is None:
            response = Response()
        self.response = response
        self.message = input_message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}", error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            response.error(f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}", error_code="UnknownAction")

        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters['action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        response.debug(f"Applying Overlay to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        # TODO: add_pubmed_ids
        # TODO: compute_confidence_scores
        # TODO: finish COHD
        # TODO: Jaccard

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            response = self.report_response_stats(response)
        return response

    def __compute_ngd(self, describe=False):
        """
        Computes normalized google distance between two nodes connected by an edge in the knowledge graph
        and adds that as an edge attribute.
        Allowable parameters: {default_value: {'0', 'inf'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        #allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'}}
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'}, 'virtual_relation_label': {self.parameters['virtual_relation_label'] if 'virtual_relation_label' in self.parameters else None},
                                    'source_qnode_id': set([x.id for x in self.message.query_graph.nodes]),
                                    'target_qnode_id': set([x.id for x in self.message.query_graph.nodes])
                                    }
        else:
            allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'}, 'virtual_relation_label': {'any string label identifying the virtual edge label (optional, otherwise applied to all existing edges in the KG)'},
                                    'source_qnode_id': {'a specific source query node id (optional, otherwise applied to all edges)'},
                                    'target_qnode_id': {'a specific target query node id (optional, otherwise applied to all edges)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = """
`compute_ngd` computes a metric (called the normalized Google distance) based on edge soure/target node co-occurrence in abstracts of all PubMed articles.
This information is then included as an edge attribute with the name `normalized_google_distance`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the type specified by `virtual_relation_label`.

Use cases include:

* focusing in on edges that are well represented in the literature
* focusing in on edges that are under-represented in the literature

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # set the default value if it's not already done
        if 'default_value' not in parameters:
            parameters['default_value'] = np.inf
        else:
            if parameters['default_value'] == '0':
                parameters['default_value'] = '0'
            else:
                parameters['default_value'] = float("-inf")

        # Check if all virtual edge params have been provided properly
        self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Overlay.compute_ngd import ComputeNGD
        NGD = ComputeNGD(self.response, self.message, parameters)
        response = NGD.compute_ngd()
        return response

    def __overlay_clinical_info(self, describe=False):  # TODO: put the default paramas and all that other goodness in
        """
        This function will apply the action overlay_clinical_info.
        Allowable parameters are:
        :return: a response
        """
        message = self.message
        parameters = self.parameters

        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'overlay_clinical_info'},
                                    'paired_concept_frequency': {'true', 'false'},
                                    'observed_expected_ratio': {'true', 'false'},
                                    'chi_square': {'true', 'false'},
                                    'virtual_relation_label': {self.parameters['virtual_relation_label'] if 'virtual_relation_label' in self.parameters else None},
                                    'source_qnode_id': set([x.id for x in self.message.query_graph.nodes]),
                                    'target_qnode_id': set([x.id for x in self.message.query_graph.nodes])
                                    }
        else:
            allowable_parameters = {'action': {'overlay_clinical_info'},
                                    'paired_concept_frequency': {'true', 'false'},
                                    'observed_expected_ratio': {'true', 'false'},
                                    'chi_square': {'true', 'false'},
                                    'virtual_relation_label': {'any string label used to identify the virtual edge (optional, otherwise information is added as an attribute to all existing edges in the KG)'},
                                    'source_qnode_id': {'a specific source query node id (optional, otherwise applied to all edges)'},
                                    'target_qnode_id': {'a specific target query node id (optional, otherwise applied to all edges)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = """
`overlay_clinical_info` overlay edges with information obtained from the knowledge provider (KP) Columbia Open Health Data (COHD).
This KP has a number of different functionalities, such as `paired_concept_frequency`, `observed_expected_ratio`, etc. which are mutually exclusive DSL parameters.
All information is derived from a 5 year hierarchical dataset: Counts for each concept include patients from descendant concepts. 
This includes clinical data from 2013-2017 and includes 1,731,858 different patients.
This information is then included as an edge attribute.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the relation specified by `virtual_relation_label`.
These virtual edges have the following types:

* `paired_concept_frequency` has the virtual edge type `has_paired_concept_frequency_with`
* `observed_expected_ratio` has the virtual edge type `has_observed_expected_ratio_with`
* `chi_square` has the virtual edge type `has_chi_square_with`

Note that this DSL command has quite a bit of functionality, so a brief description of the DSL parameters is given here:

* `paired_concept_frequency`: If set to `true`, retrieves observed clinical frequencies of a pair of concepts indicated by edge source and target nodes and adds these values as edge attributes.
* `observed_expected_ratio`: If set to `true`, returns the natural logarithm of the ratio between the observed count and expected count of edge source and target nodes. Expected count is calculated from the single concept frequencies and assuming independence between the concepts. This information is added as an edge attribute.
* `chi_square`: If set to `true`, returns the chi-square statistic and p-value between pairs of concepts indicated by edge source/target nodes and adds these values as edge attributes. The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and assuming independence between concepts. P-value is calculated with 1 DOF.
* `virtual_edge_type`: Overlays the requested information on virtual edges (ones that don't exist in the query graph).

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters


        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        #check if conflicting parameters have been provided
        mutually_exclusive_params = {'paired_concept_frequency', 'observed_expected_ratio', 'chi_square'}
        if np.sum([x in mutually_exclusive_params for x in parameters]) > 1:
            self.response.error(f"The parameters {mutually_exclusive_params} are mutually exclusive. Please provide only one for each call to overlay(action=overlay_clinical_info)")
        if self.response.status != 'OK':
            return self.response

        # Check if all virtual edge params have been provided properly
        self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # TODO: make sure that not more than one other kind of action has been asked for since COHD has a lot of functionality #606
        # TODO: make sure conflicting defaults aren't called either, partially completed
        # TODO: until then, just pass the parameters as is

        default_params = parameters  # here is where you can set default values

        from Overlay.overlay_clinical_info import OverlayClinicalInfo
        OCI = OverlayClinicalInfo(self.response, self.message, default_params)
        response = OCI.decorate()  # TODO: refactor this so it's basically another apply() like function # 606
        return response

    def __add_node_pmids(self, describe=False):
        """
        Computes normalized google distance between two nodes connected by an edge in the knowledge graph
        and adds that as an edge attribute.
        Allowable parameters: {max_num: {'all', 'any integer'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        #allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all', int()}}

        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all', int()}}
        else:
            allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all','any integer'}}

        # A little function to describe what this thing does
        if describe:
            brief_description = """
`add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters


        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # Set the default parameters
        pass_params = {'max_num': 100}  # here is where you can set default values

        # parse the input parameters to be the data types I need them to be
        for key, value in self.parameters.items():
            if key == 'max_num':
                if value == 'all':
                    pass_params[key] = None
                else:
                    try:
                        pass_params[key] = int(value)
                    except:
                        tb = traceback.format_exc()
                        error_type, error, _ = sys.exc_info()
                        self.response.error(tb, error_code=error_type.__name__)
                        self.response.error(f"parameter 'max_num' must be an integer")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Overlay.add_node_pmids import AddNodePMIDS
        ANP = AddNodePMIDS(self.response, self.message, pass_params)
        response = ANP.add_node_pmids()
        return response

    def __compute_jaccard(self, describe=False):
        """
        Computes the jaccard distance: starting_node -> {set of intermediate nodes} -> {set of end nodes}.
        for each end node x, looks at (number of intermediate nodes connected to x) / (total number of intermediate nodes).
        Basically, which of the end nodes is connected to many of the intermediate nodes. Adds an edge to the KG with the
        jaccard value, source, and target info as an edge attribute .
        Allowable parameters:
        :return:
        """
        message = self.message
        parameters = self.parameters
        # need two different ones of these since the allowable parameters will depend on the id's that they used
        # TODO: the start_node_id CANNOT be a set
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'compute_jaccard'},
                                'start_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'intermediate_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'end_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'virtual_relation_label': {self.parameters['virtual_relation_label'] if 'virtual_relation_label' in self.parameters else "any_string"}
                                }
        else:
            allowable_parameters = {'action': {'compute_jaccard'},
                                    'start_node_id': {"a node id (required)"},
                                    'intermediate_node_id': {"a query node id (required)"},
                                    'end_node_id': {"a query node id (required)"},
                                    'virtual_relation_label': {"any string label (required) that will be used to identify the virtual edge added"}
                                    }
        # print(allowable_parameters)
        # A little function to describe what this thing does
        if describe:
            brief_description = """
`compute_jaccard` creates virtual edges and adds an edge attribute (with the property name `jaccard_index`) containing the following information:
The jaccard similarity measures how many `intermediate_node_id`'s are shared in common between each `start_node_id` and `target_node_id`.
This is used for purposes such as "find me all drugs (`start_node_id`) that have many proteins (`intermediate_node_id`) in common with this disease (`end_node_id`)."
This can be used for downstream filtering to concentrate on relevant bioentities.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # No default parameters to set

        # in the above allowable_parameters, we've already checked if the node id's exist, so no need to check them

        # now do the call out to NGD
        from Overlay.compute_jaccard import ComputeJaccard
        JAC = ComputeJaccard(self.response, self.message, self.parameters)
        response = JAC.compute_jaccard()
        return response

    def __predict_drug_treats_disease(self, describe=False):
        """
        Utilizes a machine learning model to predict if a given chemical_substance treats a disease or phenotypic_feature
        Allowable parameters:
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'predict_drug_treats_disease'}, 'virtual_relation_label': {self.parameters['virtual_relation_label'] if 'virtual_edge_type' in self.parameters else None},
                                    'source_qnode_id': set([x.id for x in self.message.query_graph.nodes if x.type == "chemical_substance"]),
                                    'target_qnode_id': set([x.id for x in self.message.query_graph.nodes if (x.type == "disease" or x.type == "phenotypic_feature")])
                                    }
        else:
            allowable_parameters = {'action': {'predict_drug_treats_disease'}, 'virtual_relation_label': {'optional: any string label that identifies the virtual edges added (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'},
                                    'source_qnode_id': {'optional: a specific source query node id corresponding to a disease query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'},
                                    'target_qnode_id': {'optional: a specific target query node id corresponding to a disease or phenotypic_feature query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = """
`predict_drug_treats_disease` utilizes a machine learning model (trained on KP ARAX/KG1) to assign a probability that a given drug/chemical_substanct treats a disease/phenotypic feature.
For more information about how this model was trained and how it performs, please see [this publication](https://doi.org/10.1101/765305).
The drug-disease treatment prediction probability is included as an edge attribute (with the attribute name `probability_treats`).
You have the choice of applying this to all appropriate edges in the knowledge graph, or only between specified source/target qnode id's (make sure one is a chemical_substance, and the other is a disease or phenotypic_feature). 
If the later, virtual edges are added with the relation specified by `virtual_edge_type` and the type `probably_treats`.
Use cases include:

* Overlay drug the probability of any drug in your knowledge graph treating any disease via `overlay(action=predict_drug_treats_disease)`
* For specific drugs and diseases/phenotypes in your graph, add the probability that the drug treats them with something like `overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)`
* Subsequently remove low-probability treating drugs with `overlay(action=predict_drug_treats_disease)` followed by `filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=.6, remove_connected_nodes=t, qnode_id=n02)`

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response
        # Check if all virtual edge params have been provided properly
        self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Overlay.predict_drug_treats_disease import PredictDrugTreatsDisease
        PDTD = PredictDrugTreatsDisease(self.response, self.message, parameters)
        response = PDTD.predict_drug_treats_disease()
        return response

    def __fisher_exact_test(self, describe=False):

        """
        Computes the the Fisher's Exact Test p-value of the connection between a list of given nodes with specified query id (source_qnode_id eg. 'n01') to their adjacent nodes with specified query id (e.g. target_qnode_id 'n02') in message knowledge graph.
        Allowable parameters:
            :param source_qnode_id: (required) a specific QNode id (you used in add_qnode() in DSL) of source nodes in message KG eg. "n00"
            :param virtual_relation_label: (required) any string to label the relation and query edge id of virtual edge with fisher's exact test p-value eg. 'FET'
            :param target_qnode_id: (required) a specific QNode id (you used in add_qnode() in DSL) of target nodes in message KG. This will specify which node in KG to consider for calculating the Fisher Exact Test, eg. "n01"
            :param rel_edge_id: (optional) a specific QEdge id (you used in add_qedge() in DSL) of edges connected to both source nodes and target nodes in message KG. eg. "e01"
            :param top_n: (optional) an int indicating the top number of the most significant adjacent nodes to return (otherwise all results returned) eg. 10
            :param cutoff: (optional) a float indicating the p-value cutoff to return the results (otherwise all results returned) eg. 0.05
        :return: response
        """

        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        # allowable_parameters = {'action': {'fisher_exact_test'}, 'query_node_label': {...}, 'compare_node_label':{...}}

        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes') and hasattr(message.query_graph, 'edges'):
            allowable_source_qnode_id = list(set(itertools.chain.from_iterable([node.qnode_ids for node in message.knowledge_graph.nodes])))  # flatten these as they are lists of lists now
            allowable_target_qnode_id = list(set(itertools.chain.from_iterable([node.qnode_ids for node in message.knowledge_graph.nodes])))  # flatten these as they are lists of lists now
            allowwable_rel_edge_id = list(set(itertools.chain.from_iterable([edge.qedge_ids for edge in message.knowledge_graph.edges])))  # flatten these as they are lists of lists now
            allowwable_rel_edge_id.append(None)
            # # FIXME: need to generate this from some source as per #780
            # allowable_target_node_type = [None,'metabolite','biological_process','chemical_substance','microRNA','protein',
            #                      'anatomical_entity','pathway','cellular_component','phenotypic_feature','disease','molecular_function']
            # allowable_target_edge_type = [None,'physically_interacts_with','subclass_of','involved_in','affects','capable_of',
            #                      'contraindicated_for','indicated_for','regulates','expressed_in','gene_associated_with_condition',
            #                      'has_phenotype','gene_mutations_contribute_to','participates_in','has_part']

            allowable_parameters = {'action': {'fisher_exact_test'},
                                    'source_qnode_id': allowable_source_qnode_id,
                                    'virtual_relation_label': str(),
                                    'target_qnode_id': allowable_target_qnode_id,
                                    'rel_edge_id': allowwable_rel_edge_id,
                                    'top_n': [None,int()],
                                    'cutoff': [None,float()]
                                    }
        else:
            allowable_parameters = {'action': {'fisher_exact_test'},
                                    'source_qnode_id': {"a specific QNode id of source nodes in message KG (required), eg. 'n00'"},
                                    'virtual_relation_label': {"any string to label the relation and query edge id of virtual edge with fisher's exact test p-value (required) eg. 'FET'"},
                                    'target_qnode_id': {"a specific QNode id of target nodes in message KG. This will specify which node in KG to consider for calculating the Fisher Exact Test (required), eg. 'n01'"},
                                    'rel_edge_id': {"a specific QEdge id of edges connected to both source nodes and target nodes in message KG (optional, otherwise all edges connected to both source nodes and target nodes in message KG are considered), eg. 'e01'"},
                                    'top_n': {"an int indicating the top number (the smallest) of p-values to return (optional,otherwise all results returned), eg. 10"},
                                    'cutoff': {"a float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05"}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = """
`fisher_exact_test` computes the the Fisher's Exact Test p-values of the connection between a list of given nodes with specified query id (source_qnode_id eg. 'n01') to their adjacent nodes with specified query id (e.g. target_qnode_id 'n02') in the message knowledge graph. 
This information is then added as an edge attribute to a virtual edge which is then added to the query graph and knowledge graph.
It can also allow you filter out the user-defined insignificance of connections based on a specified p-value cutoff or return the top n smallest p-value of connections and only add their corresponding virtual edges to the knowledge graph.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).

Use cases include:

* Given an input list (or a single) bioentities with specified query id in message KG, find connected bioentities  that are most "representative" of the input list of bioentities
* Find biological pathways that are enriched for an input list of proteins (specified with a query id)
* Make long query graph expansions in a targeted fashion to reduce the combinatorial explosion experienced with long query graphs 

This p-value is calculated from fisher's exact test based on the contingency table with following format:

|||||
|-----|-----|-----|-----|
|                                  | in query node list | not in query node list | row total |
| connect to certain adjacent node |         a          |           b            |   a+b     |
| not connect to adjacent node     |         c          |           d            |   c+d     |
|         column total             |        a+c         |          b+d           |  a+b+c+d  |
    
The p-value is calculated by applying fisher_exact method of scipy.stats module in scipy package to the contingency table.
The code is as follows:

```
 _, pvalue = stats.fisher_exact([[a, b], [c, d]])
```

"""
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # now do the call out to FTEST
        from Overlay.fisher_exact_test import ComputeFTEST
        FTEST = ComputeFTEST(self.response, self.message, self.parameters)
        response = FTEST.fisher_exact_test()
        return response

##########################################################################################
def main():
    print("start ARAX_overlay")
    #### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = Response()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()

    #### Set a simple list of actions
    #actions_list = [
    #    "overlay(compute_confidence_scores=true)",
    #    "return(message=true,store=false)"
    #]

    actions_list = [
        #"overlay(action=compute_ngd)",
        #"overlay(action=compute_ngd, virtual_edge_type=NGD1, source_qnode_id=n00, target_qnode_id=n01)",
        #"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        # "overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_edge_type=P1, source_qnode_id=n00, target_qnode_id=n01)",
        #"overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
        #"overlay(action=add_node_pmids)",
        #"overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        #"overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_edge_type=P1, source_qnode_id=n00, target_qnode_id=n01)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n01, target_qnode_id=n00, virtual_edge_type=P1)",
        "return(message=true,store=false)"
    ]

    #### Parse the action_list and print the result
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()

    #message_dict = araxdb.getMessage(2)  # acetaminophen2proteins graph
    # message_dict = araxdb.getMessage(13)  # ibuprofen -> proteins -> disease # work computer
    #message_dict = araxdb.getMessage(14)  # pleuropneumonia -> phenotypic_feature # work computer
    #message_dict = araxdb.getMessage(16)  # atherosclerosis -> phenotypic_feature  # work computer
    #message_dict = araxdb.getMessage(5)  # atherosclerosis -> phenotypic_feature  # home computer
    #message_dict = araxdb.getMessage(10)
    #message_dict = araxdb.getMessage(36)  # test COHD obs/exp, via ARAX_query.py 16
    #message_dict = araxdb.getMessage(39)  # ngd virtual edge test
    message_dict = araxdb.getMessage(1)

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))

    #### Create an overlay object and use it to apply action[0] from the list
    print("Applying action")
    overlay = ARAXOverlay()
    result = overlay.apply(message, actions[0]['parameters'])
    response.merge(result)
    print("Finished applying action")

    #if result.status != 'OK':
    #    print(response.show(level=Response.DEBUG))
    #    return response
    #response.data = result.data

    #### If successful, show the result
    #print(response.show(level=Response.DEBUG))
    #response.data['message_stats'] = { 'n_results': message.n_results, 'id': message.id,
    #    'reasoner_id': message.reasoner_id, 'tool_version': message.tool_version }
    #response.data['message_stats']['confidence_scores'] = []
    #for result in message.results:
    #    response.data['message_stats']['confidence_scores'].append(result.confidence)

    #print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    #print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))
    # a comment on the end so you can better see the network on github

    # look at the response
    #print(response.show(level=Response.DEBUG))
    #print(response.show())
    #print("Still executed")

    # look at the edges
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)),sort_keys=True,indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message)), sort_keys=True, indent=2))
    #print(response.show(level=Response.DEBUG))

    # just print off the values
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    #for edge in message.knowledge_graph.edges:
    #    if hasattr(edge, 'edge_attributes') and edge.edge_attributes and len(edge.edge_attributes) >= 1:
    #        print(edge.edge_attributes.pop().value)
    #print(f"Message: {json.dumps(ast.literal_eval(repr(message)), sort_keys=True, indent=2)}")
    #print(message)
    print(f"KG edges: {json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2)}")
    #print(response.show(level=Response.DEBUG))
    print("Yet you still got here")
    #print(actions_parser.parse(actions_list))

if __name__ == "__main__": main()
