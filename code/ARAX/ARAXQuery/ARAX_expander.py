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

        #### Do the actual expansion!
        response.debug(f"Applying Expand to Message with parameters {parameters}")

        # First, extract the query sub-graph that will be expanded
        query_sub_graph = self.__extract_subgraph_to_expand()

        # Then answer that query using QueryGraphReasoner
        answer_message = self.__get_answer_to_query_using_kg1(query_sub_graph)

        # Then process the results (add query graph IDs to each node/edge)
        self.__add_query_graph_ids_to_knowledge_graph(answer_message)

        # And add them to the running knowledge graph
        self.__merge_answer_into_knowledge_graph(answer_message.knowledge_graph)

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"At the end of Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    # This currently handles only single-edge expansion
    def __extract_subgraph_to_expand(self):
        query_graph = self.message.query_graph
        knowledge_graph = self.message.knowledge_graph

        # Note: Nodes/edges must be dicts for QueryGraphReasoner
        qedge_to_expand = next(qedge.to_dict() for qedge in query_graph.edges if qedge.id == self.parameters['edge_id'])
        qnode_ids = [qedge_to_expand['source_id'], qedge_to_expand['target_id']]
        qnodes = [qnode.to_dict() for qnode in query_graph.nodes if qnode.id in qnode_ids]

        # Handle case where a query node is a set, and need to use answers from a prior Expand()
        for qnode in qnodes:
            if qnode['is_set']:
                curies_of_kg_nodes_with_this_qnode_id = [node.id for node in knowledge_graph.nodes if node.qnode_id == qnode['id']]
                if len(curies_of_kg_nodes_with_this_qnode_id):
                    qnode['curie'] = curies_of_kg_nodes_with_this_qnode_id

        sub_query_graph = {'edges': [qedge_to_expand], 'nodes': qnodes}
        return sub_query_graph

    def __get_answer_to_query_using_kg1(self, query_graph):
        q = QueryGraphReasoner()
        self.response.info(f"Sending query graph to QueryGraphReasoner: {query_graph}")
        answer_message = q.answer(query_graph, TxltrApiFormat=True)
        self.response.info(f"QueryGraphReasoner returned {len(answer_message.results)} results")
        return answer_message

    def __add_query_graph_ids_to_knowledge_graph(self, answer_message):
        # Map each node/edge in our answer to its corresponding query node/edge ID
        edge_map = dict()
        node_map = dict()
        for result in answer_message.results:
            for edge_binding in result.edge_bindings:
                edge_id = edge_binding['kg_id'][0]  # TODO! make more robust (scalars, lists...?)
                qedge_id = edge_binding['qg_id']
                edge_map[edge_id] = qedge_id

            for node_binding in result.node_bindings:
                node_id = node_binding['kg_id']  # TODO! make more robust (lists...?)
                qnode_id = node_binding['qg_id']
                node_map[node_id] = qnode_id

        # Add the proper query edge ID onto each edge
        for edge in answer_message.knowledge_graph.edges:
            edge.qedge_id = edge_map.get(edge.id)

        # Add the proper query node ID onto each node
        for node in answer_message.knowledge_graph.nodes:
            node.qnode_id = node_map.get(node.id)

        # TODO: Figure out how to handle potential duplicates here?

    def __merge_answer_into_knowledge_graph(self, answer_knowledge_graph):
        self.message.knowledge_graph.nodes += answer_knowledge_graph.nodes
        self.message.knowledge_graph.edges += answer_knowledge_graph.edges
        # TODO: Figure out how to handle potential duplicates here..


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
        "add_qnode(id=n00, curie=DOID:14330)",
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00, type=gene_associated_with_condition)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=e00)",
        "expand(edge_id=e01)",
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
