#!/bin/env python3
import sys


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


import os
import json
import ast
import re
import numpy as np
from ARAX_response import ARAXResponse
from collections import Counter
import traceback
import itertools

from ARAX_decorator import ARAXDecorator


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
            'fisher_exact_test',
            'overlay_exposures_data'
        }
        self.report_stats = True
        self.decorator = ARAXDecorator()

        # parameter descriptions
        self.default_value_info = {
            'is_required': False,
            'examples': ['0', 'inf'],
            'default': 'inf',
            'type': 'string',
            'description': 'The default value of the normalized Google distance (if its value cannot be determined)'
        }
        self.virtual_relation_label_info = {
            'is_required': False,
            'examples': ['N1', 'N2'],
            'type': 'string',
            'description': 'Any string label identifying the virtual edge label (optional, otherwise applied to all existing edges in the KG)'
        }
        self.subject_qnode_key_info = {
            'is_required': False,
            'examples': ['n00', 'n01'],
            'type': 'string',
            'description': 'A specific subject query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'
        }
        self.object_qnode_key_info = {
            'is_required': False,
            'examples': ['n00', 'n01'],
            'type': 'string',
            'description': 'A specific object query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'
        }
        self.paired_concept_frequency_info = {
            'is_required': False,
            'examples': ['true', 'false'],
            'type': 'boolean',
            'description': "Indicates if you want to use the paired concept frequency option. Mutually exlisive with: " + \
                           "`paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error."
        }
        self.observed_expected_ratio_info = {
            'is_required': False,
            'examples': ['true', 'false'],
            'type': 'boolean',
            'description': "Indicates if you want to use the paired concept frequency option. Mutually exlisive with: " + \
                           "`paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error."
        }
        self.chi_square_info = {
            'is_required': False,
            'examples': ['true', 'false'],
            'type': 'boolean',
            'description': "Indicates if you want to use the paired concept frequency option. Mutually exlisive with: " + \
                           "`paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error."
        }
        self.virtual_relation_label_info = {
            'is_required': False,
            'examples': ['N1', 'J2'],
            'type': 'string',
            'description': "An optional label to help identify the virtual edge in the relation field."
        }
        self.max_num_info = {
            'is_required': False,
            'examples': ['all', 5, 50],
            'type': 'int or string',
            'description': "The maximum number of values to return. Enter 'all' to return everything",
            'default': 100
        }
        self.start_node_key_info = {
            'is_required': True,
            'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'],
            'type': 'string',
            'description': "A curie id specifying the starting node"
        }
        self.intermediate_node_key_info = {
            'is_required': True,
            'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'],
            'type': 'string',
            'description': "A curie id specifying the intermediate node"
        }
        self.end_node_key_info = {
            'is_required': True,
            'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'],
            'type': 'string',
            'description': "A curie id specifying the ending node"
        }
        self.virtual_relation_label_required_info = {
            'is_required': True,
            'examples': ['N1', 'J2', 'FET'],
            'type': 'string',
            'description': "An optional label to help identify the virtual edge in the relation field."
        }
        self.subject_qnode_key_required_info = {
            'is_required': True,
            'examples': ['n00', 'n01'],
            'type': 'string',
            'description': 'A specific subject query node id (required)'
        }
        self.object_qnode_key_required_info = {
            'is_required': True,
            'examples': ['n00', 'n01'],
            'type': 'string',
            'description': 'A specific object query node id (required)'
        }
        self.rel_edge_key_info = {
            'is_required': False,
            'examples': ['e00', 'e01'],
            'type': 'string',
            'description': "A specific QEdge id of edges connected to both subject nodes and object nodes in message KG (optional, otherwise all edges connected to both subject nodes and object nodes in message KG are considered), eg. 'e01'"
        }
        self.COHD_method_info = {
            "is_required": False,
            # "examples": ['paired_concept_frequency', 'observed_expected_ratio', 'chi_square'],
            "enum": ['paired_concept_frequency', 'observed_expected_ratio', 'chi_square'],
            "default": "paired_concept_frequency",
            "type": "string",
            "description": "Which measure from COHD should be considered."
        }
        self.filter_type_info = {
            "is_required": False,
            "examples": ['top_n', 'cutoff', None],
            "enum": ['top_n', 'cutoff', None],
            'type': 'string or None',
            'description': "If `top_n` is set this indicate the top number (the smallest) of p-values will be returned acording to what is specified in the `value` parameter. If `cutoff` is set then this indicates the p-value cutoff should be used to return results acording to what is specified in the `value` parameter. (optional, otherwise all results returned)",
            'default': None,
            'depends_on': 'value'
        }
        self.fet_value_info = {
            "is_required": False,
            "examples": ['all', 0.05, 0.95, 5, 50],
            'type': 'int or float or None',
            'description': "If `top_n` is set for `filter_type` this is an int indicating the top number (the smallest) of p-values to return. If instead `cutoff` is set then this is a float indicating the p-value cutoff to return the results. (optional, otherwise all results returned)",
            'default': None
        }
        self.dtd_threshold_info = {
            "is_required": False,
            "examples": [0.8, 0.95, 0.5],
            'type': 'int or float or None',
            'description': "What cut-off/threshold to use for DTD probability (optional, the default is 0.8)",
            'default': 0.8
        }
        self.dtd_slow_mode_info = {
            "is_required": False,
            "examples": ["True", "False"],
            "enum": ['T', 't', 'True', 'F', 'f', 'False'],
            'type': 'boolean',
            'description': "Whether to call DTD model directly rather than the precomputed DTD database to do a real-time calculation for DTD probability (default is False)",
            'default': "false"
        }

        # descriptions
        self.command_definitions = {
            "compute_ngd": {
                "dsl_command": "overlay(action=compute_ngd)",
                "description": """
`compute_ngd` computes a metric (called the normalized Google distance) based on edge soure/object node co-occurrence in abstracts of all PubMed articles.
This information is then included as an edge attribute with the name `normalized_google_distance`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified subject/object qnode id's. If the later, virtual edges are added with the type specified by `virtual_relation_label`.

Use cases include:

* focusing in on edges that are well represented in the literature
* focusing in on edges that are under-represented in the literature

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
compute_ngd computes a metric (called the normalized Google distance) based on edge soure/object node co-occurrence in abstracts of all PubMed articles.
This information is then included as an edge attribute with the name normalized_google_distance.
You have the choice of applying this to all edges in the knowledge graph, or only between specified subject/object qnode id's. If the later, virtual edges are added with the type specified by virtual_relation_label.
                    """,
                "parameters": {
                    'default_value': self.default_value_info,
                    'virtual_relation_label': self.virtual_relation_label_info,
                    'subject_qnode_key': self.subject_qnode_key_info,
                    'object_qnode_key': self.object_qnode_key_info
                }
            },
            "overlay_clinical_info": {
                "dsl_command": "overlay(action=overlay_clinical_info)",
                "description": """
`overlay_clinical_info` overlay edges with information obtained from the knowledge provider (KP) Columbia Open Health Data (COHD).
This KP has a number of different functionalities, such as `paired_concept_frequency`, `observed_expected_ratio`, etc. which are mutually exclusive DSL parameters.
All information is derived from a 5 year hierarchical dataset: Counts for each concept include patients from descendant concepts. 
This includes clinical data from 2013-2017 and includes 1,731,858 different patients.
This information is then included as an edge attribute.
You have the choice of applying this to all edges in the knowledge graph, or only between specified subject/object qnode id's. If the later, virtual edges are added with the relation specified by `virtual_relation_label`.
These virtual edges have the following types:

* `paired_concept_frequency` has the virtual edge type `has_paired_concept_frequency_with`
* `observed_expected_ratio` has the virtual edge type `has_observed_expected_ratio_with`
* `chi_square` has the virtual edge type `has_chi_square_with`

Note that this DSL command has quite a bit of functionality, so a brief description of the DSL parameters is given here:

* `paired_concept_frequency`: If set to `true`, retrieves observed clinical frequencies of a pair of concepts indicated by edge subject and object nodes and adds these values as edge attributes.
* `observed_expected_ratio`: If set to `true`, returns the natural logarithm of the ratio between the observed count and expected count of edge subject and object nodes. Expected count is calculated from the single concept frequencies and assuming independence between the concepts. This information is added as an edge attribute.
* `chi_square`: If set to `true`, returns the chi-square statistic and p-value between pairs of concepts indicated by edge subject/object nodes and adds these values as edge attributes. The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and assuming independence between concepts. P-value is calculated with 1 DOF.
* `virtual_edge_type`: Overlays the requested information on virtual edges (ones that don't exist in the query graph).

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
overlay_clinical_info overlay edges with information obtained from the knowledge provider (KP) Columbia Open Health Data (COHD).
This KP has a number of different functionalities, such as 'paired_concept_frequency', 'observed_expected_ratio', etc. which are mutually exclusive DSL parameters.
All information is derived from a 5 year hierarchical dataset: Counts for each concept include patients from descendant concepts. 
This includes clinical data from 2013-2017 and includes 1,731,858 different patients.
This information is then included as an edge attribute.
                    """,
                "mutually_exclusive_params": [
                    'paired_concept_frequency',
                    'observed_expected_ratio',
                    'chi_square'
                ],
                "parameters": {
                    'COHD_method': self.COHD_method_info,
                    'virtual_relation_label': self.virtual_relation_label_info,
                    'subject_qnode_key': self.subject_qnode_key_info,
                    'object_qnode_key': self.object_qnode_key_info
                }
            },
            "compute_jaccard": {
                "dsl_command": "overlay(action=compute_jaccard)",
                "description": """
`compute_jaccard` creates virtual edges and adds an edge attribute (with the property name `jaccard_index`) containing the following information:
The jaccard similarity measures how many `intermediate_node_key`'s are shared in common between each `start_node_key` and `object_node_key`.
This is used for purposes such as "find me all drugs (`start_node_key`) that have many proteins (`intermediate_node_key`) in common with this disease (`end_node_key`)."
This can be used for downstream filtering to concentrate on relevant bioentities.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
compute_jaccard creates virtual edges and adds an edge attribute (with the property name 'jaccard_index') containing the following information:
The jaccard similarity measures how many 'intermediate_node_key's are shared in common between each 'start_node_key' and 'object_node_key'.
This is used for purposes such as "find me all drugs ('start_node_key') that have many proteins ('intermediate_node_key') in common with this disease ('end_node_key')."
This can be used for downstream filtering to concentrate on relevant bioentities.
                    """,
                "parameters": {
                    'start_node_key': self.start_node_key_info,
                    'intermediate_node_key': self.intermediate_node_key_info,
                    'end_node_key': self.end_node_key_info,
                    'virtual_relation_label': self.virtual_relation_label_required_info
                }
            },
            "add_node_pmids": {
                "dsl_command": "overlay(action=add_node_pmids)",
                "description": """
`add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
add_node_pmids adds PubMed PMID's as node attributes to each node in the knowledge graph.
This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
either labeling in the metadata or has the MeSH term occurring in the abstract of the article.
                    """,
                "parameters": {
                    'max_num': self.max_num_info
                }
            },
            "predict_drug_treats_disease": {
                "dsl_command": "overlay(action=predict_drug_treats_disease)",
                "description": """
`predict_drug_treats_disease` utilizes a machine learning model (trained on KP ARAX/KG1) to assign a probability that a given drug/chemical_substance treats a disease/phenotypic feature.
For more information about how this model was trained and how it performs, please see [this publication](https://doi.org/10.1101/765305).
The drug-disease treatment prediction probability is included as an edge attribute (with the attribute name `probability_treats`).
You have the choice of applying this to all appropriate edges in the knowledge graph, or only between specified subject/object qnode id's (make sure one is a chemical_substance, and the other is a disease or phenotypic_feature). 
If the later, virtual edges are added with the relation specified by `virtual_edge_type` and the type `probably_treats`.
Use cases include:

* Overlay drug the probability of any drug in your knowledge graph treating any disease via `overlay(action=predict_drug_treats_disease)`
* For specific drugs and diseases/phenotypes in your graph, add the probability that the drug treats them with something like `overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)`
* Subsequently remove low-probability treating drugs with `overlay(action=predict_drug_treats_disease)` followed by `filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=.6, remove_connected_nodes=t, qnode_key=n02)`

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
predict_drug_treats_disease utilizes a machine learning model (trained on KP RTX-KG2C) to assign a probability that a given drug/chemical_substance treats a disease/phenotypic feature.
For more information about how this model was trained and how it performs, please see this publication (https://doi.org/10.1101/765305) for the version trained on KG1 which used node2vec for its
embeddings. The current version uses KG2C; publication in preparation.
The drug-disease treatment prediction probability is included as an edge attribute (with the attribute name 'probability_treats').
You have the choice of applying this to all appropriate edges in the knowledge graph, or only between specified subject/object qnode id's (make sure one is a chemical_substance, and the other is a disease or phenotypic_feature). 
                    """,
                "parameters": {
                    'virtual_relation_label': self.virtual_relation_label_info,
                    'subject_qnode_key': self.subject_qnode_key_info,
                    'object_qnode_key': self.object_qnode_key_info,
                    'threshold': self.dtd_threshold_info,
                    'slow_mode': self.dtd_slow_mode_info
                }
            },
            "fisher_exact_test": {
                "dsl_command": "overlay(action=fisher_exact_test)",
                "description": """
`fisher_exact_test` computes the Fisher's Exact Test p-values of the connection between a list of given nodes with specified query id (subject_qnode_key eg. 'n01') to their adjacent nodes with specified query id (e.g. object_qnode_key 'n02') in the message knowledge graph. 
This information is then added as an edge attribute to a virtual edge which is then added to the query graph and knowledge graph.
It can also allow you to filter out the user-defined insignificance of connections based on a specified p-value cutoff or return the top n smallest p-value of connections and only add their corresponding virtual edges to the knowledge graph.

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
                    """,
                'brief_description': """
fisher_exact_test computes the Fisher's Exact Test p-values of the connection between a list of given nodes with specified query id (subject_qnode_key eg. 'n01') to their adjacent nodes with specified query id (e.g. object_qnode_key 'n02') in the message knowledge graph. 
This information is then added as an edge attribute to a virtual edge which is then added to the query graph and knowledge graph.
It can also allow you to filter out the user-defined insignificance of connections based on a specified p-value cutoff or return the top n smallest p-value of connections and only add their corresponding virtual edges to the knowledge graph.
                    """,
                "parameters": {
                    'subject_qnode_key': self.subject_qnode_key_required_info,
                    'virtual_relation_label': self.virtual_relation_label_required_info,
                    'object_qnode_key': self.object_qnode_key_required_info,
                    'rel_edge_key': self.rel_edge_key_info,
                    'filter_type': self.filter_type_info,
                    'value': self.fet_value_info
                }
            },
            "overlay_exposures_data": {
                "dsl_command": "overlay(action=overlay_exposures_data)",
                "description": """
`overlay_exposures_data` overlays edges with p-values obtained from the ICEES+ (Integrated Clinical and Environmental Exposures Service) knowledge provider.
This information is included in edge attributes with the name `icees_p-value`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified subject/object qnode IDs. If the latter, the data is added in 'virtual' edges with the type `has_icees_p-value_with`.

This can be applied to an arbitrary knowledge graph (i.e. not just those created/recognized by Expander Agent).
                    """,
                'brief_description': """
overlay_exposures_data overlays edges with p-values obtained from the ICEES+ (Integrated Clinical and Environmental Exposures Service) knowledge provider.
This information is included in edge attributes with the name 'icees_p-value'.
                    """,
                "parameters": {
                    'virtual_relation_label': self.virtual_relation_label_info,
                    'subject_qnode_key': self.subject_qnode_key_info,
                    'object_qnode_key': self.object_qnode_key_info
                }
            }
        }

    def report_response_stats(self, response):
        """
        Little helper function that will report the KG, QG, and results stats to the debug in the process of executing actions. Basically to help diagnose problems
        """
        message = self.message
        if self.report_stats:
            # report number of nodes and edges, and their type in the QG
            if hasattr(message, 'query_graph') and message.query_graph:
                response.debug(f"Query graph is {message.query_graph}")
            if hasattr(message, 'knowledge_graph') and message.knowledge_graph and hasattr(message.knowledge_graph,
                                                                                           'nodes') and message.knowledge_graph.nodes and hasattr(
                    message.knowledge_graph, 'edges') and message.knowledge_graph.edges:
                response.debug(f"Number of nodes in KG is {len(message.knowledge_graph.nodes)}")
                # This works for KG1 and KG2
                response.debug(
                    f"Number of nodes in KG by type is {Counter([x.categories[0] for x in message.knowledge_graph.nodes.values() if x.categories])}")  # type is a list, just get the first one
                    #f"Number of nodes in KG by type is {Counter([x for x in message.knowledge_graph.nodes.values()])}")
                # don't really need to worry about this now
                # response.debug(f"Number of nodes in KG by with attributes are {Counter([x.category for x in message.knowledge_graph.nodes.values()])}")
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(
                    f"Number of edges in KG by type is {Counter([x.predicate for x in message.knowledge_graph.edges.values()])}")
                response.debug(
                    f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges.values() if x.attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges.values():
                    if x.attributes:
                        for attr in x.attributes:
                            attribute_names.append(attr.original_attribute_name)
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

    def check_params(self, allowable_parameters):
        # Write a little helper function to test parameters
        """
        Checks to see if the input parameters are allowed
        :param input_parameters: input parameters supplied to ARAXOverlay.apply()
        :param allowable_parameters: the allowable parameters
        :return: None
        """
        # allowable_parameters = self.command_definitions['parameters']
        for key, item in self.parameters.items():
            if key not in allowable_parameters:
                self.response.error(
                    f"Supplied parameter {key} is not permitted. Allowable parameters are: {list(allowable_parameters.keys())}",
                    error_code="UnknownParameter")
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in allowable_parameters[key]]) or any([type(x) == int for x in
                                                                                      allowable_parameters[
                                                                                          key]]):  # if it's a float or int, just accept it as it is
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
        if any([x in ['virtual_relation_label', 'subject_qnode_key', 'object_qnode_key'] for x in parameters.keys()]):
            if not all([x in parameters.keys() for x in
                        ['virtual_relation_label', 'subject_qnode_key', 'object_qnode_key']]):
                self.response.error(
                    f"If any of of the following parameters are provided ['virtual_relation_label', 'subject_qnode_key', 'object_qnode_key'], all must be provided. Allowable parameters include: {allowable_parameters}")
            elif parameters['subject_qnode_key'] not in allowable_parameters['subject_qnode_key']:
                self.response.error(
                    f"subject_qnode_key value is not valid. Valid values are: {allowable_parameters['subject_qnode_key']}")
            elif parameters['object_qnode_key'] not in allowable_parameters['object_qnode_key']:
                self.response.error(
                    f"object_qnode_key value is not valid. Valid values are: {allowable_parameters['object_qnode_key']}")

    #### Top level decision maker for applying filters
    def apply(self, response, input_parameters):

        #### Define a default response
        if response is None:
            response = ARAXResponse()
        self.response = response
        self.message = response.envelope.message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}",
                           error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            response.error(
                f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}",
                error_code="UnknownAction")

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

        response.debug(
            f"Applying Overlay to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        # Don't try to overlay anything if the KG is empty
        message = response.envelope.message
        if not message.knowledge_graph or not message.knowledge_graph.nodes:
            response.debug(f"Nothing to overlay (KG is empty)")
            return response
        # Don't try to overlay anything if any of the specified qnodes aren't fulfilled in the KG
        possible_node_params = {"subject_qnode_key", "object_qnode_key", "start_node_key", "intermediate_node_key",
                                "end_node_key"}
        node_params_to_check = set(self.parameters).intersection(possible_node_params)
        qnode_keys_to_check = {self.parameters[node_param] for node_param in node_params_to_check}
        if not all(any(node for node in message.knowledge_graph.nodes.values() if qnode_key in node.qnode_keys)
                   for qnode_key in qnode_keys_to_check):
            response.debug(f"Nothing to overlay (one or more of the specified qnodes is not fulfilled in the KG)")
            return response

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters[
            'action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

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
        # allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'}}
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'},
                                    'virtual_relation_label': {self.parameters[
                                                                   'virtual_relation_label'] if 'virtual_relation_label' in self.parameters else None},
                                    'subject_qnode_key': set([key for key in self.message.query_graph.nodes.keys()]),
                                    'object_qnode_key': set([key for key in self.message.query_graph.nodes.keys()])
                                    }
        else:
            allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'},
                                    'virtual_relation_label': {
                                        'any string label identifying the virtual edge label (optional, otherwise applied to all existing edges in the KG)'},
                                    'subject_qnode_key': {
                                        'a specific subject query node id (optional, otherwise applied to all edges)'},
                                    'object_qnode_key': {
                                        'a specific object query node id (optional, otherwise applied to all edges)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['compute_ngd']
            return description_dict

        # Make sure only allowable parameters and values have been passed
        # FIXME : this will need to be fixed
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
                parameters['default_value'] = float("inf")

        # Check if all virtual edge params have been provided properly

        # FIXME : this will need to be fixed
        # self.check_virtual_edge_params(allowable_parameters)
        # FW: changing this to only check if subject_qnode_key or object_qnode_key is present
        if 'subject_qnode_key' in parameters or 'object_qnode_key' in parameters:
            self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Overlay.compute_ngd import ComputeNGD
        NGD = ComputeNGD(self.response, self.message, parameters)
        response = NGD.compute_ngd()
        self.decorator.decorate_edges(response, kind="NGD")
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
                                    'COHD_method': {'paired_concept_frequency', 'observed_expected_ratio',
                                                    'chi_square'},
                                    'paired_concept_frequency': {'true', 'false'},
                                    'observed_expected_ratio': {'true', 'false'},
                                    'chi_square': {'true', 'false'},
                                    'virtual_relation_label': {self.parameters[
                                                                   'virtual_relation_label'] if 'virtual_relation_label' in self.parameters else None},
                                    'subject_qnode_key': set([key for key in self.message.query_graph.nodes.keys()]),
                                    'object_qnode_key': set([key for key in self.message.query_graph.nodes.keys()])
                                    }
        else:
            allowable_parameters = {'action': {'overlay_clinical_info'},
                                    'COHD_method': {'paired_concept_frequency', 'observed_expected_ratio',
                                                    'chi_square'},
                                    'paired_concept_frequency': {'true', 'false'},
                                    'observed_expected_ratio': {'true', 'false'},
                                    'chi_square': {'true', 'false'},
                                    'virtual_relation_label': {
                                        'any string label used to identify the virtual edge (optional, otherwise information is added as an attribute to all existing edges in the KG)'},
                                    'subject_qnode_key': {
                                        'a specific subject query node id (optional, otherwise applied to all edges)'},
                                    'object_qnode_key': {
                                        'a specific object query node id (optional, otherwise applied to all edges)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['overlay_clinical_info']
            return description_dict

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # check if conflicting parameters have been provided
        if 'COHD_method' in self.parameters:
            for method in {'paired_concept_frequency', 'observed_expected_ratio', 'chi_square'}:
                self.parameters[method] = 'false'
            self.parameters[parameters['COHD_method']] = 'true'
        elif 'paired_concept_frequency' not in self.parameters and 'observed_expected_ratio' not in self.parameters and 'chi_square' not in self.parameters:
            self.parameters['paired_concept_frequency'] = 'true'
            self.parameters['COHD_method'] = 'paired_concept_frequency'
        else:
            mutually_exclusive_params = {'paired_concept_frequency', 'observed_expected_ratio', 'chi_square'}
            if np.sum([x in mutually_exclusive_params for x in parameters]) > 1:
                self.response.error(
                    f"The parameters {mutually_exclusive_params} are mutually exclusive. Please provide only one for each call to overlay(action=overlay_clinical_info)")
        if self.response.status != 'OK':
            return self.response

        # Check if all virtual edge params have been provided properly
        # self.check_virtual_edge_params(allowable_parameters)
        # FW: changing this to only check if subject_qnode_key or object_qnode_key is present
        if 'subject_qnode_key' in parameters or 'object_qnode_key' in parameters:
            self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # TODO: make sure that not more than one other kind of action has been asked for since COHD has a lot of functionality #606
        # TODO: make sure conflicting defaults aren't called either, partially completed
        # TODO: until then, just pass the parameters as is

        default_params = parameters  # here is where you can set default values

        from Overlay.overlay_clinical_info import OverlayClinicalInfo
        OCI = OverlayClinicalInfo(self.response, self.message, default_params)
        if OCI.response.status != 'OK':
            return OCI.response
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
        # allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all', int()}}

        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all', int()}}
        else:
            allowable_parameters = {'action': {'add_node_pmids'}, 'max_num': {'all', 'any integer'}}

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['add_node_pmids']
            return description_dict

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
        jaccard value, subject, and object info as an edge attribute .
        Allowable parameters:
        :return:
        """
        message = self.message
        parameters = self.parameters
        # need two different ones of these since the allowable parameters will depend on the id's that they used
        # TODO: the start_node_key CANNOT be a set
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'compute_jaccard'},
                                    'start_node_key': set([key for key in self.message.query_graph.nodes.keys()]),
                                    'intermediate_node_key': set(
                                        [key for key in self.message.query_graph.nodes.keys()]),
                                    'end_node_key': set([key for key in self.message.query_graph.nodes.keys()]),
                                    'virtual_relation_label': {self.parameters[
                                                                   'virtual_relation_label'] if 'virtual_relation_label' in self.parameters else "any_string"}
                                    }
        else:
            allowable_parameters = {'action': {'compute_jaccard'},
                                    'start_node_key': {"a node id (required)"},
                                    'intermediate_node_key': {"a query node id (required)"},
                                    'end_node_key': {"a query node id (required)"},
                                    'virtual_relation_label': {
                                        "any string label (required) that will be used to identify the virtual edge added"}
                                    }
        # print(allowable_parameters)
        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['compute_jaccard']
            return description_dict

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
            qg_nodes = message.query_graph.nodes
            allowable_parameters = {'action': {'predict_drug_treats_disease'}, 'virtual_relation_label': {
                self.parameters['virtual_relation_label'] if 'virtual_relation_label' in self.parameters else None},
                                    # 'subject_qnode_key': set([k for k, x in self.message.query_graph.nodes.items() if x.category == "chemical_substance"]),
                                    'subject_qnode_key': set([node_key for node_key in qg_nodes.keys()]),
                                    # allow any query node type, will be handled by predict_drug_treats_disease.py
                                    # 'object_qnode_key': set([k for k, x in self.message.query_graph.nodes.items() if (x.category == "disease" or x.category == "phenotypic_feature")])
                                    'object_qnode_key': set([node_key for node_key in qg_nodes.keys()]),
                                    'threshold': [None, int(), float()],
                                    # allow any query node type, will be handled by predict_drug_treats_disease.py
                                    'slow_mode': ["true", "false", "True", "False", "t", "f", "T", "F"]
                                    }
        else:
            allowable_parameters = {'action': {'predict_drug_treats_disease'}, 'virtual_relation_label': {
                'optional: any string label that identifies the virtual edges added (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'},
                                    'subject_qnode_key': {
                                        'optional: a specific subject query node id corresponding to a disease query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'},
                                    'object_qnode_key': {
                                        'optional: a specific object query node id corresponding to a disease or phenotypic_feature query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'},
                                    'threshold': {
                                        'optional: What cut-off/threshold to use for DTD probability (default is 0.8)'},
                                    'slow_mode': {
                                        'optional: Whether to call DTD model rather than DTD database to do a real-time calculation for DTD probability (default is False)'}
                                    }

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['predict_drug_treats_disease']
            return description_dict

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response
        # Check if all virtual edge params have been provided properly
        # self.check_virtual_edge_params(allowable_parameters)
        # FW: changing this to only check if subject_qnode_key or object_qnode_key is present
        if 'subject_qnode_key' in parameters or 'object_qnode_key' in parameters:
            self.check_virtual_edge_params(allowable_parameters)
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Overlay.predict_drug_treats_disease import PredictDrugTreatsDisease
        PDTD = PredictDrugTreatsDisease(self.response, self.message, parameters)
        if PDTD.response.status != 'OK':
            return PDTD.response
        response = PDTD.predict_drug_treats_disease()
        return response

    def __fisher_exact_test(self, describe=False):

        """
        Computes the the Fisher's Exact Test p-value of the connection between a list of given nodes with specified query key (subject_qnode_key eg. 'n01') to their adjacent nodes with specified query key (e.g. object_qnode_key 'n02') in message knowledge graph.
        Allowable parameters:
            :param subject_qnode_key: (required) a specific QNode key (you used in add_qnode() in DSL) of subject nodes in message KG eg. "n00"
            :param virtual_relation_label: (required) any string to label the relation and query edge id of virtual edge with fisher's exact test p-value eg. 'FET'
            :param object_qnode_key: (required) a specific QNode key (you used in add_qnode() in DSL) of object nodes in message KG. This will specify which node in KG to consider for calculating the Fisher Exact Test, eg. "n01"
            :param rel_edge_key: (optional) a specific QEdge key (you used in add_qedge() in DSL) of edges connected to both subject nodes and object nodes in message KG. eg. "e01"
            :param top_n: (optional) an int indicating the top number of the most significant adjacent nodes to return (otherwise all results returned) eg. 10
            :param cutoff: (optional) a float indicating the p-value cutoff to return the results (otherwise all results returned) eg. 0.05
        :return: response
        """

        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        # allowable_parameters = {'action': {'fisher_exact_test'}, 'query_node_label': {...}, 'compare_node_label':{...}}

        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph,
                                                                                  'nodes') and hasattr(
                message.query_graph, 'edges'):
            qg_nodes = message.query_graph.nodes
            qg_edges = message.query_graph.edges
            allowable_subject_qnode_key = list(
                set([node_key for node_key in qg_nodes.keys()]))  # flatten these as they are lists of lists now
            allowable_object_qnode_key = list(
                set([node_key for node_key in qg_nodes.keys()]))  # flatten these as they are lists of lists now
            allowwable_rel_edge_key = list(
                set([edge_key for edge_key in qg_edges.keys()]))  # flatten these as they are lists of lists now
            allowwable_rel_edge_key.append(None)
            # # FIXME: need to generate this from some subject as per #780
            # allowable_object_node_type = [None,'metabolite','biological_process','chemical_substance','microRNA','protein',
            #                      'anatomical_entity','pathway','cellular_component','phenotypic_feature','disease','molecular_function']
            # allowable_object_edge_type = [None,'physically_interacts_with','subclass_of','involved_in','affects','capable_of',
            #                      'contraindicated_for','indicated_for','regulates','expressed_in','gene_associated_with_condition',
            #                      'has_phenotype','gene_mutations_contribute_to','participates_in','has_part']

            allowable_parameters = {'action': {'fisher_exact_test'},
                                    'subject_qnode_key': allowable_subject_qnode_key,
                                    'virtual_relation_label': str(),
                                    'object_qnode_key': allowable_object_qnode_key,
                                    'rel_edge_key': allowwable_rel_edge_key,
                                    'top_n': [None, int()],
                                    'cutoff': [None, float()],
                                    'filter_type': {'cutoff', 'top_n'},
                                    'value': [None, int(), float()],
                                    }
        else:
            allowable_parameters = {'action': {'fisher_exact_test'},
                                    'subject_qnode_key': {
                                        "a specific QNode key of subject nodes in message KG (required), eg. 'n00'"},
                                    'virtual_relation_label': {
                                        "any string to label the relation and query edge id of virtual edge with fisher's exact test p-value (required) eg. 'FET'"},
                                    'object_qnode_key': {
                                        "a specific QNode key of object nodes in message KG. This will specify which node in KG to consider for calculating the Fisher Exact Test (required), eg. 'n01'"},
                                    'rel_edge_key': {
                                        "a specific QEdge key of edges connected to both subject nodes and object nodes in message KG (optional, otherwise all edges connected to both subject nodes and object nodes in message KG are considered), eg. 'e01'"},
                                    'top_n': {
                                        "an int indicating the top number (the smallest) of p-values to return (optional,otherwise all results returned), eg. 10"},
                                    'cutoff': {
                                        "a float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05"},
                                    'filter_type': {'cutoff', 'top_n'},
                                    'value': {
                                        'If `top_n` is set for `filter_type` this is an int indicating the top number (the smallest) of p-values to return. If instead `cutoff` is set then this is a float indicating the p-value cutoff to return the results. (optional, otherwise all results returned)'},
                                    }

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['fisher_exact_test']
            return description_dict

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if 'filter_type' in self.parameters and 'value' in self.parameters:
            if self.parameters['filter_type'] == 'cutoff':
                self.parameters['cutoff'] = self.parameters['value']
                if 'top_n' in self.parameters:
                    del self.parameters['top_n']
            elif self.parameters['filter_type'] == 'top_n':
                self.parameters['top_n'] = self.parameters['value']
                if type(self.parameters['top_n']) == float:
                    self.response.error(
                        f"Supplied value {self.parameters['top_n']} is not permitted. If 'top_n' is supplied for the 'filter_type' parameter, then the 'value' parameter cannot be a float it must be an integer or None.",
                        error_code="UnknownValue")
                if 'cutoff' in self.parameters:
                    del self.parameters['cutoff']
        if self.response.status != 'OK':
            return self.response

        # now do the call out to FTEST
        from Overlay.fisher_exact_test import ComputeFTEST
        FTEST = ComputeFTEST(self.response, self.message, self.parameters)
        response = FTEST.fisher_exact_test()
        return response

    def __overlay_exposures_data(self, describe=False):
        """
        This function applies the action overlay_exposures_data. It adds ICEES+ p-values either as virtual edges (if
        the virtual_relation_label, subject_qnode_key, and object_qnode_key are provided) or as EdgeAttributes tacked onto
        existing edges in the knowledge graph (applied to all edges).
        return: ARAXResponse
        """
        message = self.message
        parameters = self.parameters
        response = self.response

        # Make a list of the allowable parameters and their possible values
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'overlay_exposures_data'},
                                    'virtual_relation_label': {self.parameters.get('virtual_relation_label')},
                                    'subject_qnode_key': {key for key in self.message.query_graph.nodes.keys()},
                                    'object_qnode_key': {key for key in self.message.query_graph.nodes.keys()}}
        else:
            allowable_parameters = {'action': {'overlay_exposures_data'},
                                    'virtual_relation_label': {
                                        'any string label used to identify the virtual edge (optional, otherwise information is added as an attribute to all existing edges in the KG)'},
                                    'subject_qnode_key': {
                                        'a specific subject query node id (optional, otherwise applied to all edges)'},
                                    'object_qnode_key': {
                                        'a specific object query node id (optional, otherwise applied to all edges)'}}

        # A little function to describe what this thing does
        if describe:
            description_dict = self.command_definitions['overlay_exposures_data']
            return description_dict

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        if response.status != 'OK':
            return response

        from Overlay.overlay_exposures_data import OverlayExposuresData
        oed = OverlayExposuresData(response, message, parameters)
        response = oed.overlay_exposures_data()
        return response


##########################################################################################
def main():
    print("start ARAX_overlay")
    #### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = ARAXResponse()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()

    #### Set a simple list of actions
    # actions_list = [
    #    "overlay(compute_confidence_scores=true)",
    #    "return(message=true,store=false)"
    # ]

    actions_list = [
        # "overlay(action=compute_ngd)",
        # "overlay(action=compute_ngd, virtual_edge_type=NGD1, subject_qnode_key=n00, object_qnode_key=n01)",
        # "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        # "overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_edge_type=P1, subject_qnode_key=n00, object_qnode_key=n01)",
        # "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_edge_type=J1)",
        # "overlay(action=add_node_pmids)",
        # "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        # "overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_edge_type=P1, subject_qnode_key=n00, object_qnode_key=n01)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n01, object_qnode_key=n00, virtual_edge_type=P1)",
        "return(message=true,store=false)"
    ]

    #### Parse the action_list and print the result
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response
    actions = result.data['actions']

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()

    # message_dict = araxdb.getMessage(2)  # acetaminophen2proteins graph
    # message_dict = araxdb.getMessage(13)  # ibuprofen -> proteins -> disease # work computer
    # message_dict = araxdb.getMessage(14)  # pleuropneumonia -> phenotypic_feature # work computer
    # message_dict = araxdb.getMessage(16)  # atherosclerosis -> phenotypic_feature  # work computer
    # message_dict = araxdb.getMessage(5)  # atherosclerosis -> phenotypic_feature  # home computer
    # message_dict = araxdb.getMessage(10)
    # message_dict = araxdb.getMessage(36)  # test COHD obs/exp, via ARAX_query.py 16
    # message_dict = araxdb.getMessage(39)  # ngd virtual edge test
    message_dict = araxdb.getMessage(1)

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
    # print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    #### Create an overlay object and use it to apply action[0] from the list
    print("Applying action")
    overlay = ARAXOverlay()
    result = overlay.apply(message, actions[0]['parameters'])
    response.merge(result)
    print("Finished applying action")

    # if result.status != 'OK':
    #    print(response.show(level=ARAXResponse.DEBUG))
    #    return response
    # response.data = result.data

    #### If successful, show the result
    # print(response.show(level=ARAXResponse.DEBUG))
    # response.data['message_stats'] = { 'n_results': message.n_results, 'id': message.id,
    #    'reasoner_id': message.reasoner_id, 'tool_version': message.tool_version }
    # response.data['message_stats']['confidence_scores'] = []
    # for result in message.results:
    #    response.data['message_stats']['confidence_scores'].append(result.confidence)

    # print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    # print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))
    # a comment on the end so you can better see the network on github

    # look at the response
    # print(response.show(level=ARAXResponse.DEBUG))
    # print(response.show())
    # print("Still executed")

    # look at the edges
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())),sort_keys=True,indent=2))
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes.values())), sort_keys=True, indent=2))
    # print(json.dumps(message.to_dict(), sort_keys=True, indent=2))
    # print(response.show(level=ARAXResponse.DEBUG))

    # just print off the values
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())), sort_keys=True, indent=2))
    # for edge in message.knowledge_graph.edges.values():
    #    if hasattr(edge, 'attributes') and edge.attributes and len(edge.attributes) >= 1:
    #        print(edge.attributes.pop().value)
    # print(f"Message: {json.dumps(message.to_dict(), sort_keys=True, indent=2)}")
    # print(message)
    print(
        f"KG edges: {json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())), sort_keys=True, indent=2)}")
    # print(response.show(level=ARAXResponse.DEBUG))
    print("Yet you still got here")
    # print(actions_parser.parse(actions_list))


if __name__ == "__main__": main()