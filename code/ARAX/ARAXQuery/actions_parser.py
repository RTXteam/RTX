#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response


class ActionsParser:

    #### Constructor
    def __init__(self):
        pass

    #### Parse the provided action list with validation
    def parse(self, input_actions):

        #### Define a default response
        response = Response()

        #### Basic error checking of the input_actions
        if not isinstance(input_actions, list):
            response.error("Provided input actions is not a list", error_code="ActionsNotList")
            return response
        if len(input_actions) == 0:
            response.error("Provided input actions is an empty list", error_code="ActionsListEmpty")
            return response

        #### Iterate through the list, checking the items
        actions = []
        n_lines = 1
        for action in input_actions:
            response.debug(f"Parsing action: {action}")

            #### First look for a naked command without parentheses
            match = re.match("\s*([A-Za-z_]+)\s*$",action)
            if match is not None:
                action = { "line": n_lines, "command": match.group(1), "parameters": None }
                actions.append(action)

            #### Then parse a command with parentheses and a comma-separated parameter list
            if match is None:
                match = re.match("\s*([A-Za-z_]+)\((.*)\)\s*$",action)
                if match is not None:
                    param_string = match.group(2)

                    #### Split the parameters on comma and process those
                    param_string_list = re.split(",",param_string)
                    parameters = {}
                    for param_item in param_string_list:
                        #### Split on the first = only (might be = in the value)
                        values = re.split("=",param_item,1)
                        key = values[0]
                        #### If there isn't a value after an =, then just set to string true
                        value = 'true'
                        if len(values) > 1:
                            value = values[1]
                        key = key.strip()
                        value = value.strip()
                        parameters[key] = value

                    #### Store the parsed result in a dict and add to the list
                    action = { "line": n_lines, "command": match.group(1), "parameters": parameters }
                    actions.append(action)
                else:
                    response.error(f"Unable to parse action {action}", error_code="ActionsListEmpty")
            n_lines += 1

        #### Put the actions in the response data envelope and return
        response.data["actions"] = actions
        return response


##########################################################################################
def main():

    #### Create an ActionsParser object
    actions_parser = ActionsParser()
 
    #### Set a simple list of actions
    actions_list = [
        "clear_results",
        "evaluate_query_graph",
        "filter(start_node=1, maximum_results=10, minimum_probability=0.5, maximum_ngd=0.8)",
        "overlay(compute_ngd=true,default)",
        "overlay(add_pubmed_ids=true, start_node=2)",
        "return(message=true,store=false)"
    ]

    #### Parse the action_list
    result = actions_parser.parse(actions_list)

    #### Print the response information (including debug information)
    print(result.show(level=Response.DEBUG))

    #### Print the final response data envelope
    print(json.dumps(ast.literal_eval(repr(result.data)),sort_keys=True,indent=2))

if __name__ == "__main__": main()
