#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response


class ARAXOverlay:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None


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

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'compute_ngd': None,
            'add_pubmed_ids': None,
            'compute_confidence_scores': None
        }

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                parameters[key] = value
        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters


        #### Now apply the filters. Order of operations is probably quite important
        #### Scalar value filters probably come first like minimum_confidence, then complex logic filters
        #### based on edge or node properties, and then finally maximum_results
        response.debug(f"Applying Overlay to Message with parameters {parameters}")

        #### Apply compute_ngd task
        if parameters['compute_ngd'] is not None:
            self.__compute_ngd()

        #### Apply add_pubmed_ids task
        # TODO

        #### Apply compute_confidence_scores
        if parameters['compute_confidence_scores'] is not None:
           self.__compute_confidence_scores()

        #### Return the response and done
        return response

    def __compute_ngd(self):
        from Overlay.compute_ngd import ComputeNGD
        ngd_params = self.parameters['compute_ngd']
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
        "overlay(compute_ngd=true)",
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
    message_dict = araxdb.getMessage(2)

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)

    #### Create an overlay object and use it to apply action[0] from the list
    overlay = ARAXOverlay()
    result = overlay.apply(message,actions[0]['parameters'])
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
    print(json.dumps(ast.literal_eval(repr(message)), sort_keys=True, indent=2))
    print(response.show(level=Response.DEBUG))


if __name__ == "__main__": main()
