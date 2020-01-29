#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response


class ARAXExpander:

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
            'start_node': 1,
            'steps': 1,
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
        response.debug(f"Applying Expander to Message with parameters {parameters}")

        #### What might we do here? Call another method
        response.warning(f"There's no code here yet, what can we do?")
        # TODO

        #### Return the response and done
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
    actions_list = [
        "expander(start_node=1,steps=1)",
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
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
    from swagger_server.models.message import Message
    message = Message().from_dict(message_dict)

    #### Create an overlay object and use it to apply action[0] from the list
    overlay = ARAXExpander()
    result = overlay.apply(message,actions[0]['parameters'])
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    response.data = result.data

    #### If successful, show the result
    print(response.show(level=Response.DEBUG))
    response.data['message_stats'] = { 'n_results': message.n_results, 'id': message.id,
        'reasoner_id': message.reasoner_id, 'tool_version': message.tool_version }
    print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))


if __name__ == "__main__": main()
