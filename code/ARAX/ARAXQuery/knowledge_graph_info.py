#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response
from ARAX_messenger import ARAXMessenger
from query_graph_info import QueryGraphInfo


class KnowledgeGraphInfo:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None

        self.n_nodes = None
        self.n_edges = None
        self.query_graph_id_node_status = None
        self.query_graph_id_edge_status = None

    #### Top level decision maker for applying filters
    def check_for_query_graph_tags(self, message, query_graph_info):

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message
        response.debug(f"Checking KnowledgeGraph for QueryGraph tags")

        #### Get shorter handles
        knowedge_graph = message.knowledge_graph
        nodes = knowedge_graph.nodes
        edges = knowedge_graph.edges

        #### Store number of nodes and edges
        self.n_nodes = len(nodes)
        self.n_edges = len(edges)
        response.debug(f"Found {self.n_nodes} nodes and {self.n_edges} edges")

        #### Loop through nodes computing some stats
        n_nodes_with_query_graph_ids = 0
        for node in nodes:
            id = node.id
            if node.node_attributes is None:
                continue
            n_attributes = len(node.node_attributes)
            have_query_graph_id = False
            if n_attributes > 0:
                for attribute in node.node_attributes:
                    if attribute.name == 'query_graph_id':
                        have_query_graph_id = True
                        break
            if have_query_graph_id:
                n_nodes_with_query_graph_ids += 1
        if n_nodes_with_query_graph_ids == self.n_nodes:
            self.query_graph_id_node_status = 'all nodes have query_graph_ids'
        elif n_nodes_with_query_graph_ids == 0:
            self.query_graph_id_node_status = 'no nodes have query_graph_ids'
        else:
            self.query_graph_id_node_status = 'only some nodes have query_graph_ids'
        response.info("In the KnowledgeGraph, {self.query_graph_id_node_status}")

        #### Loop through edges computing some stats
        n_edges_with_query_graph_ids = 0
        for edge in edges:
            id = edge.id
            if edge.edge_attributes is None:
                continue
            n_attributes = len(edge.edge_attributes)
            have_query_graph_id = False
            if n_attributes > 0:
                for attribute in edge.edge_attributes:
                    if attribute.name == 'query_graph_id':
                        have_query_graph_id = True
                        break
            if have_query_graph_id:
                n_edges_with_query_graph_ids += 1
        if n_edges_with_query_graph_ids == self.n_edges:
            self.query_graph_id_edge_status = 'all edges have query_graph_ids'
        elif n_edges_with_query_graph_ids == 0:
            self.query_graph_id_edge_status = 'no edges have query_graph_ids'
        else:
            self.query_graph_id_edge_status = 'only some edges have query_graph_ids'
        response.info("In the KnowledgeGraph, {self.query_graph_id_edge_status}")

        #### Return the response
        return response



##########################################################################################
def main():

    #### Create a response object
    response = Response()

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
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()
    message_dict = araxdb.getMessage(2)

    #### The stored message comes back as a dict. Transform it to objects
    message = ARAXMessenger().from_dict(message_dict)
 
    #### Asses some information about the QueryGraph
    query_graph_info = QueryGraphInfo()
    result = query_graph_info.assess(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    #print(json.dumps(ast.literal_eval(repr(query_graph_info.node_order)),sort_keys=True,indent=2))

    #### Assess some information about the KnowledgeGraph
    knowledge_graph_info = KnowledgeGraphInfo()
    result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response

    tmp = { 'query_graph_id_node_status': knowledge_graph_info.query_graph_id_node_status, 'query_graph_id_edge_status': knowledge_graph_info.query_graph_id_edge_status, 
        'n_nodes': knowledge_graph_info.n_nodes, 'n_edges': knowledge_graph_info.n_edges }
    print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))




if __name__ == "__main__": main()
