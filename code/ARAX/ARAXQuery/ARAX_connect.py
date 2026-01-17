import json
import sys

from RTXConfiguration import RTXConfiguration
from pathfinder.Pathfinder import Pathfinder


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


import os
from collections import Counter
import copy
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Path_Finder.utility import get_curie_ngd_path, get_kg2c_db_path
from Expand.trapi_query_cacher import KPQueryCacher
from ARAX_messenger import ARAXMessenger

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.result import Result
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.path_binding import PathBinding
from openapi_server.models.pathfinder_analysis import PathfinderAnalysis

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../BiolinkHelper/")
from biolink_helper import BiolinkHelper


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

        self.max_pathfinder_paths_info = {
            "is_required": False,
            "examples": 500,
            "min": 1,
            "max": 20000,
            "type": "integer",
            "description": "The maximum number of paths to return. The default is 500."
        }

        self.command_definitions = {
            "connect_nodes": {
                "dsl_command": "connect(action=connect_nodes)",
                "description": """
                    `connect_nodes` Try to find reasonable paths between two bio entities. 
                        You have the option to limit the maximum number of edges in a path (via `max_path_length=<n>`)
                        and the number of paths to return (via `max_pathfinder_paths=<n>`)
                    """,
                'brief_description': "connect_nodes adds paths between two nodes specified in the query.",
                "parameters": {
                    "max_path_length": self.max_path_length_info,
                    "max_pathfinder_paths": self.max_pathfinder_paths_info
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
            if isinstance(allowable_parameters[key], str):
                if allowable_parameters[key] == 'positiveInteger':
                    try:
                        value = int(item)
                        assert value > 0
                        return
                    except:
                        self.response.error(f"Supplied parameter value {key}={item} must be a positive integer")
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

        #### Check the cache to see if we have this query cached already
        start = time.time()
        cacher = KPQueryCacher()
        kp_curie = "PathFinder"
        kp_url = "PathFinder"
        response_envelope_as_dict = self.response.envelope.to_dict()
        cleaned_parameters = self._clean_parameters(parameters)
        pathfinder_input_data = { 'query_graph': response_envelope_as_dict['message']['query_graph'], 'parameters': cleaned_parameters }
        self.response.info(f"Looking for a previously cached result from {kp_curie}")
        response_data, response_code, elapsed_time, error = cacher.get_cached_result(kp_curie, pathfinder_input_data)
        if response_code != -2 and response_code == 200:
            n_results = cacher._get_n_results(response_data)
            self.response.info(f"Found a cached result with response_code={response_code}, n_results={n_results} from the cache in {elapsed_time:.3f} seconds")
            self.response.envelope.message = ARAXMessenger().from_dict(response_data['message'])

            # Hack to explicitly convert the analyses to PathfinderAnalysis objects because this doesn't work automatically. It should. Maybe move this into Messenger? FIXME
            i_analysis = 0
            for analysis_dict in response_data['message']['results'][0]['analyses']:
                analysis_obj = PathfinderAnalysis.from_dict(analysis_dict)
                self.response.envelope.message.results[0].analyses[i_analysis] = analysis_obj
                i_analysis += 1

        else:
            self.response.debug(f"Applying Connect to Message with parameters {parameters}")

            #### This will effectively call __connect_nodes() unless the user injects something else
            result = getattr(self, '_' + self.__class__.__name__ + '__' + parameters[
                'action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

            status = 'OK'
            http_status = 200
            if result is not None and getattr(result, 'http_status', None) is not None:
                http_status = result.http_status
                status = result.status

            #### Store the result into the cache for next time
            elapsed_time = time.time() - start
            self.response.info(f"Got result from ARAX PathFinder Connect after {elapsed_time}. Converting to_dict()")
            response_object = self.response.envelope.to_dict()
            self.response.info(f"Storing resulting dict in the cache")
            cacher.store_response(
                kp_curie=kp_curie,
                query_url=kp_url,
                query_object=pathfinder_input_data,
                response_object=response_object,
                http_code=http_status,
                elapsed_time=elapsed_time,
                status=status
            )
            self.response.info(f"Stored result in the cache.")

        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response


    #### During processing, sometimes these parameters change from a string (of an integer) to an integer, so just force them all to strings for the purpose of cache comparison
    def _clean_parameters(self, parameters):
        cleaned_parameters = parameters.copy()
        if 'max_path_length' in cleaned_parameters:
            cleaned_parameters['max_path_length'] = str(cleaned_parameters['max_path_length'])
        if 'max_pathfinder_paths' in cleaned_parameters:
            cleaned_parameters['max_pathfinder_paths'] = str(cleaned_parameters['max_pathfinder_paths'])
        return cleaned_parameters


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

    def get_constraint_category(self, path):
        if path.constraints is None:
            return None
        if len(path.constraints) == 0:
            return None
        if path.constraints[0].intermediate_categories is None:
            return None
        if len(path.constraints[0].intermediate_categories) == 0:
            return None
        if len(path.constraints[0].intermediate_categories) > 1:
            self.response.error(f"Currently, PathFinder can only handle one constraint node. "
                                f"Number of constraint nodes: {len(path.intermediate_categories)}")

        return path.constraints[0].intermediate_categories[0]

    def __connect_nodes(self, describe=False):
        """
        PathFinder try to find paths between two pinned nodes.
        :return:
        """

        allowable_parameters = {
            'action': {'connect_nodes'},
            'max_path_length': {1, 2, 3, 4, 5},
            'max_pathfinder_paths': 'positiveInteger'
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
        category_constraint = self.get_constraint_category(path)
        if self.response.status != 'OK' or resp == -1:
            return self.response

        normalize_src_node_id = self.get_normalize_nodes(self.message.query_graph.nodes, src_pinned_node)
        normalize_dst_node_id = self.get_normalize_nodes(self.message.query_graph.nodes, dst_pinned_node)

        blocked_curies, blocked_synonyms = self.get_block_list()
        descendants = []
        if category_constraint:
            descendants = set(BiolinkHelper().get_descendants(category_constraint))

        pathfinder = Pathfinder(
            "MLRepo",
            RTXConfiguration().plover_url,
            get_curie_ngd_path(),
            get_kg2c_db_path(),
            blocked_curies,
            blocked_synonyms,
            self.response
        )
        max_pathfinder_paths = 500
        if 'max_pathfinder_paths' in self.parameters:
            max_pathfinder_paths = int(self.parameters['max_pathfinder_paths'])
        try:
            result, aux_graphs, knowledge_graph = pathfinder.get_paths(
                normalize_src_node_id,
                normalize_dst_node_id,
                src_pinned_node,
                dst_pinned_node,
                self.parameters['max_path_length'],
                6,
                max_pathfinder_paths,
                descendants,
            )
        except Exception as e:
            self.response.error(f"PathFinder failed to find paths between {src_pinned_node} and {dst_pinned_node}. "
                                f"Error message is: {e}", http_status=500)
            return self.response

        if len(result['analyses']) == 0:
            self.response.warning(f"Could not connect the nodes {src_pinned_node} and {dst_pinned_node} "
                                  f"with a max path length of {self.parameters['max_path_length']}.")
            return self.response

        self.convert_to_trapi(result, aux_graphs, knowledge_graph)

        mode = 'ARAX'
        if mode != "RTXKG2" and not hasattr(self.response, "original_query_graph"):
            self.response.original_query_graph = copy.deepcopy(self.response.envelope.message.query_graph)
        return self.response

    def get_block_list(self):
        with open(os.path.dirname(os.path.abspath(__file__)) + '/../KnowledgeSources/general_concepts.json',
                  'r') as file:
            json_block_list = json.load(file)
        synonyms = set(s.lower() for s in json_block_list['synonyms'])
        return set(json_block_list['curies']), synonyms

    def convert_to_trapi(self, result, aux_graphs, knowledge_graph):
        if self.response.envelope.message.results is None:
            self.response.envelope.message.results = []

        if self.response.envelope.message.auxiliary_graphs is None:
            self.response.envelope.message.auxiliary_graphs = {}

        if self.response.envelope.message.knowledge_graph is None:
            self.response.envelope.message.knowledge_graph = {}

        kg = KnowledgeGraph().from_dict(knowledge_graph)

        analyses = []
        for analys in result['analyses']:
            path_bindings = {}
            for key, value in analys['path_bindings'].items():
                path_bindings[key] = [PathBinding(id=value[0]['id'])]
            analyses.append(
                PathfinderAnalysis(
                    resource_id=analys["resource_id"],
                    path_bindings=path_bindings,
                    score=analys['score']
                )
            )

        node_bindings = {}
        for key, value in result["node_bindings"].items():
            node_bindings[key] = [NodeBinding(id=value[0]['id'])]
        self.response.envelope.message.results.append(
            Result(
                id=result["id"],
                analyses=analyses,
                node_bindings=node_bindings,
                essence="result"
            )
        )
        for key, value in aux_graphs.items():
            self.response.envelope.message.auxiliary_graphs[key] = AuxiliaryGraph(
                edges=value['edges'],
                attributes=[]
            )
        self.response.envelope.message.knowledge_graph.edges.update(kg.edges)
        self.response.envelope.message.knowledge_graph.nodes.update(kg.nodes)


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
