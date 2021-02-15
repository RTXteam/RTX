#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from ARAX_response import ARAXResponse


class ActionsParser:

    #### Constructor
    def __init__(self):
        pass

    #### Parse the provided action list with validation
    def parse(self, input_actions):

        #### Define a default response
        response = ARAXResponse()
        response.info(f"Parsing input actions list")

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

            # If this line is empty, then skip
            match = re.match(r"\s*$",action)
            if match:
                continue

            # If this line begins with a #, it is a comment, then skip
            match = re.match(r"#",action)
            if match:
                continue

            #### First look for a naked command without parentheses
            match = re.match(r"\s*([A-Za-z_]+)\s*$",action)
            if match is not None:
                action = { "line": n_lines, "command": match.group(1), "parameters": None }
                actions.append(action)

            #### Then look for and parse a command with parentheses and a comma-separated parameter list
            if match is None:
                match = re.match(r"\s*([A-Za-z_]+)\((.*)\)\s*$",action)
                if match is not None:
                    command = match.group(1)
                    param_string = match.group(2)

                    #### Split the parameters on comma and process those
                    param_string_list = re.split(",",param_string)
                    parameters = {}

                    #### If a value is of the form key=[value1,value2] special code is needed to recompose that
                    mode = 'normal'
                    list_buffer = []
                    key = ''
                    for param_item in param_string_list:
                        param_item = param_item.strip()
                        if mode == 'normal':

                            #### Split on the first = only (might be = in the value)
                            values = re.split("=",param_item,1)
                            key = values[0]
                            #### If there isn't a value after an =, then just set to string true
                            value = 'true'
                            if len(values) > 1:
                                value = values[1]
                            key = key.strip()
                            value = value.strip()

                            #### If the value begins with a "[", then this is a list
                            match = re.match(r"\[(.+)$",value)
                            if match:
                                #### If it also ends with a "]", then this is a list of one element
                                match2 = re.match(r"\[(.*)\]$",value)
                                if match2:
                                    if match2.group(1) == '':
                                        parameters[key] = [ ]
                                    else:
                                        parameters[key] = [ match2.group(1) ]
                                else:
                                    mode = 'in_list'
                                    list_buffer = [ match.group(1) ]
                            else:
                                parameters[key] = value

                        #### Special processing if we're in the middle of a list
                        elif mode == 'in_list':
                            match = re.match(r"(.*)\]$",param_item)
                            if match:
                                mode = 'normal'
                                list_buffer.append(match.group(1))
                                parameters[key] = list_buffer
                            else:
                                list_buffer.append(param_item)
                        else:
                            eprint("Inconceivable!")
                    if mode == 'in_list':
                        parameters[key] = list_buffer

                    #### Store the parsed result in a dict and add to the list
                    action = { "line": n_lines, "command": command, "parameters": parameters }
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
        "expand(command=expand_nodes, edge_id=[e00,e01,e02], add_virtual_nodes=true)",
        "expand(edge_id=[e00,e01,e02], sort_by=[type,name])",
        "expand(edge_id=[e00], sort_by=[type], empty_list=[] , dangling_comma=[p,q,])",
        "overlay(compute_ngd=true,default)",
        "overlay(add_pubmed_ids=true, start_node=2)",
        "return(message=true,store=false,test=accept=true)"
    ]

    #### Parse the action_list
    result = actions_parser.parse(actions_list)

    #### Print the response information (including debug information)
    print(result.show(level=ARAXResponse.DEBUG))

    #### Print the final response data envelope
    print(json.dumps(ast.literal_eval(repr(result.data)),sort_keys=True,indent=2))

if __name__ == "__main__": main()
