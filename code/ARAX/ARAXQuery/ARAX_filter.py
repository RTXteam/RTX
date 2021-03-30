#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from ARAX_response import ARAXResponse


class ARAXFilter:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None


    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters):

        #### Define a default response
        response = ARAXResponse()
        self.response = response
        self.message = input_message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'maximum_results': None,
            'minimum_confidence': None,
            'start_node': 1
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
        response.debug(f"Applying filter to Message with parameters {parameters}")

        #### First, as a test, blow away the results and see if we can recompute them
        #message.n_results = 0
        #message.results = []
        #self.__recompute_results()

        #### Apply scalar value filters first to do easy things and reduce the problem
        # TODO

        #### Complex logic filters probably come next. These may be hard
        # TODO

        #### Finally, if the maximum_results parameter is set, then limit the number of results to that last
        if parameters['maximum_results'] is not None:
           self.__apply_maximum_results_filter(parameters['maximum_results'])

        #### Return the response
        return response


    #### Apply the maximum_results filter. Double underscore means this is a private method
    def __recompute_results(self):

        #### Set up local references to the response and the message
        response = self.response
        message = self.message

        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=ARAXResponse.DEBUG))
            return response
        print(json.dumps(ast.literal_eval(repr(query_graph_info.node_order)),sort_keys=True,indent=2))



    #### Apply the maximum_results filter. Double underscore means this is a private method
    def __apply_maximum_results_filter(self, maximum_results):

        #### Set up local references to the response and the message
        response = self.response
        message = self.message

        #### Check the input. Null or None is fine and just returned, else must be an int
        if not isinstance(maximum_results, int):
            maximum_results = str(maximum_results)
            if maximum_results.upper() == 'NONE' or maximum_results.upper() == 'NULL':
                response.debug(f"maximum_results is null and not applied")
                return response
            try:
                maximum_results = int(maximum_results)
            except:
                response.error(f"Supplied maximum_results '{maximum_results}' must be an integer", error_code="MaximumResultsInvalid")
                return response
 
        response.debug(f"Applying maximum_results filter")

        #### Verify that n_results is correct and warn if not
        results = message.results
        if len(results) != message.n_results:
            response.warning(f"n_results does not match the number of results in list")
            message.n_results = len(results)

        #### First check for no results
        if message.n_results == 0:
            response.debug(f"n_results is already 0, nothing to do")
            return response

        #### If there are more results than the maximum, then truncate
        if message.n_results > maximum_results:
            response.info(f"Truncating message results from {message.n_results} to {maximum_results}")
            del message.results[maximum_results:]
            message.n_results = len(message.results)

        #### Otherwise nothing to do
        else:
            response.debug(f"Number of message results={message.n_results}, less than {maximum_results} so nothing to do")

        #### Return the response
        return response



##########################################################################################
def main():

    #### Create a response object
    response = ARAXResponse()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
 
    #### Set a simple list of actions
    actions_list = [
        "filter(start_node=1, maximum_results=10, minimum_confidence=0.5)",
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
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()
    message_dict = araxdb.getMessage(2)

    #### The stored message comes back as a dict. Transform it to objects
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
    from swagger_server.models.message import Message
    message = Message().from_dict(message_dict)

    #### Create a filter object and use it to apply action[0] from the list
    filter = ARAXFilter()
    result = filter.apply(message,actions[0]['parameters'])
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response
    response.data = result.data

    #### Show the final message
    print(response.show(level=ARAXResponse.DEBUG))
    response.data['message_stats'] = { 'n_results': message.n_results, 'id': message.id,
        'reasoner_id': message.reasoner_id, 'tool_version': message.tool_version }
    print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    for result in message.results:
        if result.essence is not None:
            essence = result.essence
        else:
            essence = f"{len(result.node_bindings)} node bindings, {len(result.edge_bindings)} edge bindings"
        print(f" - {essence}")
    print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))
    # yet another meaningless comment

if __name__ == "__main__": main()
