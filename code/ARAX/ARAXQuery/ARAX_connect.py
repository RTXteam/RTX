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

    def get_constraint_node(self):
        constraint_node = []
        for key, node in self.message.query_graph.nodes.items():
            if node.categories and len(node.categories) > 0:
                constraint_node.append(key)
        if len(constraint_node) > 1:
            self.response.error(f"For now PathFinder can only handle one constraint node. "
                                f"Number of pinned nodes: {len(constraint_node)}")
        return constraint_node

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

    def get_src_node(self, pinned_nodes):
        for key_node in pinned_nodes:
            for key_edge, edge in self.message.query_graph.edges.items():
                if edge.subject == key_node:
                    return key_node
        self.response.error(f"Could not find source node")

    def get_dst_node(self, pinned_nodes):
        for key_node in pinned_nodes:
            for key_edge, edge in self.message.query_graph.edges.items():
                if edge.object == key_node:
                    return key_node
        self.response.error(f"Could not find destination node")

    def get_q_src_dest_edge_name(self, src_key, dst_key):
        for key_edge, edge in self.message.query_graph.edges.items():
            if edge.subject == src_key and edge.object == dst_key:
                return key_edge
        self.response.error(f"Could not find source to destination edge")

    def get_q_src_mid_edge_name(self, src_key, mid_key):
        for key_edge, edge in self.message.query_graph.edges.items():
            if edge.subject == src_key and edge.object == mid_key:
                return key_edge
        self.response.error(f"Could not find source to constraint edge")

    def get_q_mid_dest_edge_name(self, mid_key, dst_key):
        for key_edge, edge in self.message.query_graph.edges.items():
            if edge.subject == mid_key and edge.object == dst_key:
                return key_edge
        self.response.error(f"Could not find constraint to destination edge")

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
        src_pinned_node = self.get_src_node(pinned_nodes)
        dst_pinned_node = self.get_dst_node(pinned_nodes)
        constraint_node = self.get_constraint_node()[0]
        q_src_dest_edge_name = self.get_q_src_dest_edge_name(src_pinned_node, dst_pinned_node)
        q_src_mid_edge_name = self.get_q_src_mid_edge_name(src_pinned_node, constraint_node)
        q_mid_dest_edge_name = self.get_q_mid_dest_edge_name(constraint_node, dst_pinned_node)
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
            q_src_dest_edge_name=q_src_dest_edge_name,
            q_src_mid_edge_name=q_src_mid_edge_name,
            q_mid_dest_edge_name=q_mid_dest_edge_name,
            result_name="result",
            auxiliary_graph_name="aux",
            kg_src_dest_edge_name="kg_src_dest_edge",
            kg_src_mid_edge_name="kg_src_mid_edge",
            kg_mid_dest_edge_name="kg_mid_dest_edge",
        )
        edge_extractor = EdgeExtractorFromPloverDB(
            RTXConfiguration().plover_url
        )
        ResultPerPathConverter(
            paths,
            normalize_src_node_id,
            normalize_dst_node_id,
            src_pinned_node,
            dst_pinned_node,
            constraint_node,
            names,
            edge_extractor,
            self.message.query_graph.nodes[constraint_node].categories[0]
        ).convert(self.response)

        mode = 'ARAX'
        if mode != "RTXKG2" and not hasattr(self.response, "original_query_graph"):
            self.response.original_query_graph = copy.deepcopy(self.response.envelope.message.query_graph)
        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
