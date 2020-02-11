#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
from response import Response


class ARAXOverlay:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'compute_ngd',
            'overlay_clinical_info',
            'compute_jaccard'
        }

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        for action in self.allowable_actions:
            getattr(self, '_' + self.__class__.__name__ + '__' + action)(describe=True)

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
                self.response.error(
                    f"Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}",
                    error_code="UnknownValue")


    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters):

        #### Define a default response
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
        return response

    def __compute_ngd(self, describe=False):
        """
        Computes normalized google distance between two nodes connected by an edge in the knowledge graph
        and adds that as an edge attribute.
        Allowable parameters: {default_value: {'0', 'inf'}}
        :return:
        """
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        allowable_parameters = {'action': {'compute_ngd'}, 'default_value': {'0', 'inf'}}

        # A little function to describe what this thing does
        if describe:
            print(allowable_parameters)
            return

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        ngd_params = {'default_value': np.inf}  # here is where you can set default values

        # parse the input parameters to be the data types I need them to be
        for key, value in self.parameters.items():
            if key != 'action':
                if key == 'default_value':
                    if value == '0':
                        ngd_params[key] = 0
                    elif value == 'inf':
                        ngd_params[key] = np.inf

        # now do the call out to NGD
        from Overlay.compute_ngd import ComputeNGD
        NGD = ComputeNGD(self.response, self.message, ngd_params)
        response = NGD.compute_ngd()
        return response

    #### Compute confidence scores. Double underscore means this is a private method
    def __compute_confidence_scores(self):

        #### Set up local references to the response and the message
        response = self.response
        message = self.message

        response.debug(f"Computing confidence scores for all results")

        response.warning(f"OMG, we're just generating random numbers!")
        import random

        #### Loop over all results, computing and storing confidence scores
        for result in message.results:
            result.confidence = float(int(random.random()*1000))/1000

        #### Return the response
        return response

    def __overlay_clinical_info(self, describe=False):  # TODO: put the default paramas and all that other goodness in
        """
        This function will apply the action overlay_clinical_info.
        Allowable parameters are:
        :return: a response
        """
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        allowable_parameters = {'action': {'overlay_clinical_info'}, 'paired_concept_freq': {'true', 'false'}}

        # A little function to describe what this thing does
        if describe:
            print(allowable_parameters)
            return

        # Make sure only allowable parameters and values have been passed
        self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK':
            return self.response

        # TODO: make sure that not more than one other kind of action has been asked for since COHD has a lot of functionality #606
        # TODO: make sure conflicting defaults aren't called either
        # TODO: until then, just pass the parameters as is

        default_params = self.parameters  # here is where you can set default values

        from Overlay.overlay_clinical_info import OverlayClinicalInfo
        OCI = OverlayClinicalInfo(self.response, self.message, default_params)
        response = OCI.decorate()  # TODO: refactor this so it's basically another apply() like function # 606
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
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'compute_jaccard'},
                                'start_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'intermediate_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'end_node_id': set([x.id for x in self.message.query_graph.nodes]),
                                'virtual_edge_label': {self.parameters['virtual_edge_label'] if 'virtual_edge_label' in self.parameters else "any_string"}
                                }
        else:
            allowable_parameters = {'action': {'compute_jaccard'},
                                    'start_node_id': {"a node id"},
                                    'intermediate_node_id': {"a node id"},
                                    'end_node_id': {"a node id"},
                                    'virtual_edge_label': {"any string label"}
                                    }
        print(allowable_parameters)
        # A little function to describe what this thing does
        if describe:
            print(allowable_parameters)
            return

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

##########################################################################################
def main():

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
        #"overlay(action=overlay_clinical_info, paired_concept_freq=true)",
        "overlay(action=compute_jaccard, start_node_id=qg1, intermediate_node_id=qg1, end_node_id=qg0, virtual_edge_label=J1)",
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

    message_dict = araxdb.getMessage(2)  # acetaminophen2proteins graph
    # message_dict = araxdb.getMessage(13)  # ibuprofen -> proteins -> disease # work computer
    #message_dict = araxdb.getMessage(14)  # pleuropneumonia -> phenotypic_feature # work computer
    # message_dict = araxdb.getMessage(16)  # atherosclerosis -> phenotypic_feature  # work computer
    #message_dict = araxdb.getMessage(5)  # atherosclerosis -> phenotypic_feature  # home computer

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))

    #### Create an overlay object and use it to apply action[0] from the list
    overlay = ARAXOverlay()
    result = overlay.apply(message, actions[0]['parameters'])
    response.merge(result)

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
    print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    #for edge in message.knowledge_graph.edges:
    #    print(edge.edge_attributes.pop().value)
    print(response.show(level=Response.DEBUG))
    #print(actions_parser.parse(actions_list))

if __name__ == "__main__": main()
