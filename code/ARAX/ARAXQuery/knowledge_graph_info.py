#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response
from query_graph_info import QueryGraphInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.edge_attribute import EdgeAttribute


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

        #### Clear the maps
        self.node_map = {}
        self.edge_map = {}

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
                        query_graph_id = attribute.value
                        have_query_graph_id = True
                        #### Also, add this node to a lookup hash by query_graph_id
                        if query_graph_id not in self.node_map:
                            self.node_map[query_graph_id] = []
                        self.node_map[query_graph_id].append(node)
                        break
            if have_query_graph_id:
                n_nodes_with_query_graph_ids += 1

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
            if edge.edge_attributes is None:
                continue
            n_attributes = len(edge.edge_attributes)
            have_query_graph_id = False
            if n_attributes > 0:
                for attribute in edge.edge_attributes:
                    if attribute.name == 'query_graph_id':
                        query_graph_id = attribute.value
                        have_query_graph_id = True
                        #### Also, add this edge to a lookup hash by query_graph_id
                        if query_graph_id not in self.edge_map:
                            self.edge_map[query_graph_id] = []
                        self.edge_map[query_graph_id].append(edge)
                        break
            if have_query_graph_id:
                n_edges_with_query_graph_ids += 1
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
        response = Response()
        self.response = response
        self.message = message
        response.debug(f"Adding temporary QueryGraph ids to KnowledgeGraph")

        #### Get shorter handles
        knowedge_graph = message.knowledge_graph
        nodes = knowedge_graph.nodes
        edges = knowedge_graph.edges

        #### Loop through nodes adding query_graph_ids
        for node in nodes:

            #### Check to see if there is already a query_graph_id attribute on the node
            already_have_query_graph_id = False
            if node.node_attributes is None:
                node.node_attributes = []
            else:
                for attribute in node.node_attributes:
                    if attribute.name == 'query_graph_id':
                        already_have_query_graph_id = True
                        break

            #### If not, then determine what it should be and add it
            if not already_have_query_graph_id:
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
                query_graph_id = query_graph_info.node_type_map[found_type]

                #### And add it
                node_attribute = NodeAttribute()
                node_attribute.name = 'query_graph_id'
                node_attribute.value = query_graph_id
                node.node_attributes.append(node_attribute)


        #### Loop through the edges adding query_graph_ids
        for edge in edges:
            id = edge.id

            #### Check to see if there is already a query_graph_id attribute on the edge
            already_have_query_graph_id = False
            if edge.edge_attributes is None:
                edge.edge_attributes = []
            else:
                for attribute in edge.edge_attributes:
                    if attribute.name == 'query_graph_id':
                        already_have_query_graph_id = True
                        break

            #### If not, then add it
            if not already_have_query_graph_id:

                #### Determine what the query_graph_id should be for this edge
                if edge.type is None:
                    response.error(f"KnowledgeGraph edge {id} does not have a type. This should never be", error_code="EdgeMissingType")
                    return response
                if edge.type not in query_graph_info.edge_type_map:
                    response.error(f"Tried to find type '{edge.type}' for KnowledgeGraph node {id} in query_graph_info, but did not find it", error_code="EdgeTypeMissingInQueryGraph")
                    return response
                query_graph_id = query_graph_info.edge_type_map[edge.type]

            query_graph_id = query_graph_info.edge_type_map[edge.type]
            edge_attribute = EdgeAttribute()
            edge_attribute.name = 'query_graph_id'
            edge_attribute.value = query_graph_id
            edge.edge_attributes.append(edge_attribute)


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
    from ARAX_messenger import ARAXMessenger
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

    #### Try to add query_graph_ids to the KnowledgeGraph
    result = knowledge_graph_info.add_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response

    #### Reassess some information about the KnowledgeGraph
    result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response


    print(response.show(level=Response.DEBUG))

    tmp = { 'query_graph_id_node_status': knowledge_graph_info.query_graph_id_node_status, 'query_graph_id_edge_status': knowledge_graph_info.query_graph_id_edge_status, 
        'n_nodes': knowledge_graph_info.n_nodes, 'n_edges': knowledge_graph_info.n_edges }
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))
    print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))




if __name__ == "__main__": main()
