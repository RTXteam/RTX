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
from swagger_server.models.query_graph import QueryGraph

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

        # First, extract the sub-query to expand
        query_sub_graph = self.__extract_subgraph_to_expand()
        if response.status != 'OK':
            return response

        # Then answer that query using QueryGraphReasoner
        answer_message = self.__get_answer_to_query_using_kg1(query_sub_graph)
        if response.status != 'OK':
            return response

        # And add answers to overarching knowledge graph
        self.__process_and_merge_results(answer_message)
        if response.status != 'OK':
            return response

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    def __extract_subgraph_to_expand(self):
        sub_query_graph = QueryGraph()
        sub_query_graph.nodes = []
        sub_query_graph.edges = []

        # Grab and validate the edge ID passed in
        qedge_ids_to_expand = self.parameters['edge_id']
        if not qedge_ids_to_expand:
            self.response.error("Expand is missing value for required parameter edge_id", error_code="MissingValue")
        else:
            # Make sure edge ID(s) are stored in a list (can be passed in as a string or a list of strings)
            if type(qedge_ids_to_expand) is not list:
                qedge_ids_to_expand = [qedge_ids_to_expand]

            query_graph = self.message.query_graph
            knowledge_graph = self.message.knowledge_graph

            # Build a query graph with the specified subset of nodes/edges from the larger query graph
            for qedge_id in qedge_ids_to_expand:
                # Make sure this query edge ID actually exists in the larger query graph
                if not any(edge.id == qedge_id for edge in query_graph.edges):
                    self.response.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph", error_code="UnknownValue")
                else:
                    # Grab this query edge and its two nodes
                    qedge_to_expand = next(edge for edge in query_graph.edges if edge.id == qedge_id)
                    qnode_ids = [qedge_to_expand.source_id, qedge_to_expand.target_id]
                    qnodes = [node for node in query_graph.nodes if node.id in qnode_ids]

                    # Handle case where a query node is a set and we need to use answers from a prior Expand()
                    for qnode in qnodes:
                        if qnode.is_set:
                            curies_of_kg_nodes_with_this_qnode_id = [node.id for node in knowledge_graph.nodes if node.qnode_id == qnode.id]
                            if len(curies_of_kg_nodes_with_this_qnode_id):
                                qnode.curie = curies_of_kg_nodes_with_this_qnode_id

                    # Add this edge and its two nodes to our sub query graph, excluding any duplicate nodes
                    sub_query_graph.edges.append(qedge_to_expand)
                    sub_query_graph.nodes += [qnode for qnode in qnodes if not any(node.id == qnode.id for node in sub_query_graph.nodes)]

        return sub_query_graph

    def __get_answer_to_query_using_kg1(self, query_graph):
        q = QueryGraphReasoner()
        self.response.info(f"Sending query graph to QueryGraphReasoner: {query_graph.to_dict()}")
        answer_message = q.answer(query_graph.to_dict(), TxltrApiFormat=True)
        if not answer_message.results:
            self.response.info(f"QueryGraphReasoner found no results for this query graph")
        else:
            kg = answer_message.knowledge_graph
            self.response.info(f"QueryGraphReasoner returned {len(answer_message.results)} results ({len(kg.nodes)} nodes, {len(kg.edges)} edges)")
        return answer_message

    def __process_and_merge_results(self, answer_message):
        if answer_message.results:
            overarching_kg = self.message.knowledge_graph
            answer_nodes = answer_message.knowledge_graph.nodes
            answer_edges = answer_message.knowledge_graph.edges
            query_id_map = self.__build_query_id_map(answer_message.results)

            for node in answer_nodes:
                # Tack this node's corresponding query node ID onto it (needed for later processing)
                node.qnode_id = query_id_map['nodes'].get(node.id)
                if node.qnode_id is None:
                    self.response.warning(f"Node {node.id} is missing a qnode_id")

                # Add this node to the overarching knowledge graph, preventing duplicates
                if any(node.id == existing_node.id for existing_node in overarching_kg.nodes):
                    # TODO: Add additional query node ID onto this node (if different)?
                    pass
                else:
                    overarching_kg.nodes.append(node)

            for edge in answer_edges:
                # Tack this edge's corresponding query edge ID onto it (needed for later processing)
                edge.qedge_id = query_id_map['edges'].get(edge.id)
                if edge.qedge_id is None:
                    self.response.warning(f"Edge {edge.id} is missing a qedge_id")

                # Add this edge to the overarching knowledge graph, preventing duplicates
                if any(edge.id == existing_edge.id for existing_edge in overarching_kg.edges):
                    # TODO: Add additional query edge ID onto this edge (if different)?
                    pass
                else:
                    overarching_kg.edges.append(edge)

    def __build_query_id_map(self, results):
        query_id_map = {'edges': dict(), 'nodes': dict()}

        for result in results:
            for edge_binding in result.edge_bindings:
                for edge_id in edge_binding['kg_id']:
                    qedge_id = edge_binding['qg_id']
                    query_id_map['edges'][edge_id] = qedge_id

            for node_binding in result.node_bindings:
                node_id = node_binding['kg_id']
                qnode_id = node_binding['qg_id']
                query_id_map['nodes'][node_id] = qnode_id

        # TODO: Allow multiple query graph IDs per node/edge?
        return query_id_map

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
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))

if __name__ == "__main__": main()
