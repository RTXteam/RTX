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
        edge_id = self.parameters['edge_id']
        edges_to_expand_string = f"edges {', '.join(edge_id)}" if type(edge_id) is list else f"edge {edge_id}"
        response.info(f"Beginning expansion of {edges_to_expand_string} using {self.parameters['kp']}")

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_version_of_kg = self.__convert_standard_kg_to_dict_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = dict_version_of_kg

        self.response.debug("Extracting sub query graph to expand")
        query_sub_graph = self.__extract_subgraph_to_expand(self.parameters['edge_id'])
        if response.status != 'OK':
            return response
        self.response.debug(f"Query graph to expand is: {query_sub_graph.to_dict()}")

        # Expand the query graph edge by edge because it's much faster for neo4j queries
        ordered_edges = self.__get_order_to_expand_edges_in(query_sub_graph)
        for edge in ordered_edges:
            self.response.info(f"Expanding edge {edge.id}")
            edge_query_graph = self.__extract_subgraph_to_expand(edge.id)

            answer_knowledge_graph = self.__answer_query(edge_query_graph, self.parameters['kp'])
            if response.status != 'OK':
                return response

            self.__merge_answer_kg_into_message_kg(answer_knowledge_graph)
            if response.status != 'OK':
                return response

        # Convert message knowledge graph back to API standard format
        standard_kg = self.__convert_dict_kg_to_standard_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = standard_kg

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    def __extract_subgraph_to_expand(self, qedge_ids_to_expand):
        """
        This function extracts the portion of the original query graph (stored in message.query_graph) that this current
        expand() call will expand, based on the query edge ID(s) specified.
        :param qedge_ids_to_expand: A single qedge_id (str) OR a list of qedge_ids.
        :return: A query graph, in Translator API standard format.
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
                if not any(qedge.id == qedge_id for qedge in query_graph.edges):
                    self.response.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph",
                                        error_code="UnknownValue")
                else:
                    # Grab this query edge and its two nodes
                    qedge_to_expand = next(qedge for qedge in query_graph.edges if qedge.id == qedge_id)
                    qnode_ids = [qedge_to_expand.source_id, qedge_to_expand.target_id]
                    qnodes = [qnode for qnode in query_graph.nodes if qnode.id in qnode_ids]

                    # Add (a copy of) this edge to our new query sub graph
                    new_qedge = self.__copy_qedge(qedge_to_expand)
                    if not any(qedge.id == new_qedge.id for qedge in sub_query_graph.edges):
                        sub_query_graph.edges.append(new_qedge)

                    # Check for (unusual) case in which this edge has already been expanded (e.g., in a prior Expand() call)
                    edge_has_already_been_expanded = False
                    if any(node.qnode_id == qnodes[0].id for node in self.message.knowledge_graph['nodes'].values()) and \
                            any(node.qnode_id == qnodes[1].id for node in self.message.knowledge_graph['nodes'].values()):
                        edge_has_already_been_expanded = True

                    # Add (copies of) this edge's two nodes to our new query sub graph
                    for qnode in qnodes:
                        new_qnode = self.__copy_qnode(qnode)

                        # Handle case where we need to use nodes found in a prior Expand() as the curie for this qnode
                        if not new_qnode.curie and not edge_has_already_been_expanded:
                            curies_of_kg_nodes_with_this_qnode_id = [node.id for node in
                                                                     self.message.knowledge_graph['nodes'].values()
                                                                     if node.qnode_id == new_qnode.id]
                            if curies_of_kg_nodes_with_this_qnode_id:
                                new_qnode.curie = curies_of_kg_nodes_with_this_qnode_id

                        if not any(qnode.id == new_qnode.id for qnode in sub_query_graph.nodes):
                            sub_query_graph.nodes.append(new_qnode)

        return sub_query_graph

    def __get_order_to_expand_edges_in(self, query_graph):
        edges_remaining = [edge for edge in query_graph.edges]
        ordered_edges = []
        while edges_remaining:
            if not ordered_edges:
                # Start with an edge that has a node with a curie specified
                edge_with_curie = self.__get_edge_with_curie_node(query_graph)
                first_edge = edge_with_curie if edge_with_curie else edges_remaining[0]
                ordered_edges = [first_edge]
                edges_remaining.pop(edges_remaining.index(first_edge))
            else:
                # Add connected edges in a rightward direction if possible
                right_end_edge = ordered_edges[-1]
                edge_connected_to_right_end = self.__find_connected_edge(edges_remaining, right_end_edge)
                if edge_connected_to_right_end:
                    ordered_edges.append(edge_connected_to_right_end)
                    edges_remaining.pop(edges_remaining.index(edge_connected_to_right_end))
                else:
                    left_end_edge = ordered_edges[0]
                    edge_connected_to_left_end = self.__find_connected_edge(edges_remaining, left_end_edge)
                    if edge_connected_to_left_end:
                        ordered_edges.insert(0, edge_connected_to_left_end)
                        edges_remaining.pop(edges_remaining.index(edge_connected_to_left_end))
        return ordered_edges

    def __answer_query(self, query_graph, kp_to_use):
        """
        This function answers a query using the specified knowledge provider (KG1 or KG2 for now, with other KPs to be
        added later on.) If no KP was specified, KG1 is used by default. (Eventually it will be possible to automatically
        determine which KP to use.)
        :param query_graph: A Translator API standard query graph.
        :param kp_to_use: A string representing the knowledge provider to fulfill this query with.
        :return: An (almost) Translator API standard knowledge graph (dictionary version).
        """
        valid_kps = ['ARAX/KG2', 'ARAX/KG1']

        if kp_to_use in valid_kps or kp_to_use is None:
            querier = None
            if kp_to_use == 'ARAX/KG2':
                from Expand.kg2_querier import KG2Querier
                querier = KG2Querier(self.response)
            else:
                from Expand.kg1_querier import KG1Querier
                querier = KG1Querier(self.response)

            self.response.debug(f"Sending edge query graph to {type(querier).__name__}: {query_graph.to_dict()}")
            answer_knowledge_graph = querier.answer_query(query_graph)
            return answer_knowledge_graph
        else:
            self.response.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are: "
                                f"{', '.join(valid_kps)} (or you can omit this parameter).", error_code="UnknownValue")
            return None

    def __merge_answer_kg_into_message_kg(self, knowledge_graph):
        """
        This function merges a knowledge graph into the overarching knowledge graph (stored in message.knowledge_graph).
        It prevents duplicate nodes/edges in the merged kg.
        :param knowledge_graph: An (almost) Translator API standard knowledge graph (dictionary version).
        :return: None
        """
        self.response.debug("Merging results into Message.KnowledgeGraph")
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
                # TODO: Fix how we're identifying edges (edge.id doesn't work when using multiple KPs)
                pass
            else:
                existing_edges[edge_key] = edge

    def __get_edge_with_curie_node(self, query_graph):
        for edge in query_graph.edges:
            source_node = self.__get_query_node(query_graph, edge.source_id)
            target_node = self.__get_query_node(query_graph, edge.target_id)
            if source_node.curie or target_node.curie:
                return edge
        return None

    def __find_connected_edge(self, edge_list, edge):
        edge_node_ids = {edge.source_id, edge.target_id}
        for potential_connected_edge in edge_list:
            potential_connected_edge_node_ids = {potential_connected_edge.source_id, potential_connected_edge.target_id}
            if edge_node_ids.intersection(potential_connected_edge_node_ids):
                return potential_connected_edge
        return None

    def __get_query_node(self, query_graph, qnode_id):
        for node in query_graph.nodes:
            if node.id == qnode_id:
                return node
        return None

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

    def __copy_qedge(self, old_qedge):
        new_qedge = QEdge()
        for edge_property in new_qedge.to_dict():
            value = getattr(old_qedge, edge_property)
            setattr(new_qedge, edge_property, value)
        return new_qedge

    def __copy_qnode(self, old_qnode):
        new_qnode = QNode()
        for node_property in new_qnode.to_dict():
            value = getattr(old_qnode, node_property)
            setattr(new_qnode, node_property, value)
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
        # "add_qedge(id=e00, source_id=n00, target_id=n01, type=molecularly_interacts_with)",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        # "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
        # "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
        # "add_qnode(type=disease, is_set=true, id=n02)",
        # "add_qedge(source_id=n01, target_id=n00, id=e00)",
        # "add_qedge(source_id=n01, target_id=n02, id=e01)",
        # "add_qnode(id=n00, curie=DOID:824)",  # periodontitis
        # "add_qnode(id=n01, type=protein, is_set=True)",
        # "add_qnode(id=n02, type=phenotypic_feature)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00)",
        # "add_qedge(id=e01, source_id=n01, target_id=n02)",
        # "add_qnode(id=n00, curie=DOID:0060227)",  # Adams-Oliver
        # "add_qnode(id=n01, type=protein)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00)",
        # "add_qnode(id=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
        # "add_qnode(id=n01, type=chemical_substance)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00)",
        # "expand(edge_id=e00, kp=ARAX/KG2)",
        # "expand(edge_id=e00, kp=ARAX/KG2)",
        # "expand(edge_id=e01, kp=ARAX/KG2)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
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
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))
    print(response.show(level=Response.DEBUG))


if __name__ == "__main__":
    main()
