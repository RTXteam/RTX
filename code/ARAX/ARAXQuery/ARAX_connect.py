import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_expander import ARAXExpander
import traceback
from collections import Counter
from collections.abc import Hashable
from itertools import combinations
import copy

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode

class ARAXConnect:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'connect_nodes',
        }
        self.report_stats = True  # Set this to False when ready to go to production, this is only for debugging purposes

        #parameter descriptions
        self.max_path_length_info = {
            "is_required": False,
            "examples": [2,3,5],
            "min": 1,
            "max": 5,
            "type": "integer",
            "description": "The maximum path length to connect nodes with. If not provided defaults to 2."
        }
        self.qnode_keys_info = {
            "is_required": False,
            "examples": [['n01', 'n02'],[]],
            "type": "list",
            "description": "List of qnode keys to connect. If not provided or empty all qnode_keys will be connected. If not empty must have at least 2 elements."
        }
        

        #command descriptions
        self.command_definitions = {
            "connect_nodes": {
                "dsl_command": "connect(action=connect_nodes)",
                "description": """
`connect_nodes` adds paths between nodes in the query graph and then preforms the fill operation to compete the knowledge graph. 

Use cases include:

* finding out how 3 concepts are connected. 
* connect 2 subgraphs in a query.
* etc.
            
You have the option to limit the maximum length of connections for node pairs (via `max_path_length=<n>`), or
else, limit which node pairs to connect based on a query node ids (via `qnode_keys=<a list of qnode keys>`
            
This can be applied to an arbitrary query graph as long as there are nodes.
                    """,
                'brief_description': """
connect_nodes adds paths between nodes in the query graph and then preforms the fill operation to compete the knowledge graph.
                    """,
                "parameters": {
                    "max_path_length": self.max_path_length_info,
                    "qnode_keys": self.qnode_keys_info
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

        self.response.debug(f"Applying Connect to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response

    def __connect_nodes(self, describe=False):
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
            allowable_parameters = {'action': {'connect_nodes'},
                                    'shortest_path': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'max_path_length': {int()}
                                    'qnode_keys': set(self.message.query_graph.nodes.keys())
                                }
        else:
            allowable_parameters = {'action': {'connect_nodes'},
                                    'shortest_path': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'max_path_length': {'a maximum path length to use to connect qnodes. Defaults to 2.'},
                                    'qnode_keys':{'a list of query node keys to connect'}
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
        if 'shortest_path' in self.parameters:
            if self.parameters['shortest_path'] in {'true', 'True', 't', 'T'}:
                self.parameters['shortest_path'] = True
            elif self.parameters['shortest_path'] in {'false', 'False', 'f', 'F'}:
                self.parameters['shortest_path'] = False
        else:
            self.parameters['shortest_path'] = True
        if 'qnode_keys' not in self.parameters or len(self.parameters['qnode_keys']) == 0:
            self.parameters['qnode_keys'] = list(set(self.message.query_graph.nodes.keys()))
            if len(self.parameters['qnode_keys']) < 2:
                self.response.error(
                    f"Query graph must have at least 2 nodes to connect.",
                    error_code="QueryGraphError")
        elif len(self.parameters['qnode_keys']) == 1:
            self.response.error(
                f"If qnode keys are provided you must provide at least 2 qnode keys.",
                error_code="ValueError")
        
        if 'max_path_length' not in self.parameters:
            self.parameters['max_path_length'] = 2
        
        if self.parameters['max_path_length'] < 1 or self.parameters['max_path_length'] > 5:
            self.response.error(
                f"Maximum path length must be betwen 1 and 5 inclusive.",
                error_code="ValueError")

        if self.response.status != 'OK':
            return self.response

        expander = ARAXExpander()
        messenger = ARAXMessenger()


        # Expand parameters
        mode = 'ARAX'
        timeout = 60
        kp = 'infores:rtx-kg2'
        prune_threshold = 500

        qnode_key_pairs = list(combinations(self.parameters['qnode_keys'], 2))
        edge_n = 1
        node_n = 1
        for qnode_pair in qnode_key_pairs:
            added_connection = False
            for n_new_nodes in range(self.parameters['max_path_length']):
                new_response = ARAXResponse()
                messenger.create_envelope(new_response)
                new_response.envelope.message.query_graph.nodes = {k:v for k,v in self.response.envelope.message.query_graph.nodes.items() if k in qnode_pair}
                qedge_keys = []
                node_pair_list = [qnode_pair[0]]
                for i in range(n_new_nodes):
                    new_qnode_key = f'arax_connect_node_{node_n}'
                    node_n += 1
                    # make new names until we find a node key not in the query graph
                    while new_qnode_key in self.response.envelope.message.query_graph.nodes:
                        new_qnode_key = f'arax_connect_node_{node_n}'
                        node_n += 1
                    node_pair_list.append(new_qnode_key)
                    add_qnode_params = {
                        'is_set' : 'true',
                        'key' : new_qnode_key
                    }
                    new_response = messenger.add_qnode(new_response, add_qnode_params)
                node_pair_list.append(qnode_pair[1])
                assert len(node_pair_list) == 2 + n_new_nodes
                # This zip command grabs nodes next to each other and puts them into tuple pairs
                # E.G. [1,2,3,4,5] -> [(1,2),(2,3),(3,4),(4,5)]
                new_qnode_key_pairs = list(zip(node_pair_list,node_pair_list[1:]))
                for new_qnode_pair in new_qnode_key_pairs:
                    new_qedge_key = f'connected_edge_{edge_n}'
                    edge_n += 1
                    # make new names until we find an edge key not in the query graph
                    while new_qedge_key in self.response.envelope.message.query_graph.edges:
                        new_qedge_key = f'arax_connect_edge_{edge_n}'
                        edge_n += 1
                    qedge_keys.append(new_qedge_key)
                    add_qedge_params = {
                        'key' : new_qedge_key,
                        'subject' : new_qnode_pair[0],
                        'object' : new_qnode_pair[1]
                    }
                    new_response = messenger.add_qedge(new_response, add_qedge_params)
                expand_params = {
                    'kp':kp,
                    'prune_threshold':prune_threshold,
                    'edge_key':qedge_keys,
                    'kp_timeout':timeout
                }
                new_response = expander.apply(new_response, expand_params, mode=mode)
                if new_response.status == 'OK' and len(new_response.envelope.message.knowledge_graph.edges) > len(self.response.envelope.message.knowledge_graph.edges):
                    added_connection = True
                    # FW: confirm with Eric that this is the correct way to merge response objects
                    self.response.envelope.message.query_graph.edges.update(new_response.envelope.message.query_graph.edges)
                    self.response.envelope.message.query_graph.nodes.update(new_response.envelope.message.query_graph.nodes)
                    self.response.envelope.message.knowledge_graph.edges.update(new_response.envelope.message.knowledge_graph.edges)
                    self.response.envelope.message.knowledge_graph.nodes.update(new_response.envelope.message.knowledge_graph.nodes)
                    self.response.merge(new_response)
                    # FW: If we do not want to stop when we find the shortest connection we could add an option 
                    # for shortest path and then check that here to deside if we want to break
                    break
            if not added_connection:
                #FW: may want to change this to an error
                self.response.warning(f"Could not connect the nodes {qnode_pair[0]} and {qnode_pair[1]} with a max path length of {self.parameters['max_path_length']}.")        
        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
