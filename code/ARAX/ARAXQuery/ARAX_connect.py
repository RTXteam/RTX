import sys

from RTXConfiguration import RTXConfiguration


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


import os
from collections import Counter
import copy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Path_Finder.converter.EdgeExtractorFromPloverDB import EdgeExtractorFromPloverDB
from Path_Finder.converter.ResultPerPathConverter import ResultPerPathConverter
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

        # Set this to False when ready to go to production, this is only for debugging purposes
        self.report_stats = False

        self.max_path_length_info = {
            "is_required": False,
            "examples": [2, 3, 5],
            "min": 1,
            "max": 5,
            "type": "integer",
            "description": "The maximum edges to connect two nodes with. If not provided defaults to 4."
        }

        self.command_definitions = {
            "connect_nodes": {
                "dsl_command": "connect(action=connect_nodes)",
                "description": """
                    `connect_nodes` Try to find reasonable paths between two bio entities. 
                        You have the option to limit the maximum number of edges in a path (via `max_path_length=<n>`)
                    """,
                'brief_description': "connect_nodes adds paths between two nodes specified in the query.",
                "parameters": {
                    "max_path_length": self.max_path_length_info
                }
            }
        }

    def report_response_stats(self, response):
        """
        Little helper function that will report the KG, QG, and results stats to the debug in the process of executing actions. Basically to help diagnose problems
        """
        message = self.message
        if self.report_stats:

            if hasattr(message, 'query_graph') and message.query_graph:
                response.debug(f"Query graph is {message.query_graph}")

            if (hasattr(message, 'knowledge_graph') and
                    message.knowledge_graph and
                    hasattr(message.knowledge_graph, 'nodes') and
                    message.knowledge_graph.nodes and
                    hasattr(message.knowledge_graph, 'edges') and
                    message.knowledge_graph.edges):

                response.debug(f"Number of nodes in KG is {len(message.knowledge_graph.nodes)}")
                response.debug(
                    f"Number of nodes in KG by type is "
                    f"{Counter([x.categories[0] for x in message.knowledge_graph.nodes.values()])}")
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(
                    f"Number of edges in KG by type is "
                    f"{Counter([x.predicate for x in message.knowledge_graph.edges.values()])}")
                response.debug(
                    f"Number of edges in KG with attributes is "
                    f"{len([x for x in message.knowledge_graph.edges.values() if x.attributes])}")

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
            if item not in allowable_parameters[key]:
                if any([type(x) == int for x in allowable_parameters[key]]):
                    continue
                else:
                    self.response.error(
                        f"Supplied value {item} is not permitted. In action "
                        f"{allowable_parameters['action']}, "
                        f"allowable values to {key} are: {list(allowable_parameters[key])}")
                    return -1

    def apply(self, input_response, input_parameters):

        self.response = input_response
        self.message = input_response.envelope.message
        if self.message.knowledge_graph is None:
            self.message.knowledge_graph = KnowledgeGraph(nodes=dict(), edges=dict())

        if not isinstance(input_parameters, dict):
            self.response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return self.response

        allowable_actions = self.allowable_actions

        if 'action' not in input_parameters:
            self.response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}",
                                error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            self.response.error(
                f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}",
                error_code="UnknownAction")

        if self.response.status != 'OK':
            return self.response

        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        self.response.data['parameters'] = parameters
        self.parameters = parameters

        getattr(self, '_' + self.__class__.__name__ + '__' + parameters[
            'action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        self.response.debug(f"Applying Connect to Message with parameters {parameters}")

        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response

    def get_pinned_nodes(self):
        pinned_nodes = []
        for key, node in self.message.query_graph.nodes.items():
            if node.ids and len(node.ids) > 0:
                pinned_nodes.append(key)
        if len(pinned_nodes) != 2:
            self.response.error(f"Query graph must have exactly 2 pinned nodes to connect. "
                                f"Number of pinned nodes: {len(pinned_nodes)}")
        return pinned_nodes



    def get_normalize_nodes(self, nodes, pinned_qnode_id):
        synonymizer = NodeSynonymizer()
        try:
            return synonymizer.get_canonical_curies(
                curies=nodes[pinned_qnode_id].ids[0])[nodes[pinned_qnode_id].ids[0]]['preferred_curie']
        except Exception as e:
            self.response.error(f"PathFinder could not get canonical CURIE for the node: {pinned_qnode_id}"
                                f" with id: {nodes[pinned_qnode_id].ids[0]}."
                                f" You need to provide id (CURIE) or name for this node."
                                f" Error message is: {e}")
            return self.response

    def get_path(self):
        if not self.message.query_graph.paths:
            self.response.error(f"Query graph does not have paths argument. Paths is None")
        if len(self.message.query_graph.paths) != 1:
            self.response.error(f"Query graph has more than one path. This is not supported yet.")
        path = next(iter(self.message.query_graph.paths.values()))
        if path.subject is None:
            self.response.error(f"The path does not have a subject.")
        if path.object is None:
            self.response.error(f"The path does not have a subject.")
        return path

    def get_src_node(self, pinned_nodes, path):
        for pinned_node in pinned_nodes:
            if path.subject == pinned_node:
                return path.subject
        self.response.error(f"Pathfinder cannot find {path.subject} in pinned nodes.")

    def get_dst_node(self, pinned_nodes, path):
        for pinned_node in pinned_nodes:
            if path.object == pinned_node:
                return path.object
        self.response.error(f"Pathfinder cannot find {path.object} in pinned nodes.")

    def get_constraint_node(self, path):
        if len(path.intermediate_nodes) > 1:
            self.response.error(f"Currently, PathFinder can only handle one constraint node. "
                                f"Number of constraint nodes: {len(path.intermediate_nodes)}")
        if len(path.intermediate_nodes) == 0:
            return None

        constraint_qnode = path.intermediate_nodes[0]

        for key, node in self.message.query_graph.nodes.items():
            if node.categories and len(node.categories) > 0:
                if constraint_qnode == key:
                    return constraint_qnode

        self.response.error(
            f"Intermediate node: {constraint_qnode} is not defined in the nodes list.")

    def __connect_nodes(self, describe=False):
        """
        PathFinder try to find paths between two pinned nodes.
        :return:
        """

        allowable_parameters = {
            'action': {'connect_nodes'},
            'max_path_length': {1, 2, 3, 4, 5}
        }
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        if 'max_path_length' not in self.parameters:
            self.parameters['max_path_length'] = 4
        if type(self.parameters['max_path_length']) != int:
            self.parameters['max_path_length'] = int(self.parameters['max_path_length'])
        if self.parameters['max_path_length'] < 1 or self.parameters['max_path_length'] > 5:
            self.response.error(f"Maximum path length must be between 1 and 5 inclusive.", error_code="ValueError")
        if self.response.status != 'OK':
            return self.response

        resp = self.check_params(allowable_parameters)
        if self.response.status != 'OK' or resp == -1:
            return self.response

        pinned_nodes = self.get_pinned_nodes()
        path = self.get_path()
        src_pinned_node = self.get_src_node(pinned_nodes, path)
        dst_pinned_node = self.get_dst_node(pinned_nodes, path)
        constraint_node = self.get_constraint_node(path)
        if self.response.status != 'OK' or resp == -1:
            return self.response

        normalize_src_node_id = self.get_normalize_nodes(self.message.query_graph.nodes, src_pinned_node)
        normalize_dst_node_id = self.get_normalize_nodes(self.message.query_graph.nodes, dst_pinned_node)

        path_finder = BidirectionalPathFinder(
            "MLRepo",
            self.response
        )
        paths = path_finder.find_all_paths(
            normalize_src_node_id,
            normalize_dst_node_id,
            hops_numbers=self.parameters['max_path_length']
        )

        self.response.debug(f"PathFinder found {len(paths)} paths")

        if len(paths) == 0:
            self.response.warning(f"Could not connect the nodes {src_pinned_node} and {dst_pinned_node} "
                                  f"with a max path length of {self.parameters['max_path_length']}.")
            return self.response

        names = Names(
            result_name="result",
            auxiliary_graph_name="aux",
        )
        edge_extractor = EdgeExtractorFromPloverDB(
            RTXConfiguration().plover_url
        )
        category_constraint = None
        if constraint_node:
            category_constraint = self.message.query_graph.nodes[constraint_node].categories[0]
        ResultPerPathConverter(
            paths,
            normalize_src_node_id,
            normalize_dst_node_id,
            src_pinned_node,
            dst_pinned_node,
            constraint_node,
            names,
            edge_extractor,
            category_constraint
        ).convert(self.response)

        mode = 'ARAX'
        if mode != "RTXKG2" and not hasattr(self.response, "original_query_graph"):
            self.response.original_query_graph = copy.deepcopy(self.response.envelope.message.query_graph)
        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
