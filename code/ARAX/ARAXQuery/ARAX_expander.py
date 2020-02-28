#!/bin/env python3


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import sys
import os
import traceback
import json
import ast

from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from QueryGraphReasoner import QueryGraphReasoner


class ARAXExpander:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = {'edge_id': None, 'kp': None}

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        # this is quite different than the `describe_me` in ARAX_overlay and ARAX_filter_kg due to expander being less
        # of a dispatcher (like overlay and filter_kg) and more of a single self contained class
        brief_description = """
`expand` effectively takes a query graph (QG) and reaches out to various knowledge providers (KP's) to find all bioentity subgraphs
that satisfy that QG and augments the knowledge graph (KG) with them. As currently implemented, `expand` can utilize the ARA Expander
team KG1 and KG2 Neo4j instances to fulfill QG's, with functionality built in to reach out to other KP's as they are rolled out.
        """
        description_list = []
        params_dict = dict()
        params_dict['brief_description'] = brief_description
        params_dict['edge_id'] = {"a query graph edge ID or list of such id's (required)"}  # this is a workaround due to how self.parameters is utilized in this class
        params_dict['kp'] = {"the knowledge provider to use - current options are 'ARAX/KG1' or 'ARAX/KG2' (optional, default is ARAX/KG1)"}
        # TODO: will need to update manually if more self.parameters are added
        # eg. params_dict[node_id] = {"a query graph node ID or list of such id's (required)"} as per issue #640
        description_list.append(params_dict)
        return description_list

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
        parameters = self.parameters
        parameters['kp'] = None  # Make sure the kp is reset every time we apply expand

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

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_version_of_kg = self.__convert_standard_kg_to_dict_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = dict_version_of_kg

        # Extract the sub-query to expand
        query_sub_graph = self.__extract_subgraph_to_expand(self.parameters['edge_id'])
        if response.status != 'OK':
            return response

        # Then answer that query using specified knowledge provider
        answer_knowledge_graph = self.__answer_query(query_sub_graph)
        if response.status != 'OK':
            return response

        # And add our answer knowledge graph to the overarching knowledge graph
        self.__merge_answer_kg_into_message_kg(answer_knowledge_graph)
        if response.status != 'OK':
            return response

        # Convert message knowledge graph back to API standard format
        standard_kg = self.__convert_dict_kg_to_standard_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = standard_kg

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"After expansion, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    def __extract_subgraph_to_expand(self, qedge_ids_to_expand):
        """
        This function extracts the portion of the original query graph (stored in message.query_graph) that this current
        expand() call will expand, based on the query edge ID(s) specified.
        :param qedge_ids_to_expand: A single qedge_id (str) OR a list of qedge_ids
        :return: A query graph, in Translator API format
        """
        query_graph = self.message.query_graph
        sub_query_graph = QueryGraph()
        sub_query_graph.nodes = []
        sub_query_graph.edges = []

        # Grab and validate the edge ID(s) passed in
        if not qedge_ids_to_expand:
            self.response.error("Expand is missing value for required parameter edge_id", error_code="MissingValue")
        else:
            # Make sure edge ID(s) are stored in a list (can be passed in as a string or a list of strings)
            if type(qedge_ids_to_expand) is not list:
                qedge_ids_to_expand = [qedge_ids_to_expand]

            for qedge_id in qedge_ids_to_expand:
                # Make sure this query edge ID actually exists in the larger query graph
                if not any(edge.id == qedge_id for edge in query_graph.edges):
                    self.response.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph", error_code="UnknownValue")
                else:
                    # Grab this query edge and its two nodes
                    qedge_to_expand = next(edge for edge in query_graph.edges if edge.id == qedge_id)
                    qnode_ids = [qedge_to_expand.source_id, qedge_to_expand.target_id]
                    qnodes = [node for node in query_graph.nodes if node.id in qnode_ids]

                    # Add (a copy of) this edge to our new query sub graph
                    new_qedge = self.__copy_qedge(qedge_to_expand)
                    sub_query_graph.edges.append(new_qedge)

                    for qnode in qnodes:
                        new_qnode = self.__copy_qnode(qnode)

                        # Handle case where query node is a set and we need to use answers from a prior Expand()
                        if new_qnode.is_set:
                            curies_of_kg_nodes_with_this_qnode_id = [node.id for node_key, node in self.message.knowledge_graph['nodes'].items()
                                                                     if node.qnode_id == new_qnode.id]
                            if len(curies_of_kg_nodes_with_this_qnode_id):
                                new_qnode.curie = curies_of_kg_nodes_with_this_qnode_id

                        # Add this node to our query sub graph if it's not already in there
                        if not any(node.id == new_qnode.id for node in sub_query_graph.nodes):
                            sub_query_graph.nodes.append(new_qnode)

        return sub_query_graph

    def __answer_query(self, query_graph):
        """
        This function answers a query using the specified knowledge provider (KG1 or KG2 for now, with other KPs to be
        added later on.) If no KP was specified, KG1 is used by default.
        :param query_graph: A Translator API standard query graph.
        :return: A knowledge graph containing all the answers to the query.
        """
        kp_to_use = self.parameters['kp']
        querier = None
        # TODO: Add some way of catching when an invalid knowledge provider is entered

        if kp_to_use == 'ARAX/KG2':
            from Expand.kg2_querier import KG2Querier
            querier = KG2Querier(self.response)
        else:
            from Expand.kg1_querier import KG1Querier
            querier = KG1Querier(self.response)

        self.response.info(f"Sending this query graph to {type(querier).__name__}: {query_graph.to_dict()}")
        answer_knowledge_graph = querier.answer_query(query_graph)
        return answer_knowledge_graph

    def __merge_answer_kg_into_message_kg(self, knowledge_graph):
        """
        This function merges a knowledge graph into the overarching knowledge graph (stored in message.knowledge_graph).
        It prevents duplicate nodes/edges in the merged kg.
        :param knowledge_graph: A knowledge graph, in Translator API format.
        :return: None
        """
        answer_nodes = knowledge_graph.get('nodes')
        answer_edges = knowledge_graph.get('edges')
        existing_nodes = self.message.knowledge_graph.get('nodes')
        existing_edges = self.message.knowledge_graph.get('edges')

        for node_key, node in answer_nodes.items():
            # Check if this is a duplicate node
            if existing_nodes.get(node_key):
                # TODO: Add additional query node ID onto this node (if different)?
                pass
            else:
                existing_nodes[node_key] = node

        for edge_key, edge in answer_edges.items():
            # Check if this is a duplicate edge
            if existing_edges.get(edge_key):
                # TODO: Add additional query edge ID onto this edge (if different)?
                pass
            else:
                existing_edges[edge_key] = edge

    def __convert_standard_kg_to_dict_kg(self, knowledge_graph):
        dict_kg = dict()
        dict_kg['nodes'] = dict()
        dict_kg['edges'] = dict()
        for node in knowledge_graph.nodes:
            dict_kg['nodes'][node.id] = node
        for edge in knowledge_graph.edges:
            dict_kg['edges'][edge.id] = edge
        return dict_kg

    def __convert_dict_kg_to_standard_kg(self, dict_kg):
        standard_kg = KnowledgeGraph()
        standard_kg.nodes = []
        standard_kg.edges = []
        for node_key, node in dict_kg.get('nodes').items():
            standard_kg.nodes.append(node)
        for edge_key, edge in dict_kg.get('edges').items():
            standard_kg.edges.append(edge)
        return standard_kg

    def __copy_qedge(self, qedge):
        new_qedge = QEdge()
        new_qedge.id = qedge.id
        new_qedge.type = qedge.type
        new_qedge.negated = qedge.negated
        new_qedge.relation = qedge.relation
        new_qedge.source_id = qedge.source_id
        new_qedge.target_id = qedge.target_id
        return new_qedge

    def __copy_qnode(self, qnode):
        new_qnode = QNode()
        new_qnode.id = qnode.id
        new_qnode.curie = qnode.curie
        new_qnode.type = qnode.type
        new_qnode.is_set = qnode.is_set
        return new_qnode

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
        # "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
        # "add_qnode(id=n01, type=protein, is_set=true)",
        # "add_qedge(id=e00, type=physically_interacts_with, source_id=n00, target_id=n01)",
        # "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        # "add_qnode(id=n01, type=protein, is_set=True)",
        # "add_qnode(id=n02, type=chemical_substance)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00, type=gene_associated_with_condition)",
        # "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        # "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
        # "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
        # "add_qnode(type=disease, is_set=true, id=n02)",
        # "add_qedge(source_id=n01, target_id=n00, id=e00)",
        # "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "add_qnode(id=n00, curie=DOID:824)",
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=phenotypic_feature)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "expand(edge_id=e01)",
        # "expand(edge_id=e00, kp=ARAX/KG1)",
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
            result = messenger.create_message()
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
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))

if __name__ == "__main__": main()
