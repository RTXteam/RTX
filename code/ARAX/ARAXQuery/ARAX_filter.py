#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response
from actions_parser import ActionsParser


class ARAXFilter:

    #### Constructor
    def __init__(self):
        pass

    #### Destructor
    def __del__(self):
        pass


    #### Define attribute message
    @property
    def message(self) -> str:
        return self._message

    @message.setter
    def message(self, message: str):
        self._message = message


    #### Define attribute parameters
    @property
    def parameters(self) -> str:
        return self._parameters

    @parameters.setter
    def parameters(self, parameters: str):
        self._parameters = parameters


    #### Define attribute response
    @property
    def response(self) -> Response:
        return self._response

    @response.setter
    def response(self, response: Response):
        self._response = response


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
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters

        response.debug(f"Applying filter to Message with parameters {parameters}")

        #### Now apply the filters. Order of operations is probably quite important
        #### Scalar value filters probably come first like minimum_confidence, then complex logic filters
        #### based on edge or node properties, and then finally maximum_results

        #### Apply scalar value filters first to do easy things and reduce the problem
        # TODO

        #### Complex logic filters probably come next. These may be hard
        # TODO

        #### Finally, if the maximum_results parameter is set, then limit the number of results to that last
        if parameters['maximum_results'] is not None:
           self.apply_maximum_results_filter(parameters['maximum_results'])

        #### Return the response
        return response


    #### Top level decision maker for applying filters
    def apply_maximum_results_filter(self, maximum_results):

        #### Set up local handles to the response and the message
        response = self.response
        message = self.message

        #### Check the input
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

        #### Double check the number of results
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

    response = Response()

    #### Create an ActionsParser object
    actions_parser = ActionsParser()
 
    #### Set a simple list of actions
    actions_list = [
        "filter(start_node=1, maximum_results=None, minimum_confidence=0.5)",
        "return(message=true,store=false)"
    ]

    #### Parse the action_list and print the result
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return
    actions = result.data['actions']

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()
    message_dict = araxdb.getMessage(2)
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
    from swagger_server.models.message import Message
    message = Message().from_dict(message_dict)

    #### Create a filter object and use it to apply action[0] from the list
    filter = ARAXFilter()
    result = filter.apply(message,actions[0]['parameters'])
    response.merge(result)
    response.data = result.data
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return

    #### If successful, show the result
    print(response.show(level=Response.DEBUG))
    response.data['message_stats'] = {}
    response.data['message_stats']['n_results'] = message.n_results
    response.data['message_stats']['id'] = message.id
    response.data['message_stats']['reasoner_id'] = message.reasoner_id
    response.data['message_stats']['tool_version'] = message.tool_version
    print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))


if __name__ == "__main__": main()
