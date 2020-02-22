#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
from datetime import datetime

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.message import Message
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction")
from KGNodeIndex import KGNodeIndex


class ARAXMessenger:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None


    #### Create a fresh Message object and fill with defaults
    def create(self):

        #### Define a default response
        response = Response()
        self.response = response

        #### Create the top-level message
        response.info("Creating an empty template ARAX Message")
        message = Message()
        self.message = message

        #### Fill it with default information
        message.id = None
        message.type = "translator_reasoner_message"
        message.reasoner_id = "ARAX"
        message.tool_version = RTXConfiguration().version
        message.schema_version = "0.9.3"
        message.message_code = "OK"
        message.code_description = "Created empty template Message"
        message.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"

        #### Why is this _datetime ?? FIXME
        message._datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		#### Create an empty master knowledge graph
        message.knowledge_graph = KnowledgeGraph()
        message.knowledge_graph.nodes = []
        message.knowledge_graph.edges = []

		#### Create an empty query graph
        message.query_graph = QueryGraph()
        message.query_graph.nodes = []
        message.query_graph.edges = []

        #### Create empty results
        message.results = []
        message.n_results = 0

        #### Return the response
        response.data['message'] = message
        return response


    #### Add a new QNode
    def add_qnode(self, message, input_parameters):

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'id': None,
            'curie': None,
            'name': None,
            'type': None,
            'is_set': None,
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
        response.info(f"Adding a QueryNode to Message with parameters {parameters}")

        #### Make sure there's a query_graph already here
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.nodes is None:
            message.query_graph.nodes = []

        #### Set up the KGNodeIndex
        kgNodeIndex = KGNodeIndex()

        #### If the CURIE is specified, try to find that
        if parameters['curie'] is not None:
            response.debug(f"Looking up CURIE {parameters['curie']} in KgNodeIndex")
            nodes = kgNodeIndex.get_curies_and_types(parameters['curie'])
            if len(nodes) == 0:
                response.error(f"A node with CURIE {parameters['curie']} is not in our knowledge graph", error_code="UnknownCURIE")
                return response
            qnode = QNode()
            if parameters['id'] is not None:
                id = parameters['id']
            else:
                id = self.__get_next_free_node_id()
            qnode.id = id
            qnode.curie = nodes[0]['curie']
            qnode.type = nodes[0]['type']
            if parameters['is_set'] is not None:
                qnode.is_set = (parameters['is_set'].lower() == 'true')
            message.query_graph.nodes.append(qnode)
            return response

        #### If the name is specified, try to find that
        if parameters['name'] is not None:
            response.debug(f"Looking up CURIE {parameters['name']} in KgNodeIndex")
            nodes = kgNodeIndex.get_curies_and_types(parameters['name'])
            if len(nodes) == 0:
                response.error(f"A node with name '{parameters['name']}'' is not in our knowledge graph", error_code="UnknownCURIE")
                return response
            qnode = QNode()
            if parameters['id'] is not None:
                id = parameters['id']
            else:
                id = self.__get_next_free_node_id()
            qnode.id = id
            qnode.curie = nodes[0]['curie']
            qnode.type = nodes[0]['type']
            if parameters['is_set'] is not None:
                qnode.is_set = (parameters['is_set'].lower() == 'true')
            message.query_graph.nodes.append(qnode)
            return response

        #### If the type is specified, just add that type. There should be checking that it is legal. FIXME
        if parameters['type'] is not None:
            qnode = QNode()
            if parameters['id'] is not None:
                id = parameters['id']
            else:
                id = self.__get_next_free_node_id()
            qnode.id = id
            qnode.type = parameters['type']
            if parameters['is_set'] is not None:
                qnode.is_set = (parameters['is_set'].lower() == 'true')
            message.query_graph.nodes.append(qnode)
            return response

        #### Return the response
        return response


    #### Get the next free node id like nXX where XX is a zero-padded integer starting with 00
    def __get_next_free_node_id(self):

        #### Set up local references to the message and verify the query_graph nodes
        message = self.message
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.nodes is None:
            message.query_graph.nodes = []
        qnodes = message.query_graph.nodes

        #### Loop over the nodes making a dict of the ids
        ids = {}
        for qnode in qnodes:
            id = qnode.id
            ids[id] = 1

        #### Find the first unused id
        index = 0
        while 1:
            pad = '0'
            if index > 9:
                pad = ''
            potential_node_id = f"n{pad}{str(index)}"
            if potential_node_id not in ids:
                return potential_node_id
            index += 1


    #### Add a new QEdge
    def add_qedge(self, message, input_parameters):

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'id': None,
            'source_id': None,
            'target_id': None,
            'type': None,
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
        response.info(f"Adding a QueryEdge to Message with parameters {parameters}")

        #### Make sure there's a query_graph already here
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.edges is None:
            message.query_graph.edges = []

        #### Create a QEdge
        qedge = QEdge()
        if parameters['id'] is not None:
            id = parameters['id']
        else:
            id = self.__get_next_free_edge_id()
        qedge.id = id

        #### Get the list of available node_ids
        qnodes = message.query_graph.nodes
        ids = {}
        for qnode in qnodes:
            id = qnode.id
            ids[id] = 1

        #### Add the source_id
        if parameters['source_id'] is not None:
            if parameters['source_id'] not in ids:
                response.error(f"While trying to add QEdge, there is no QNode with id {parameters['source_id']}", error_code="UnknownSourceId")
                return response
            qedge.source_id = parameters['source_id']
        else:
            response.error(f"While trying to add QEdge, source_id is a required parameter", error_code="MissingSourceId")
            return response

        #### Add the target_id
        if parameters['target_id'] is not None:
            if parameters['target_id'] not in ids:
                response.error(f"While trying to add QEdge, there is no QNode with id {parameters['target_id']}", error_code="UnknownTargetId")
                return response
            qedge.target_id = parameters['target_id']
        else:
            response.error(f"While trying to add QEdge, source_id is a required parameter", error_code="MissingSourceId")
            return response

        #### Add the type if any. Need to verify it's an allowed type. FIXME
        if parameters['type'] is not None:
            qedge.type = parameters['type']

        #### Add it to the query_graph edge list
        message.query_graph.edges.append(qedge)

        #### Return the response
        return response


    #### Get the next free edge id like eXX where XX is a zero-padded integer starting with 00
    def __get_next_free_edge_id(self):

        #### Set up local references to the message and verify the query_graph nodes
        message = self.message
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.edges is None:
            message.query_graph.edges = []
        qedges = message.query_graph.edges

        #### Loop over the nodes making a dict of the ids
        ids = {}
        for qedge in qedges:
            id = qedge.id
            ids[id] = 1

        #### Find the first unused id
        index = 0
        while 1:
            pad = '0'
            if index > 9:
                pad = ''
            potential_edge_id = f"e{pad}{str(index)}"
            if potential_edge_id not in ids:
                return potential_edge_id
            index += 1


    #### Convert a Message as a dict to a Message as objects
    def from_dict(self, message):

        message = Message().from_dict(message)
        message.query_graph = QueryGraph().from_dict(message.query_graph)
        message.knowledge_graph = KnowledgeGraph().from_dict(message.knowledge_graph)
        #new_nodes = []
        #for qnode in message.query_graph.nodes:
        #    print(type(qnode))
        #    new_nodes.append(QNode().from_dict(qnode))
        #message.query_graph.nodes = new_nodes
        #for qedge in message.query_graph.edges:
        #    new_edges.append(QEdge().from_dict(qedge))
        #message.query_graph.edges = new_edges
       #newresults = []
       #for result in message.results
       #KnowledgeGraph().from_dict(message.knowledge_graph)

        return message


    #### Re-create the results[] list based on the QueryGraph and the KnowledgeGraph
    def generate_results(self, message):

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Create a new results list
        results = []

        #### Get QueryGraph information
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

        #### Assess some information about the KnowledgeGraph
        knowledge_graph_info = KnowledgeGraphInfo()
        result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

        #### Figure out where to start
        start_node_qg_id = query_graph_info.start_node['id']
        print(start_node_qg_id)
        for node1 in knowledge_graph_info.node_map[start_node_qg_id]:
            print(node1)

        #Continue here in some recurcive edge following


        return response


##########################################################################################
def main():

    #### Create a response object
    response = Response()

    #### Create a default ARAX Message
    messenger = ARAXMessenger()
    result = messenger.create()
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    message = messenger.message

    #### Some qnode examples
    parameters_sets = [
        { 'curie': 'DOID:9281'},
        { 'name': 'acetaminophen'},
        { 'type': 'protein', 'id': 'n10'},
    ]

    for parameter in parameters_sets:
        #### Add a QNode
        result = messenger.add_qnode(message, parameter)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Some qedge examples
    parameters_sets = [
        { 'source_id': 'n00', 'target_id': 'n01' },
        { 'source_id': 'n01', 'target_id': 'n10', 'type': 'treats' },
   ]

    for parameter in parameters_sets:
        #### Add a QEdge
        result = messenger.add_qedge(message, parameter)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response


    #### Show the final result
    print(response.show(level=Response.DEBUG))
    print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
