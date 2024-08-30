import sys

import requests
from RTXConfiguration import RTXConfiguration


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


import os
from collections import Counter
import copy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Path_Finder.converter.EdgeExtractorFromPloverDB import EdgeExtractorFromPloverDB
from Path_Finder.converter.SuperNodeConverter import SuperNodeConverter
from Path_Finder.converter.Names import Names
from Path_Finder.BidirectionalPathFinder import BidirectionalPathFinder

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.knowledge_graph import KnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class ARAXConnect:

    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'connect_nodes',
        }
        self.report_stats = False  # Set this to False when ready to go to production, this is only for debugging purposes

        # parameter descriptions
        self.max_path_length_info = {
            "is_required": False,
            "examples": [2, 3, 5],
            "min": 1,
            "max": 5,
            "type": "integer",
            "description": "The maximum edges to connect two nodes with. If not provided defaults to 2."
        }
        self.qnode_keys_info = {
            "is_required": True,
            "examples": [['n01', 'n02'], []],
            "type": "list",
            "description": "List with just two qnode keys to connect. example: [n1, n2]"
        }
        self.node_category_constraint_info = {
            "is_required": False,
            "examples": ['biolink:Disease', 'biolink:Gene', 'biolink:ChemicalEntity'],
            "type": "string",
            "description": "This constraint will display paths that only pass through the user-specified category."
        }

        # command descriptions
        self.command_definitions = {
            "connect_nodes": {
                "dsl_command": "connect(action=connect_nodes)",
                "description": """
`connect_nodes` Try to find reasonable paths between two bio entities. 

Use cases include:

* finding out how 2 concepts are connected. 
            
You have the option to limit the maximum number of edges in a path (via `max_path_length=<n>`)
                    """,
                'brief_description': """
connect_nodes adds paths between two nodes specified in the query.
                    """,
                "parameters": {
                    "max_path_length": self.max_path_length_info,
                    "qnode_keys": self.qnode_keys_info,
                    "node_category_constraint": self.node_category_constraint_info
                }
            }
        }

    def report_response_stats(self, response):
        """
        Little helper function that will report the KG, QG, and results stats to the debug in the process of executing actions. Basically to help diagnose problems
        """
        message = self.message
        if self.report_stats:
            # report number of nodes and edges, and their type in the QG
            if hasattr(message, 'query_graph') and message.query_graph:
                response.debug(f"Query graph is {message.query_graph}")
            if hasattr(message, 'knowledge_graph') and message.knowledge_graph and hasattr(message.knowledge_graph,
                                                                                           'nodes') and message.knowledge_graph.nodes and hasattr(
                message.knowledge_graph, 'edges') and message.knowledge_graph.edges:
                response.debug(f"Number of nodes in KG is {len(message.knowledge_graph.nodes)}")
                response.debug(
                    f"Number of nodes in KG by type is {Counter([x.categories[0] for x in message.knowledge_graph.nodes.values()])}")  # type is a list, just get the first one
                # response.debug(f"Number of nodes in KG by with attributes are {Counter([x.category for x in message.knowledge_graph.nodes.values()])}")  # don't really need to worry about this now
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(
                    f"Number of edges in KG by type is {Counter([x.predicate for x in message.knowledge_graph.edges.values()])}")
                response.debug(
                    f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges.values() if x.attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges.values():
                    if x.attributes:
                        for attr in x.attributes:
                            if hasattr(attr, "original_attribute_name"):
                                attribute_names.append(attr.original_attribute_name)
                            if hasattr(attr, "attribute_type_id"):
                                attribute_names.append(attr.attribute_type_id)
                response.debug(f"Number of edges in KG by attribute {Counter(attribute_names)}")
        return response

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        return list(self.command_definitions.values())

    def check_params(self, allowable_parameters):
        """
        Checks to see if the input parameters are allowed
        :param input_parameters: input parameters supplied to ARAXOverlay.apply()
        :param allowable_parameters: the allowable parameters
        :return: None
        """
        for key, item in self.parameters.items():
            if key not in allowable_parameters:
                self.response.error(
                    f"Supplied parameter {key} is not permitted. Allowable parameters are: {list(allowable_parameters.keys())}",
                    error_code="UnknownParameter")
                return -1
            elif type(item) == list or type(item) == set:
                for item_val in item:
                    if item_val not in allowable_parameters[key]:
                        self.response.warning(
                            f"Supplied value {item_val} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                        return -1
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in
                        allowable_parameters[key]]):  # if it's a float, just accept it as it is
                    continue
                elif any([type(x) == int for x in allowable_parameters[key]]):
                    continue
                elif any([type(x) == str for x in allowable_parameters[key]]):
                    continue
                else:  # otherwise, it's really not an allowable parameter
                    self.response.warning(
                        f"Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                    return -1

    #### Top level decision maker for applying filters
    def apply(self, input_response, input_parameters):

        self.response = input_response
        self.message = input_response.envelope.message
        if self.message.knowledge_graph is None:
            self.message.knowledge_graph = KnowledgeGraph(nodes=dict(), edges=dict())

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            self.response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return self.response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            self.response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}",
                                error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            self.response.error(
                f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}",
                error_code="UnknownAction")

        #### Return if any of the parameters generated an error (showing not just the first one)
        if self.response.status != 'OK':
            return self.response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        #### Store these final parameters for convenience
        self.response.data['parameters'] = parameters
        self.parameters = parameters

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters[
            'action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        self.response.debug(
            f"Applying Connect to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response

    def __connect_nodes(self, describe=False):
        """
        Connects qnodes and runs expand.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'connect_nodes'},
                                    'max_path_length': {int()},
                                    'node_category_constraint': {str()},
                                    'qnode_keys': set(self.message.query_graph.nodes.keys())
                                    }
        else:
            allowable_parameters = {'action': {'connect_nodes'},
                                    'max_path_length': {
                                        'A maximum path length to use to connect qnodes. Defaults to 2.'},
                                    'node_category_constraint': {
                                        'All paths must include at least one node from this category constraint.'},
                                    'qnode_keys': {'A list with just two query keys to connect'}
                                    }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'qnode_keys' not in self.parameters or len(self.parameters['qnode_keys']) == 0:
            self.parameters['qnode_keys'] = list(set(self.message.query_graph.nodes.keys()))
            if len(self.parameters['qnode_keys']) < 2:
                self.response.error(
                    f"Query graph must have at least 2 nodes to connect.",
                    error_code="QueryGraphError")
        elif len(self.parameters['qnode_keys']) == 1:
            self.response.error(
                f"If qnode keys are provided you must provide at least 2 qnode keys.",
                error_code="ValueError")

        if 'max_path_length' not in self.parameters:
            self.parameters['max_path_length'] = 2
        if 'node_category_constraint' not in self.parameters:
            self.parameters['node_category_constraint'] = ''
        # convert path length to int if it isn't already
        if type(self.parameters['max_path_length']) != int:
            self.parameters['max_path_length'] = int(self.parameters['max_path_length'])

        if self.parameters['max_path_length'] < 1 or self.parameters['max_path_length'] > 5:
            self.response.error(
                f"Maximum path length must be betwen 1 and 5 inclusive.",
                error_code="ValueError")

        if self.response.status != 'OK':
            return self.response

        mode = 'ARAX'

        if len(self.parameters['qnode_keys']) != 2:
            self.response.error(
                f"Connect works with just two qnodes. qnode list size: {len(self.parameters['qnode_keys'])}"
            )
            return self.response

        nodes = {k: v for k, v in self.response.envelope.message.query_graph.nodes.items() if
                 k in self.parameters['qnode_keys']}
        if len(nodes) != 2:
            self.response.error(f"Need to have two nodes to find paths between them. Number of nodes: {len(nodes)}")

        path_finder = BidirectionalPathFinder(
            "NGDSortedNeighborsRepo",
            self.response
        )
        qnode_1_id = self.parameters['qnode_keys'][0]
        qnode_2_id = self.parameters['qnode_keys'][1]
        synonymizer = NodeSynonymizer()
        node_1_id = synonymizer.get_canonical_curies(curies=nodes[qnode_1_id].ids[0])[nodes[qnode_1_id].ids[0]]['preferred_curie']
        node_2_id = synonymizer.get_canonical_curies(curies=nodes[qnode_2_id].ids[0])[nodes[qnode_2_id].ids[0]]['preferred_curie']

        paths = path_finder.find_all_paths(node_1_id, node_2_id, hops_numbers=self.parameters['max_path_length'])

        if len(paths) == 0:
            self.response.warning(f"Could not connect the nodes {qnode_1_id} and {qnode_2_id} "
                                  f"with a max path length of {self.parameters['max_path_length']}.")
            return self.response

        qnode_mid_id = "qnode_mid_id"
        self.response.envelope.message.query_graph.nodes[qnode_mid_id] = QNode(
            ids=[],
            categories=None,
            is_set=False,
            set_interpretation='BATCH',
            set_id=None,
            constraints=[],
            option_group_id=None
        )

        q_edge_src_dest = 'q_edge_src_dest'
        self.response.envelope.message.query_graph.edges[q_edge_src_dest] = QEdge(
            object=qnode_1_id,
            subject=qnode_2_id
        )
        q_edge_src_mid = 'q_edge_src_mid'
        self.response.envelope.message.query_graph.edges[q_edge_src_mid] = QEdge(
            object=qnode_1_id,
            subject=qnode_mid_id
        )
        q_edge_mid_dest = 'q_edge_mid_dest'
        self.response.envelope.message.query_graph.edges[q_edge_mid_dest] = QEdge(
            object=qnode_mid_id,
            subject=qnode_2_id
        )

        names = Names(
            q_src_dest_edge_name=q_edge_src_dest,
            q_src_mid_edge_name=q_edge_src_mid,
            q_mid_dest_edge_name=q_edge_mid_dest,
            result_name="result",
            auxiliary_graph_name="aux",
            kg_src_dest_edge_name="kg_src_dest_edge",
            kg_src_mid_edge_name="kg_src_mid_edge",
            kg_mid_dest_edge_name="kg_mid_dest_edge",
        )
        edge_extractor = EdgeExtractorFromPloverDB(
            RTXConfiguration().plover_url
        )
        SuperNodeConverter(
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            qnode_mid_id,
            names,
            edge_extractor,
            self.parameters['node_category_constraint']
        ).convert(self.response)

        if mode != "RTXKG2" and not hasattr(self.response, "original_query_graph"):
            self.response.original_query_graph = copy.deepcopy(self.response.envelope.message.query_graph)
        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
