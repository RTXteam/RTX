#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from ARAX_response import ARAXResponse
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

        self.node_map = {}
        self.edge_map = {}


    #### Top level decision maker for applying filters
    def check_for_query_graph_tags(self, message, query_graph_info):

        #### Define a default response
        response = ARAXResponse()
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

        #### Clear the maps
        self.node_map = { 'by_qnode_id': {} }
        self.edge_map = { 'by_qedge_id': {} }

        #### Loop through nodes computing some stats
        n_nodes_with_query_graph_ids = 0
        for node in nodes:
            id = node.id
            if node.qnode_id is None:
                continue
            n_nodes_with_query_graph_ids += 1

            #### Place an entry in the node_map
            if node.qnode_id not in self.node_map['by_qnode_id']:
                self.node_map['by_qnode_id'][node.qnode_id] = {}
            self.node_map['by_qnode_id'][node.qnode_id][id] = 1

        #### Tally the stats
        if n_nodes_with_query_graph_ids == self.n_nodes:
            self.query_graph_id_node_status = 'all nodes have query_graph_ids'
        elif n_nodes_with_query_graph_ids == 0:
            self.query_graph_id_node_status = 'no nodes have query_graph_ids'
        else:
            self.query_graph_id_node_status = 'only some nodes have query_graph_ids'
        response.info(f"In the KnowledgeGraph, {self.query_graph_id_node_status}")

        #### Loop through edges computing some stats
        n_edges_with_query_graph_ids = 0
        for edge in edges:
            id = edge.id
            if edge.qedge_id is None:
                continue
            n_edges_with_query_graph_ids += 1

            #### Place an entry in the edge_map
            if edge.qedge_id not in self.edge_map['by_qedge_id']:
                self.edge_map['by_qedge_id'][edge.qedge_id] = {}
            self.edge_map['by_qedge_id'][edge.qedge_id][id] = 1

        if n_edges_with_query_graph_ids == self.n_edges:
            self.query_graph_id_edge_status = 'all edges have query_graph_ids'
        elif n_edges_with_query_graph_ids == 0:
            self.query_graph_id_edge_status = 'no edges have query_graph_ids'
        else:
            self.query_graph_id_edge_status = 'only some edges have query_graph_ids'
        response.info(f"In the KnowledgeGraph, {self.query_graph_id_edge_status}")

        #### Return the response
        return response



    #### Top level decision maker for applying filters
    def add_query_graph_tags(self, message, query_graph_info):

        #### Define a default response
        response = ARAXResponse()
        self.response = response
        self.message = message
        response.debug(f"Adding temporary QueryGraph ids to KnowledgeGraph")

        #### Get shorter handles
        knowedge_graph = message.knowledge_graph
        nodes = knowedge_graph.nodes
        edges = knowedge_graph.edges

        #### Loop through nodes adding qnode_ids
        for node in nodes:

            #### If there is not qnode_id, then determine what it should be and add it
            if node.qnode_id is None:
                id = node.id
                types = node.type
 
                #### Find a matching type in the QueryGraph for this node
                if types is None:
                    response.error(f"KnowledgeGraph node {id} does not have a type. This should never be", error_code="NodeMissingType")
                    return response
                n_found_types = 0
                found_type = None
                for node_type in types:
                    if node_type in query_graph_info.node_type_map:
                        n_found_types += 1
                        found_type = node_type

                #### If we did not find exactly one matching type, error out
                if n_found_types == 0:
                    response.error(f"Tried to find types '{types}' for KnowledgeGraph node {id} in query_graph_info, but did not find it", error_code="NodeTypeMissingInQueryGraph")
                    return response
                elif n_found_types > 1:
                    response.error(f"Tried to find types '{types}' for KnowledgeGraph node {id} in query_graph_info, and found multiple matches. This is ambiguous", error_code="MultipleNodeTypesInQueryGraph")
                    return response

                #### Else add it
                node.qnode_id = query_graph_info.node_type_map[found_type]

        #### Loop through the edges adding qedge_ids
        for edge in edges:
            id = edge.id

            #### Check to see if there is already a qedge_id attribute on the edge
            if edge.qedge_id is None:

                #### If there isn't a type or can't find it in the query_graph, error out
                if edge.type is None:
                    response.error(f"KnowledgeGraph edge {id} does not have a type. This should never be", error_code="EdgeMissingType")
                    return response
                if edge.type not in query_graph_info.edge_type_map:
                    response.error(f"Tried to find type '{edge.type}' for KnowledgeGraph node {id} in query_graph_info, but did not find it", error_code="EdgeTypeMissingInQueryGraph")
                    return response

                #### Else add it
                edge.qedge_id = query_graph_info.edge_type_map[edge.type]

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
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
 
    #### Asses some information about the QueryGraph
    query_graph_info = QueryGraphInfo()
    result = query_graph_info.assess(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response
    #print(json.dumps(ast.literal_eval(repr(query_graph_info.node_order)),sort_keys=True,indent=2))

    #### Assess some information about the KnowledgeGraph
    knowledge_graph_info = KnowledgeGraphInfo()
    result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    #### Try to add query_graph_ids to the KnowledgeGraph
    result = knowledge_graph_info.add_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    #### Reassess some information about the KnowledgeGraph
    result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response


    print(response.show(level=ARAXResponse.DEBUG))

    tmp = { 'query_graph_id_node_status': knowledge_graph_info.query_graph_id_node_status, 'query_graph_id_edge_status': knowledge_graph_info.query_graph_id_edge_status, 
        'n_nodes': knowledge_graph_info.n_nodes, 'n_edges': knowledge_graph_info.n_edges }
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))




if __name__ == "__main__": main()
