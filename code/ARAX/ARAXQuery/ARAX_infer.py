#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
import math
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_expander import ARAXExpander
from ARAX_resultify import ARAXResultify
from ARAX_decorator import ARAXDecorator
import traceback
from collections import Counter
from collections.abc import Hashable
from itertools import combinations
import copy

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.node import Node

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'scripts']))
from infer_utilities import InferUtilities
# from creativeDTD import creativeDTD
from creativeCRG import creativeCRG
from ExplianableDTD_db import ExplainableDTD
# from ExplianableCRG import ExplianableCRG

# sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
# from RTXConfiguration import RTXConfiguration
# RTXConfig = RTXConfiguration()

import pickle
import pandas as pd


class ARAXInfer:

    #### Constructor
    def __init__(self):
        self.kedge_global_iter = 0
        self.qedge_global_iter = 0
        self.qnode_global_iter = 0
        self.option_global_iter = 0
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'drug_treatment_graph_expansion',
            'chemical_gene_regulation_graph_expansion'
        }
        self.report_stats = True  # Set this to False when ready to go to production, this is only for debugging purposes

        #parameter descriptions
        self.xdtd_node_curie_info = {
            "is_required": True,
            "examples": ["DOID:9352","MONDO:0005306","HP:0001945"],
            "type": "string",
            "description": "The curie for the node you wish to predict drugs which will treat."
        }
        self.xdtd_n_drugs_info = {
            "is_required": False,
            "examples": [5,15,25],
            "default": 10,
            "type": "integer",
            "description": "The number of drug nodes to return. If not provided defaults to 10. Considering the response speed, the maximum number of drugs returned is only allowed to be 25."
        }
        self.xdtd_n_paths_info = {
            "is_required": False,
            "examples": [5,15,25],
            "default": 10,
            "type": "integer",
            "description": "The number of paths connecting to each returned node. If not provided defaults to 10. Considering the response speed, the maximum number of paths (if available) returned is only allowed to be 25."
        }
        self.xcrg_subject_curie_info = {
            "is_required": True,
            "examples": ["UMLS:C1440117", "MESH:D007053", "CHEMBL.COMPOUND:CHEMBL33884"],
            'type': 'string',
            'description': "The chemical curie, a curie with category of either 'biolink:ChemicalEntity', 'biolink:ChemicalMixture', or 'biolink:SmallMolecule'. **Note that although this parameter is said to be required, exactly one of `subject_curie` or `object_curie` is required as a parameter rather than both.**",
        }
        self.xcrg_object_curie_info = {
            "is_required": True,
            "examples": ["UniProtKB:Q96P20", "UniProtKB:O75807", "NCBIGene:406983"],
            'type': 'string',
            'description': "The gene curie, a curie with category of either 'biolink:Gene' or 'biolink:Protein'. **Note that although this parameter is said to be required, exactly one of `subject_curie` or `object_curie` is required as a parameter rather than both.**",
        }
        self.xcrg_subject_qnode_id = {
            "is_required": True,
            "examples": ["n01","n02"],
            "type": "string",
            "description": "The query graph node ID of a chemical. **Note that although this parameter is said to be required, this parameter is valid only when a query graph is used. Additionally, exactly one of 'subject_qnode_id' or 'object_qnode_id' is required when a query graph is used.**"
        }
        self.xcrg_object_qnode_id = {
            "is_required": True,
            "examples": ["n01","n02"],
            "type": "string",
            "description": "The query graph node ID of a gene. **Note that although this parameter is said to be required, this parameter is valid only when a query graph is used. Additionally, exactly one of 'subject_qnode_id' or 'object_qnode_id' is required when a query graph is used.**"
        }
        self.xcrg_regulation_type = {
            "is_required": False,
            "examples": ["n01","n02"],
            "default": "increase",
            "type": "string",
            "description": "What model (increased prediction or decreased prediction) to consult."
        }
        self.xcrg_n_result_curies_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 10,
            "type": "integer",
            "description": "The number of top predicted result nodes to return. If not provided defaults to 10."
        }
        self.xcrg_threshold = {
            "is_required": False,
            "examples": [0.3,0.5,0.8],
            "default": 0.5,
            "type": "float",
            "description": "Threshold to filter the prediction probability. If not provided defaults to 0.5."
        }
        self.xcrg_kp = {
            "is_required": False,
            "examples": ['infores:rtx-kg2',None],
            "default": 'infores:rtx-kg2',
            "type": "string",
            "description": "KP to use in path extraction. If not provided defaults to 'infores:rtx-kg2'."
        }
        self.xcrg_path_len = {
            "is_required": False,
            "examples": [2,3,4],
            "default": 2,
            "type": "integer",
            "description": "The length of paths for prediction. If not provided defaults to 2."
        }
        self.xcrg_n_paths_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 10,
            "type": "integer",
            "description": "The number of paths connecting to each returned node. If not provided defaults to 10."
        } 
        self.qedge_id_info = {
            "is_required": False,
            "examples": ["qedge_id_1","qedge_id_2","qedge_id_3"],
            "type": "string",
            "description": "The id of the qedge you wish to perform the drug treatment/chemical regulation inference expansion."
        }

        #command descriptions
        self.command_definitions = {
            "drug_treatment_graph_expansion": {
                "dsl_command": "infer(action=drug_treatment_graph_expansion)",
                "description": """
`drug_treatment_graph_expansion` predicts drug treatments for a given disease curie. It returns the top n results along with predicted graph explanations.  
            
You have the option to limit the maximum number of drug nodes to return (via `n_drugs=<n>`)
            
This cannot be applied to non disease/phenotypic feature nodes (nodes that do not belong to either of 'biolink:biolink:Disease', 'biolink:PhenotypicFeature', or 'biolink:DiseaseOrPhenotypicFeature').
                    """,
                'brief_description': """
drug_treatment_graph_expansion predicts drug treatments for a given node curie and provides along with an explination graph for each prediction.
                    """,
                "parameters": {
                    "node_curie": self.xdtd_node_curie_info,
                    "qedge_id": self.qedge_id_info,
                    "n_drugs": self.xdtd_n_drugs_info,
                    "n_paths": self.xdtd_n_paths_info
                }
            },
            "chemical_gene_regulation_graph_expansion": {
                "dsl_command": "infer(action=chemical_gene_regulation_graph_expansion)",
                "description": """
`chemical_gene_regulation_graph_expansion` predicts the regulation relationship (increase/decrease activity) between given chemicals or given genes. It return the top n results along with predicted graph explinations.  
            
You have the option to limit the maximum number of result nodes to return (via `n_result_curies=<n>`)
            
This can be applied to an arbitrary nide curie though will not return sensible results for the subject nodes without category 'chemicalentity/chemicalmixture/smallmodule' or the object nodes without category 'gene/protein".' 

**Note that the 'subject_curie' and 'object_curie' cannot be given in the same time, that is, if you give a curie to either one, another one should be omitted. However, when a query graph is used via DSL command or JSON format, the parameters 'subject_curie' and 'object_curie' can be omitted but one of 'subject_qnode_id' or 'object_qnode_id' need to be specified.**.
                    """,
                'brief_description': """
chemical_gene_regulation_graph_expansion predicts the regulation relationship between given chemicals and/or given genes and provides along with an explination graph for each prediction. Note that one of subject_curie (curie with category 'chemicalentity/chemicalmixture/smallmodule') or object_curie (curie with category 'gene/protein') is required as a parameter, However, when a query graph is used via DSL command or JSON format, the parameters 'subject_curie' and 'object_curie' can be omitted but one of 'subject_qnode_id' or 'object_qnode_id' need to be specified.
                    """,
                "parameters": {
                    "subject_curie": self.xcrg_subject_curie_info,
                    "object_curie": self.xcrg_object_curie_info,
                    "subject_qnode_id": self.xcrg_subject_qnode_id,
                    "object_qnode_id": self.xcrg_object_qnode_id,
                    "qedge_id": self.qedge_id_info,
                    "threshold": self.xcrg_threshold,
                    "kp": self.xcrg_kp,
                    "path_len": self.xcrg_path_len,
                    "regulation_type": self.xcrg_regulation_type,
                    "n_result_curies": self.xcrg_n_result_curies_info,
                    "n_paths": self.xcrg_n_paths_info
                }                
            }
        }

    # def __get_formated_edge_key(self, edge: Edge, kp: str = 'infores:rtx-kg2') -> str:
    #     return f"{kp}:{edge.subject}-{edge.predicate}-{edge.object}"

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
                response.debug(f"Number of nodes in KG by type is {Counter([x.categories[0] for x in message.knowledge_graph.nodes.values()])}")  # type is a list, just get the first one
                #response.debug(f"Number of nodes in KG by with attributes are {Counter([x.category for x in message.knowledge_graph.nodes.values()])}")  # don't really need to worry about this now
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(f"Number of edges in KG by type is {Counter([x.predicate for x in message.knowledge_graph.edges.values()])}")
                response.debug(f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges.values() if x.attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges.values():
                    if x.attributes:
                        for attr in x.attributes:
                            if hasattr(attr, "original_attribute_name"):
                                attribute_names.append(attr.original_attribute_name)
                            if hasattr(attr, "attribute_type_id"):
                                attribute_names.append(attr.attribute_type_id)      
                response.debug(f"Number of edges in KG by attribute {Counter(attribute_names)}")
        return response

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        #description_list = []
        #for action in self.allowable_actions:
        #    description_list.append(getattr(self, '_' + self.__class__.__name__ + '__' + action)(describe=True))
        #return description_list
        return list(self.command_definitions.values())

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
                return -1
            elif type(item) == list or type(item) == set:
                    for item_val in item:
                        if item_val not in allowable_parameters[key]:
                            self.response.error(
                                f"Supplied value {item_val} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                            return -1
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in allowable_parameters[key]]):  # if it's a float, just accept it as it is
                    continue
                elif any([type(x) == int for x in allowable_parameters[key]]):
                    continue
                elif any([x is None for x in allowable_parameters[key]]):
                    continue
                elif key == "node_curie":  #FIXME: For now, if it's a node curie, just accept it as it is
                    continue
                elif key == "subject_curie": #FIXME: same as above
                    continue
                elif key == "object_curie": #FIXME: same as above
                    continue
                elif key == "subject_qnode_id": #FIXME: same as above
                    continue
                elif key == "object_qnode_id": #FIXME: same as above
                    continue
                elif key == "kp": #FIXME: same as above
                    continue
                else:  # otherwise, it's really not an allowable parameter
                    self.response.error(
                        f"This Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                    return -1

    #### Top level decision maker for applying filters
    def apply(self, response, input_parameters):

        if response is None:
            response = ARAXResponse()
        self.response = response
        self.message = response.envelope.message

        # initialize creative mode objects and node synonymizer
        self.synonymizer = NodeSynonymizer()

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            self.response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return self.response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            self.response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}", error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            self.response.error(f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}", error_code="UnknownAction")

        #### Return if any of the parameters generated an error (showing not just the first one)
        if self.response.status != 'OK':
            return self.response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        #### Store these final parameters for convenience
        self.response.data['parameters'] = parameters
        self.parameters = parameters

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters['action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        self.response.debug(f"Applying Infer to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response

    def __drug_treatment_graph_expansion(self, describe=False):
        """
        Run "drug_treatment_graph_expansion" action.
        Allowable parameters: {'node_curie': str, 
                                'qedge_id': str,
                                'n_drugs': int
                                'n_paths': int}
        :return:
        """
        message = self.message
        parameters = self.parameters
        XDTD = ExplainableDTD()
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'drug_treatment_graph_expansion'},
                                    'node_curie': {str()},
                                    'qedge_id': set([key for key in self.message.query_graph.edges.keys()]),
                                    'n_drugs': {int()},
                                    'n_paths': {int()}
                                }
        else:
            allowable_parameters = {'action': {'drug_treatment_graph_expansion'},
                                    'node_curie': {'The node to predict drug treatments for.'},
                                    'qedge_id': {'The edge to place the predicted mechanism of action on. If none is provided, the query graph must be empty and a new one will be inserted.'},
                                    'n_drugs': {'The number of drugs to return. Defaults to 10. Maxiumum is only allowable to be 25.'},
                                    'n_paths': {'The number of paths connecting each drug to return. Defaults to 10.  Maxiumum is only allowable to be 25.'}
                                }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        
        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # Make sure that if ARAXi node_curie is provided, that node is actually in the query graph
        if 'node_curie' in parameters and parameters['node_curie'] and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes') and message.query_graph.nodes:
            ids_in_qg = set()
            for node in message.query_graph.nodes.values():
                if node.ids:
                    ids_in_qg.update(node.ids)
            if parameters['node_curie'] not in ids_in_qg:
                self.response.error(f"Supplied node_curie {parameters['node_curie']} is not in the query graph. I was given the curies: {ids_in_qg}", error_code="UnknownNode")
                return self.response
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        # Set defaults and check parameters:
        if 'n_drugs' in self.parameters:
            try:
                self.parameters['n_drugs'] = int(self.parameters['n_drugs'])
            except ValueError:
                self.response.error(f"The `n_drugs` value must be a positive integer. The provided value was {self.parameters['n_drugs']}.", error_code="ValueError")
            if self.parameters['n_drugs'] <= 0:
                self.response.error(f"The `n_drugs` value should be larger than 0. The provided value was {self.parameters['n_drugs']}.", error_code="ValueError")
            if self.parameters['n_drugs'] > 25:
                self.response.warning(f"The `n_drugs` value was set to {self.parameters['n_drugs']}, but the maximum allowable value is 25. Setting `n_drugs` to 25.")
                self.parameters['n_drugs'] = 25
        else:
            self.parameters['n_drugs'] = 10

        if 'n_paths' in self.parameters:
            try:
                self.parameters['n_paths'] = int(self.parameters['n_paths'])
            except ValueError:
                self.response.error(f"The `n_paths` value must be a positive integer. The provided value was {self.parameters['n_paths']}.", error_code="ValueError")
            if self.parameters['n_paths'] <= 0:
                self.response.error(f"The `n_paths` value should be larger than 0. The provided value was {self.parameters['n_paths']}.", error_code="ValueError")
            if self.parameters['n_paths'] > 25:
                self.response.warning(f"The `n_paths` value was set to {self.parameters['n_paths']}, but the maximum allowable value is 25. Setting `n_paths` to 25.")
                self.parameters['n_paths'] = 25
        else:
            self.parameters['n_paths'] = 10

        if self.response.status != 'OK':
            return self.response

        normalized_curie = self.synonymizer.get_canonical_curies(self.parameters['node_curie'])[self.parameters['node_curie']]
        if normalized_curie:
            preferred_curie = normalized_curie['preferred_curie']
            self.response.debug(f"Get a preferred sysnonym {preferred_curie} from Node Synonymizer for {self.parameters['node_curie']}")
        else:
            self.response.warning(f"Could not get a preferred sysnonym for disease {self.parameters['node_curie']}")

        try:
            top_drugs = XDTD.get_top_drugs_for_disease(disease_ids=preferred_curie)
            top_paths = XDTD.get_top_paths_for_disease(disease_ids=preferred_curie)
        except:
            self.response.error(f"Could not get top drugs and paths for disease {preferred_curie}", error_code="ValueError")
            return self.response

        if len(top_drugs) == 0:
            self.response.error(f"Could not get predicted drugs for disease {preferred_curie}. Likely the model was not trained with this disease.", error_code="ValueError")
            return self.response
        if len(top_paths) == 0:
            self.response.warning(f"Could not get any predicted paths for disease {preferred_curie}. Likely the model considers there is no reasonable path for this disease.")

        # FW: temp fix to use the pickle fil for dev work rather than recomputing
        # Comment out the following 3 lines and uncomment the above for prod deploy
        # top_drugs = pd.read_csv(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data',"top_n_drugs.csv"]))
        # with open(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data',"result_from_self_predict_top_M_paths.pkl"]),"rb") as fid:
        #     top_paths = pickle.load(fid)
        
        ## Limit the number of drugs and paths to the top n
        top_drugs = top_drugs.iloc[:self.parameters['n_drugs'],:].reset_index(drop=True)
        top_paths = {(row[0], row[2]):top_paths[(row[0], row[2])][:self.parameters['n_paths']] for row in top_drugs.to_numpy()}

        # TRAPI-ifies the results of the model
        iu = InferUtilities()
        qedge_id = self.parameters.get('qedge_id')

        self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = iu.genrete_treat_subgraphs(self.response, top_drugs, top_paths, qedge_id, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter)

        return self.response


    def __chemical_gene_regulation_graph_expansion(self, describe=False):
        """
        Run "chemical_gene_regulation_graph_expansion" action.
        Allowable parameters: {'subject_curie': str, 
                                'object_curie': str,
                                'qedge_id' str,
                                'regulation_type': {'increase', 'decrease'},
                                'threshold': float,
                                'kp': str,
                                'path_len': int,
                                'n_result_curies': int,
                                'n_paths': int}
        :return:
        """
        message = self.message
        parameters = self.parameters
        XCRG = creativeCRG(self.response, os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data', 'xCRG_data']))
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'chemical_gene_regulation_graph_expansion'},
                                    'subject_curie': {str()},
                                    'object_curie': {str()},
                                    'subject_qnode_id': {str()},
                                    'object_qnode_id': {str()},
                                    'qedge_id': set([key for key in self.message.query_graph.edges.keys()]),
                                    'regulation_type': ['increase', 'decrease'],
                                    'threshold': {float()},
                                    'kp': {str()},
                                    'path_len': {int()},
                                    'n_result_curies': {int()},
                                    'n_paths': {int()}
                                }
        else:
            allowable_parameters = {'action': {'chemical_gene_regulation_graph_expansion'},
                                    'subject_curie': {'The chemical curie used for gene regulation.'},
                                    'object_curie': {'The gene curie used to predict what chemicals can regulate it.'},
                                    'subbject_qnode_id': {'The query graph node ID of a chemical.'},
                                    'object_qnode_id': {'The query graph node ID of a gene.'},
                                    'qedge_id': {'The edge to place the predicted mechanism of action on. If none is provided, the query graph must be empty and a new one will be inserted.'},
                                    'regulation_type': {"What model (increased prediction or decreased prediction) to consult. Two options: 'increase', 'decrease'."},
                                    'threshold': {"Threshold to filter the prediction probability. If not provided defaults to 0.5."},
                                    'kp': {"KP to use in path extraction. If not provided defaults to 'infores:rtx-kg2'."},
                                    'path_len': {"The length of paths for prediction. If not provided defaults to 2."},
                                    'n_result_curies': {'The number of top predicted result nodes to return. Defaults to 20.'},
                                    'n_paths': {'The number of paths connecting to each returned node. Defaults to 20.'}
                                }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)

        # Set defaults and check parameters:
        if 'regulation_type' in self.parameters:
            self.parameters['regulation_type'] = self.parameters['regulation_type'].lower()
            if self.parameters['regulation_type'] not in ['increase', 'decrease']:
                self.response.error(
                f"The `regulation_type` value must be either 'increase' or 'decrease'. The provided value was {self.parameters['regulation_type']}.",
                error_code="ValueError")
        else:
            self.parameters['regulation_type'] = 'increase'
            
        if 'threshold' in self.parameters:
            if isinstance(self.parameters['threshold'], str):
                self.parameters['threshold'] = eval(self.parameters['threshold'])
            if isinstance(self.parameters['threshold'], int):
                if self.parameters['threshold'].is_float():
                    self.parameters['threshold'] = float(self.parameters['threshold'])
            if not isinstance(self.parameters['threshold'], float) or self.parameters['threshold'] > 1 or self.parameters['threshold'] < 0:
                self.response.error(
                f"The `threshold` value must be a positive float between 0 and 1. The provided value was {self.parameters['threshold']}.",
                error_code="ValueError")
        else:
            self.parameters['threshold'] = 0.5   

        if 'kp' in self.parameters:
            if not isinstance(self.parameters['kp'], str) or not (self.parameters['kp'] is None):
                self.response.error(
                f"The `kp` value must be None or a specific kp. The provided value was {self.parameters['kp']}.",
                error_code="ValueError")
        else:
            self.parameters['kp'] = 'infores:rtx-kg2'

        if 'path_len' in self.parameters:
            if isinstance(self.parameters['path_len'], str):
                self.parameters['path_len'] = eval(self.parameters['path_len'])
            if isinstance(self.parameters['path_len'], float):
                if self.parameters['path_len'].is_integer():
                    self.parameters['path_len'] = int(self.parameters['path_len'])
            if not isinstance(self.parameters['path_len'], int) or self.parameters['path_len'] < 1:
                self.response.error(
                f"The `path_len` value must be a positive integer. The provided value was {self.parameters['path_len']}.",
                error_code="ValueError")
        else:
            self.parameters['path_len'] = 2

        if 'n_result_curies' in self.parameters:
            if isinstance(self.parameters['n_result_curies'], str):
                self.parameters['n_result_curies'] = eval(self.parameters['n_result_curies'])
            if isinstance(self.parameters['n_result_curies'], float):
                if self.parameters['n_result_curies'].is_integer():
                    self.parameters['n_result_curies'] = int(self.parameters['n_result_curies'])
            if not isinstance(self.parameters['n_result_curies'], int) or self.parameters['n_result_curies'] < 1:
                self.response.error(
                f"The `n_result_curies` value must be a positive integer. The provided value was {self.parameters['n_result_curies']}.",
                error_code="ValueError")
        else:
            self.parameters['n_result_curies'] = 10

        if 'n_paths' in self.parameters:
            if isinstance(self.parameters['n_paths'], str):
                self.parameters['n_paths'] = eval(self.parameters['n_paths'])
            if isinstance(self.parameters['n_paths'], float):
                if self.parameters['n_paths'].is_integer():
                    self.parameters['n_paths'] = int(self.parameters['n_paths'])
            if not isinstance(self.parameters['n_paths'], int) or self.parameters['n_paths'] < 1:
                self.response.error(
                f"The `n_paths` value must be a positive integer. The provided value was {self.parameters['n_paths']}.",
                error_code="ValueError")
        else:
            self.parameters['n_paths'] = 10

        if self.response.status != 'OK':
            return self.response

        # Make sure that if at least subject node or object node is provided. If it is provided, check if it also exists in the query graph        
        if hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes') and message.query_graph.nodes:
            qnodes = message.query_graph.nodes
            if 'subject_qnode_id' in parameters or 'object_qnode_id' in parameters:
                if 'subject_qnode_id' in parameters:
                    if parameters['subject_qnode_id'] in qnodes:
                        if not qnodes[parameters['subject_qnode_id']].ids:
                            self.response.error(f"The corresponding ids of subject_qnode_id '{parameters['subject_qnode_id']}' is None")
                            return self.response
                        subject_curie = qnodes[parameters['subject_qnode_id']].ids[0]
                        normalized_subject_curie = self.synonymizer.get_canonical_curies(subject_curie)[subject_curie]
                        if normalized_subject_curie:
                            preferred_subject_curie = normalized_subject_curie['preferred_curie']
                        else:
                            preferred_subject_curie = subject_curie
                    else:
                        self.response.error(f"Could not find subject_qnode_id '{parameters['subject_qnode_id']}' in the query graph")
                        return self.response
                else:
                    preferred_subject_curie = None

                if 'object_qnode_id' in parameters:
                    if parameters['object_qnode_id'] in qnodes:
                        if not qnodes[parameters['object_qnode_id']].ids:
                            self.response.error(f"The corresponding ids of object_qnode_id '{parameters['object_qnode_id']}' is None")
                            return self.response
                        object_curie = qnodes[parameters['object_qnode_id']].ids[0]
                        normalized_object_curie = self.synonymizer.get_canonical_curies(object_curie)[object_curie]
                        if normalized_object_curie:
                            preferred_object_curie = normalized_object_curie['preferred_curie']
                        else:
                            preferred_object_curie = subject_curie
                    else:
                        self.response.error(f"Could not find object_qnode_id '{parameters['object_qnode_id']}' in the query graph")
                        return self.response
                else:
                    preferred_object_curie = None

                if preferred_subject_curie and preferred_object_curie:
                    self.response.error(f"The parameters 'subject_curie' and 'object_curie' in infer action 'chemical_gene_regulation_graph_expansion' can't be specified in the same time.")
                    return self.response

                if not preferred_subject_curie and not preferred_object_curie:
                    self.response.error(f"Both parameters 'subject_curie' and 'object_curie' are not provided. Please provide the curie for either one of them")
                    return self.response

            else:
                self.response.error(f"The 'query_graph' is detected. One of 'subject_qnode_id' or 'object_qnode_id' should be specified.")

        else:
            if 'subject_curie' in parameters or 'object_curie' in parameters:
                if 'subject_curie' in parameters:
                    parameters['subject_curie'] = eval(parameters['subject_curie']) if parameters['subject_curie'] == 'None' else parameters['subject_curie']
                    if parameters['subject_curie']:
                        ## if 'subject_curie' passes, return its normalized curie
                        normalized_subject_curie = self.synonymizer.get_canonical_curies(self.parameters['subject_curie'])[self.parameters['subject_curie']]
                        if normalized_subject_curie:
                            preferred_subject_curie = normalized_subject_curie['preferred_curie']
                            self.response.debug(f"Get a preferred sysnonym {preferred_subject_curie} from Node Synonymizer for subject curie {self.parameters['subject_curie']}")
                        else:
                            preferred_subject_curie = self.parameters['subject_curie']
                            self.response.warning(f"Could not get a preferred sysnonym for the queried chemical {self.parameters['subject_curie']} and thus keep it as it")
                    else:
                        preferred_subject_curie = None
                else:
                    preferred_subject_curie = None

                if 'object_curie' in parameters:
                    parameters['object_curie'] = eval(parameters['object_curie']) if parameters['object_curie'] == 'None' else parameters['object_curie']
                    if parameters['object_curie']:
                        ## if 'object_curie' passes, return its normalized curie
                        normalized_object_curie = self.synonymizer.get_canonical_curies(self.parameters['object_curie'])[self.parameters['object_curie']]
                        if normalized_object_curie:
                            preferred_object_curie = normalized_object_curie['preferred_curie']
                            self.response.debug(f"Get a preferred sysnonym {preferred_object_curie} from Node Synonymizer for object curie {self.parameters['object_curie']}")
                        else:
                            preferred_object_curie = self.parameters['object_curie']
                            self.response.warning(f"Could not get a preferred sysnonym for the queried gene {self.parameters['object_curie']}")
                    else:
                        preferred_object_curie = None
                else:
                    preferred_object_curie = None


                if preferred_subject_curie and preferred_object_curie:
                    self.response.error(f"The parameters 'subject_curie' and 'object_curie' in infer action 'chemical_gene_regulation_graph_expansion' can't be specified in the same time.")
                    return self.response

                if not preferred_subject_curie and not preferred_object_curie:
                    self.response.error(f"Both parameters 'subject_curie' and 'object_curie' are not provided. Please provide the curie for either one of them")
                    return self.response
            else:
                self.response.error(f"No 'query_graph' is found and thus either 'subject_curie' or 'object_curie' should be specified.")

        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response


        if preferred_subject_curie and not preferred_object_curie:
            try:
                top_predictions = XCRG.predict_top_N_genes(query_chemical=preferred_subject_curie, N=self.parameters['n_result_curies'], threshold=self.parameters['threshold'], model_type=self.parameters['regulation_type'])
                top_paths = XCRG.predict_top_M_paths(query_chemical=preferred_subject_curie, query_gene=None, model_type=self.parameters['regulation_type'], N=self.parameters['n_result_curies'], M=self.parameters['n_paths'], threshold=self.parameters['threshold'], kp=self.parameters['kp'], path_len=self.parameters['path_len'], interm_ids=None, interm_names= None, interm_categories=None)
            except:
                self.response.error(f"Something error occurred to get top genes or paths for chemical {preferred_subject_curie}", error_code="ValueError")
                return self.response
            if top_predictions is None or len(top_predictions) == 0:
                self.response.warning(f"Could not get predicted genes for chemical {preferred_subject_curie}. Likely the model was not trained with this chemical.")
                return self.response
            if top_paths is None or len(top_paths) == 0:
                self.response.warning(f"Could not get any predicted paths for chemical {preferred_subject_curie}. Likely the model considers there is no reasonable path for this chemical.")

            iu = InferUtilities()
            qedge_id = self.parameters.get('qedge_id')
            self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = iu.genrete_regulate_subgraphs(self.response, normalized_subject_curie, None, top_predictions, top_paths, qedge_id, self.parameters['regulation_type'], self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter)
        elif not preferred_subject_curie and preferred_object_curie:
            try:
                top_predictions = XCRG.predict_top_N_chemicals(query_gene=preferred_object_curie, N=self.parameters['n_result_curies'], threshold=self.parameters['threshold'], model_type=self.parameters['regulation_type'])
                top_paths = XCRG.predict_top_M_paths(query_chemical=None, query_gene=preferred_object_curie, model_type=self.parameters['regulation_type'], N=self.parameters['n_result_curies'], M=self.parameters['n_paths'], threshold=self.parameters['threshold'], kp=self.parameters['kp'], path_len=self.parameters['path_len'], interm_ids=None, interm_names= None, interm_categories=None)
            except:
                self.response.error(f"Something error occurred to get top chemicals or paths for gene {preferred_object_curie}", error_code="ValueError")
                return self.response
            if top_predictions is None or len(top_predictions) == 0:
                self.response.warning(f"Could not get predicted chemicals for gene {preferred_object_curie}. Likely the model was not trained with this gene.")
                return self.response
            if top_paths is None or len(top_paths) == 0:
                self.response.warning(f"Could not get any predicted paths for gene {preferred_object_curie}. Likely the model considers there is no reasonable path for this gene.")

            iu = InferUtilities()
            qedge_id = self.parameters.get('qedge_id')
            self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = iu.genrete_regulate_subgraphs(self.response, None, normalized_object_curie, top_predictions, top_paths, qedge_id,  self.parameters['regulation_type'], self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter)

        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
