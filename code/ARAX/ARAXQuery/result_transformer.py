import os
import sys
from typing import List, Set, Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.result import Result
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.auxiliary_graph import AuxiliaryGraph


class ResultTransformer:

    def transform(self, response: ARAXResponse):
        response.info(f"Transforming results to TRAPI 1.4 format (moving 'virtual' nodes/edges to support graphs)")
        response.debug(f"Original input QG was: {response.original_query_graph}")  # TODO: Make more compact
        message = response.envelope.message

        for result in message.results:
            # Find the connected supporting components (includes only edges NOT bound to the original QG)
            supporting_components = self._get_supporting_components(result, response.original_query_graph)
            single_edge_components = []
            multi_edge_components = []
            for component in supporting_components:
                if len(component) == 1:
                    single_edge_components.append(component)
                else:
                    multi_edge_components.append(component)

            # For each component that consists only of a single edge, just add it to its own support graph
            for single_edge_component in single_edge_components:
                self._move_to_support_graph(single_edge_component, result, message.auxiliary_graphs)

            # Add each path in the remaining components as separate support graphs
            for multi_edge_component in multi_edge_components:
                paths = self._get_simple_paths(multi_edge_component)
                for path in paths:
                    self._move_to_support_graph(path, result, message.auxiliary_graphs)

            # TODO: May need to check if handling of non-Infer option_group queries is ok...
        response.info(f"Done transforming results to TRAPI 1.4 format (i.e., using support_graphs)")

    @staticmethod
    def _get_supporting_components(result: Result, original_query_graph: QueryGraph) -> List[Set[str]]:
        # Each component is represented as a set of edge IDs (which fulfill things NOT in the original QG)

        return []

    @staticmethod
    def _get_simple_paths(multi_edge_component: Set[str]) -> List[Set[str]]:
        # Should return list of edge IDs?
        # Find all paths from one 'end' (node in original QG) to another (OTHER node in original QG)
        # Can do this using networkx's nx.all_simple_paths(G, source=x, target=y)
        # Parallel edges that are part of a larger component should probably go in same support graph?

        return []

    @staticmethod
    def _move_to_support_graph(edge_ids: Set[str], result: Result, all_auxiliary_graphs: Dict[str, AuxiliaryGraph]):
        # Create a support graph with these edges, if one doesn't yet exist

        # Delete these edge bindings from the Result

        # Delete any support nodes from the node bindings (nodes not referenced by remaining 'required' edges)

        pass
