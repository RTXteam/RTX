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

        response.debug(f"Applying Expander to Message with parameters {parameters}")

        # First, extract the query sub-graph that will be expanded
        query_sub_graph = self.__extract_subgraph_to_expand()

        # Then answer that query using QueryGraphReasoner
        answer_message = self.__get_answer_to_query_using_kg1(query_sub_graph)

        # Then process the results (add query graph IDs to each node/edge)
        self.__add_query_graph_ids_to_knowledge_graph(answer_message)

        # And add them to the running knowledge graph
        self.__merge_answer_into_knowledge_graph(answer_message.knowledge_graph)

        #### Return the response and done
        return response

    def __extract_subgraph_to_expand(self):
        # TODO: Add to this function so it can handle is_set=True nodes, multiple edge queries, etc.
        query_graph = self.message.query_graph
        # Nodes/edges must be dicts for QueryGraphReasoner...says 'not iterable' otherwise
        edge_to_expand = next(edge.to_dict() for edge in query_graph.edges if edge.id == self.parameters['edge_id'])
        node_ids = [edge_to_expand['source_id'], edge_to_expand['target_id']]
        nodes = [node.to_dict() for node in query_graph.nodes if node.id in node_ids]
        sub_query_graph = {'edges': [edge_to_expand], 'nodes': nodes}
        return sub_query_graph

    def __get_answer_to_query_using_kg1(self, query_graph):
        q = QueryGraphReasoner()
        self.response.info(f"Sending query graph to QueryGraphReasoner: {query_graph}")
        answer_message = q.answer(query_graph, TxltrApiFormat=True)
        self.response.info(f"QueryGraphReasoner returned {len(answer_message.results)} results")
        return answer_message

    def __add_query_graph_ids_to_knowledge_graph(self, answer_message):
        # TODO: Extract query graph ID from bindings in results, and attach to each node/edge in KG
        pass

    def __merge_answer_into_knowledge_graph(self, answer_knowledge_graph):
        # Handle case when message knowledge graph is empty
        if len(self.message.knowledge_graph.nodes) == 0:
            self.response.debug("Message knowledge graph is empty at this point; setting equal to answer knowledge graph")
            self.message.knowledge_graph = answer_knowledge_graph
        else:
            # TODO: Merge this KG with whatever is currently in the message KG
            self.response.debug("Should merge answer into message knowledge graph here")



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
    # now you can see the expander branch

if __name__ == "__main__": main()
