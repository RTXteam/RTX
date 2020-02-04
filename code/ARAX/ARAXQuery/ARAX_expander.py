#!/bin/env python3

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import sys
import os
import json
import ast
import re

from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from QueryGraphReasoner import QueryGraphReasoner


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
        message = self.message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'edge_id': None,
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

        # First, extract the query sub-graph that will be expanded
        query_sub_graph = self.__extract_subgraph_to_expand(message)

        # Then answer that query using QueryGraphReasoner
        q = QueryGraphReasoner()
        response.info(f"Sending query graph to QueryGraphReasoner: {query_sub_graph}")
        answer_message = q.answer(query_sub_graph, TxltrApiFormat=True)
        response.info(f"QueryGraphReasoner returned {len(answer_message.results)} results")

        # TODO: Then process results... merge answer knowledge graph with current knowledge graph?
        # For now, storing answer knowledge graph in larger knowledge graph
        message.knowledge_graph = answer_message

        #### Return the response and done
        return response

    # This function is very simple for now (only handles single edge query, etc...will become more complex soon)
    def __extract_subgraph_to_expand(self, message):
        query_graph = message.query_graph
        # Nodes/edges must be dicts for QueryGraphReasoner...says 'not iterable' otherwise
        edge_to_expand = next(edge.to_dict() for edge in query_graph.edges if edge.id == self.parameters['edge_id'])
        node_ids = [edge_to_expand['source_id'], edge_to_expand['target_id']]
        nodes = [node.to_dict() for node in query_graph.nodes if node.id in node_ids]
        sub_query_graph = {'edges': [edge_to_expand], 'nodes': nodes}
        return sub_query_graph



##########################################################################################
def main():

    #### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = Response()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
 
    #### Set a list of actions
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=True, id=n01)",
        "add_qnode(type=drug, id=n02)",
        "add_qedge(source_id=n01, target_id=n00, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=e00)",
        "return(message=true, store=false)",
    ]

    #### Parse the raw action_list into commands and parameters
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    #### Create a Messager and an Expander and execute the command list
    from ARAX_messenger import ARAXMessenger
    messenger = ARAXMessenger()
    expander = ARAXExpander()

    #### Loop over each action and dispatch to the correct place
    for action in actions:
        if action['command'] == 'create_message':
            result = messenger.create()
            message = result.data['message']
            response.data = result.data
        elif action['command'] == 'add_qnode':
            result = messenger.add_qnode(message,action['parameters'])
        elif action['command'] == 'add_qedge':
            result = messenger.add_qedge(message,action['parameters'])
        elif action['command'] == 'expand':
            result = expander.apply(message,action['parameters'])
        elif action['command'] == 'return':
            break
        else:
            response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
            print(response.show(level=Response.DEBUG))
            return response

        #### Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Show the final response
    print(response.show(level=Response.DEBUG))
    print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
