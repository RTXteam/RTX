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
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'scripts']))
# from creativeDTD import creativeDTD

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
        }
        self.report_stats = True  # Set this to False when ready to go to production, this is only for debugging purposes

        #parameter descriptions
        self.node_curie_info = {
            "is_required": True,
            "examples": ["DOID:9352","MONDO:0005306","HP:0001945"],
            "type": "string",
            "description": "The curie for the node you wish to predict drugs which will treat."
        }
        self.n_drugs_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 50,
            "type": "integer",
            "description": "The number of drug nodes to return. If not provided defaults to 50."
        }
        self.n_paths_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 20,
            "type": "integer",
            "description": "The number of paths connecting to each returned drug node. If not provided defaults to 20."
        }
        

        #command descriptions
        self.command_definitions = {
            "drug_treatment_graph_expansion": {
                "dsl_command": "infer(action=drug_treatment_graph_expansion)",
                "description": """
`drug_treatment_graph_expansion` predicts drug treatments for a given node curie. It return the top n results along with predicted graph explinations.  
            
You have the option to limit the maximum number of drug nodes to return (via `n_drugs=<n>`)
            
This can be applied to an arbitrary nide curie though will not return sensible results for non disease/phenotypic feature nodes.
                    """,
                'brief_description': """
drug_treatment_graph_expansion predicts drug treatments for a given node curie and provides along with an explination graph for each prediction.
                    """,
                "parameters": {
                    "node_curie": self.node_curie_info,
                    "n_drugs": self.n_drugs_info,
                    "n_paths":self.n_paths_info
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
                            self.response.warning(
                                f"Supplied value {item_val} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                            return -1
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in allowable_parameters[key]]):  # if it's a float, just accept it as it is
                    continue
                elif any([type(x) == int for x in allowable_parameters[key]]):
                    continue
                elif any([x is None for x in allowable_parameters[key]]):
                    continue
                else:  # otherwise, it's really not an allowable parameter
                    self.response.warning(
                        f"Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                    return -1

    #### Top level decision maker for applying filters
    def apply(self, input_response, input_parameters):

        #### Define a default response
        #response = ARAXResponse()
        self.response = input_response
        self.message = input_response.envelope.message

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
        Connects qnodes and runs expand.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'drug_treatment_graph_expansion'},
                                    'node_curie': {None},
                                    'n_drugs': {int()},
                                    'n_paths': {int()}
                                }
        else:
            allowable_parameters = {'action': {'drug_treatment_graph_expansion'},
                                    'node_curie': {'The node to predict drug treatments for.'},
                                    'n_drugs': {'The number of drugs to return. Defaults to 50.'},
                                    'n_paths': {'The number of paths connecting each drug to return. Defaults to 20.'}
                                }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        
        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response


        # Set defaults and check parameters:
        if 'n_drugs' in self.parameters:
            if isinstance(self.parameters['n_drugs'], float):
                if self.parameters['n_drugs'].is_integer():
                    self.parameters['n_drugs'] = int(self.parameters['n_drugs'])
            if not isinstance(self.parameters['n_drugs'], int) or self.parameters['n_drugs'] < 1:
                self.response.error(
                f"The `n_drugs` value must be a positive integer. The provided value was {self.parameters['n_drugs']}.",
                error_code="ValueError")
        else:
            self.parameters['n_drugs'] = 50

        if 'n_paths' in self.parameters:
            if isinstance(self.parameters['n_paths'], float):
                if self.parameters['n_paths'].is_integer():
                    self.parameters['n_paths'] = int(self.parameters['n_paths'])
            if not isinstance(self.parameters['n_paths'], int) or self.parameters['n_paths'] < 1:
                self.response.error(
                f"The `n_paths` value must be a positive integer. The provided value was {self.parameters['n_paths']}.",
                error_code="ValueError")
        else:
            self.parameters['n_paths'] = 20

        if self.response.status != 'OK':
            return self.response

        # FW: may need these to add the answer graphs if not will delete
        expander = ARAXExpander()
        messenger = ARAXMessenger()

        # expand parameters
        mode = 'ARAX'
        timeout = 60
        kp = 'infores:rtx-kg2'
        prune_threshold = 500


        # dtd = creativeDTD(data_path, model_path, use_gpu=False)

        # dtd.set_query_disease(self.parameters['node_curie'])
        # top_drugs = dtd.predict_top_N_drugs(self.parameters['n_drugs'])
        # top_paths = dtd.predict_top_M_paths(self.parameters['n_paths'])

        # FW: temp fix to use the pickle fil for dev work rather than recomputing
        
        top_drugs = pd.read_csv(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data',"top_n_drugs.csv"]))
        with open(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data',"result_from_self_predict_top_M_paths.pkl"]),"rb") as fid:
            top_paths = pickle.load(fid)
        path_lengths = set([math.floor(len(x[0].split("->"))/2.) for paths in top_paths.values() for x in paths])
        max_path_len = max(path_lengths)
        disease = list(top_paths.keys())[0][1]
        add_qnode_params = {
            'key' : "disease",
            'name': disease
        }
        self.response = messenger.add_qnode(self.response, add_qnode_params)
        add_qnode_params = {
            'key' : "drug",
            'categories': ['biolink:Drug']
        }
        self.response = messenger.add_qnode(self.response, add_qnode_params)
        add_qedge_params = {
            'key' : "probably_treats",
            'subject' : "drug",
            'object' : "disease",
            'predicates': ["biolink:probably_treats"]
        }
        self.response = messenger.add_qedge(self.response, add_qedge_params)
        path_keys = [{} for i in range(max_path_len)]
        for i in range(max_path_len+1):
            if (i+1) in path_lengths:
                path_qnodes = ["drug"]
                for j in range(i):
                    new_qnode_key = f"creative_DTD_qnode_{self.qnode_global_iter}"
                    path_qnodes.append(new_qnode_key)
                    add_qnode_params = {
                        'key' : new_qnode_key,
                        'option_group_id': f"creative_DTD_option_group_{self.option_global_iter}",
                        "is_set": "true"
                    }
                    self.response = messenger.add_qnode(self.response, add_qnode_params)
                    self.qnode_global_iter += 1
                path_qnodes.append("disease")
                qnode_pairs = list(zip(path_qnodes,path_qnodes[1:]))
                qedge_key_list = []
                for qnode_pair in qnode_pairs:
                    add_qedge_params = {
                        'key' : f"creative_DTD_qedge_{self.qedge_global_iter}",
                        'subject' : qnode_pair[0],
                        'object' : qnode_pair[1],
                        'option_group_id': f"creative_DTD_option_group_{self.option_global_iter}"
                    }
                    qedge_key_list.append(f"creative_DTD_qedge_{self.qedge_global_iter}")
                    self.qedge_global_iter += 1
                    self.response = messenger.add_qedge(self.response, add_qedge_params)
                path_keys[i]["qnode_pairs"] = qnode_pairs
                path_keys[i]["qedge_keys"] = qedge_key_list
                self.option_global_iter += 1

        # FW: code that will add resulting paths to the query graph and knowledge graph goes here
        essence_scores = {}
        for (drug, disease), paths in top_paths.items():
            path_added = False
            # Splits the paths which are encodes as strings into a list of nodes names and edge predicates
            # The x[0] is here since each element consists of the string path and a score we are currently ignoring the score
            split_paths = [x[0].split("->") for x in paths]
            for path in split_paths:
                new_response = ARAXResponse()
                messenger.create_envelope(new_response)
                n_elements = len(path)
                # Creates edge tuples of the form (node name 1, edge predicate, node name 2)
                edge_tuples = [(path[i],path[i+1],path[i+2]) for i in range(0,n_elements-2,2)]
                path_idx = len(edge_tuples)-1
                added_nodes = set()
                for i in range(path_idx+1):
                    if path_keys[path_idx]["qnode_pairs"][i][0] not in added_nodes:
                        add_qnode_params = {
                            'key' : path_keys[path_idx]["qnode_pairs"][i][0],
                            'name': edge_tuples[i][0]
                        }
                        new_response = messenger.add_qnode(new_response, add_qnode_params)
                        added_nodes.add(path_keys[path_idx]["qnode_pairs"][i][0])
                    if path_keys[path_idx]["qnode_pairs"][i][1] not in added_nodes:
                        add_qnode_params = {
                            'key' : path_keys[path_idx]["qnode_pairs"][i][1],
                            'name': edge_tuples[i][2]
                        }
                        new_response = messenger.add_qnode(new_response, add_qnode_params)
                        added_nodes.add(path_keys[path_idx]["qnode_pairs"][i][1])
                    new_qedge_key = path_keys[path_idx]["qedge_keys"][i]
                    add_qedge_params = {
                        'key' : new_qedge_key,
                        'subject' : path_keys[path_idx]["qnode_pairs"][i][0],
                        'object' : path_keys[path_idx]["qnode_pairs"][i][1],
                        'predicates': [edge_tuples[i][1]]
                    }
                    new_response = messenger.add_qedge(new_response, add_qedge_params)
                expand_params = {
                    'kp':kp,
                    'prune_threshold':prune_threshold,
                    'edge_key':path_keys[path_idx]["qedge_keys"],
                    'kp_timeout':timeout
                }
                new_response = expander.apply(new_response, expand_params, mode=mode)
                if new_response.status == 'OK':
                    for knode_id, knode in new_response.envelope.message.knowledge_graph.nodes.items():
                        if 'disease' in knode.qnode_keys:
                            normalized_disease = knode_id
                        if 'drug' in knode.qnode_keys:
                            normalized_drug = knode_id
                            normalized_drug_name = knode.name
                        if knode_id in self.response.envelope.message.knowledge_graph.nodes:
                            new_response.envelope.message.knowledge_graph.nodes[knode_id].qnode_keys += self.response.envelope.message.knowledge_graph.nodes[knode_id].qnode_keys
                            self.response.envelope.message.knowledge_graph.nodes[knode_id].qnode_keys = new_response.envelope.message.knowledge_graph.nodes[knode_id].qnode_keys
                    self.response.envelope.message.knowledge_graph.nodes.update(new_response.envelope.message.knowledge_graph.nodes)
                    self.response.envelope.message.knowledge_graph.edges.update(new_response.envelope.message.knowledge_graph.edges)
                    self.response.merge(new_response)
                    path_added = True
            if path_added:
                treat_score = top_drugs.loc[top_drugs['drug_id'] == drug]["tp_score"].iloc[0]
                essence_scores[normalized_drug_name] = treat_score
                edge_attribute_list = [
                    # EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                    EdgeAttribute(original_attribute_name="provided_by", value="infores:arax", attribute_type_id="biolink:aggregator_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                    EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="biolink:computed_value", attribute_source="infores:arax-reasoner-ara", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    EdgeAttribute(attribute_type_id="EDAM:data_0951", original_attribute_name="probability_treats", value=str(treat_score))
                ]
                fixed_edge = Edge(predicate="biolink:probably_treats", subject=normalized_drug, object=normalized_disease,
                                attributes=edge_attribute_list)
                fixed_edge.qedge_keys = ["probably_treats"]
                self.response.envelope.message.knowledge_graph.edges[f"creative_DTD_prediction_{self.kedge_global_iter}"] = fixed_edge
                self.kedge_global_iter += 1
            else:
                self.response.warning(f"Something went wrong when adding the subgraph for the drug-disease pair ({drug},{disease}) to the knowledge graph. Skipping this result....")
        resultifier = ARAXResultify()
        resultify_params = {
            "ignore_edge_direction": "true"
        }
        self.response = resultifier.apply(self.response, resultify_params)
        for result in self.response.envelope.message.results:
            result.score = essence_scores[result.essence]
        self.response.envelope.message.results.sort(key=lambda x: x.score, reverse=True)
        return self.response







##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
