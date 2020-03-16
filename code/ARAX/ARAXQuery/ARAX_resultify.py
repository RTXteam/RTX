#!/usr/bin/env python3
'''This module defines the `ARAXResultify` class whose `__resultify` method
enumerates subgraphs of a knowledge graph (KG) that match a pattern set by a
query graph (QG) and sets the `results` data attribute of the `message` object
to be a list of `Result` objects, each corresponding to one of the enumerated
subgraphs. The matching between the KG subgraphs and the QG can be forced to be
sensitive to edge direction by setting `ignore_edge_direction=false` (the
default is to ignore edge direction). If any query nodes in the QG have the
`is_set` property set to `true`, this can be overridden in `resultify` by
including the query node `id` string (or the `id` fields of more than one query
node) in a parameter `force_isset_false` of type `List[str]`.

   Usage: python3 -u ARAX_resultify.py

   will run the built-in tests for ARAX_resultify.py. When testing, also be sure
   to run the `document_dsl_commands.py` script in the `code/ARAX/Documentation`
   directory since that script uses the `describe_me` method of this module.

'''

import collections
import itertools
import math
import os
import sys
from typing import List, Dict, Set, Union
from response import Response

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'David Koslicki', 'Eric Deutsch']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'


# is there a better way to import swagger_server?  Following SO posting 16981921
PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.node_binding import NodeBinding
from swagger_server.models.edge_binding import EdgeBinding
from swagger_server.models.biolink_entity import BiolinkEntity
from swagger_server.models.result import Result
from swagger_server.models.message import Message


# define a string-parameterized BiolinkEntity class
class BiolinkEntityStr(BiolinkEntity):
    def __init__(self, category_label: str):
        super().__init__()
        self.category_label = category_label

    def __str__(self):
        return super().__str__() + ":" + self.category_label


# define a map between category_label and BiolinkEntity object
BIOLINK_CATEGORY_LABELS = {'protein', 'disease', 'phenotypic_feature', 'gene', 'chemical_substance'}
BIOLINK_ENTITY_TYPE_OBJECTS = {category_label: BiolinkEntityStr(category_label) for
                               category_label in BIOLINK_CATEGORY_LABELS}


class ARAXResultify:
    ALLOWED_PARAMETERS = {'debug', 'force_isset_false', 'ignore_edge_direction'}

    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """

        brief_description = """ Creates a list of results from the input query graph (QG) based on the the information contained in the message knowledge graph (KG). Every subgraph through the KG that satisfies the GQ is returned. Such use cases include: 
- `resultify()` Returns all subgraphs in the knowledge graph that satisfy the query graph
- `resultify(force_isset_false=[n01])` This forces each result to include only one example of node `n01` if it was originally part of a set in the QG. An example where one might use this mode is: suppose that the preceding DSL commands constructed a knowledge graph containing several proteins that are targets of a given drug, by making the protein node (suppose it is called `n01`) on the query graph have `is_set=true`. To extract one subgraph for each such protein, one would use `resultify(force_isset_false=[n01])`. The brackets around `n01` are because it is a list; in fact, multiple node IDs can be specified there, if they are separated by commas.
- `resultiy(ignore_edge_direction=false)` This mode checks edge directions in the QG to ensure that matching an edge in the KG to an edge in the QG is only allowed if the two edges point in the same direction. The default is to not check edge direction. For example, you may want to include results that include relationships like `(protein)-[involved_in]->(pathway)` even though the underlying KG only contains directional edges of the form `(protein)<-[involved_in]-(pathway)`.
Note that this command will successfully execute given an arbitrary query graph and knowledge graph provided by the automated reasoning system, not just ones generated by Team ARA Expander."""
        description_list = []
        params_dict = dict()
        params_dict['brief_description'] = brief_description
        params_dict['force_isset_false'] = {'''set of `id` strings of nodes in the QG. Optional; default = empty set.'''}
        params_dict['ignore_edge_direction'] = {'''`true` or `false`. Optional; default is `true`.'''}
        # TODO: will need to update manually if more self.parameters are added
        # eg. params_dict[node_id] = {"a query graph node ID or list of such id's (required)"} as per issue #640
        description_list.append(params_dict)
        return description_list

    def apply(self, input_message: Message, input_parameters: dict) -> Response:

        # Define a default response
        response = Response()
        self.response = response
        self.message = input_message

        # Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        # Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        # call __resultify
        self.__resultify(describe=False)

        response.debug(f"Applying Resultifier to Message with parameters {parameters}")

        # Return the response and done
        return response

    def __resultify(self, describe: bool = False):
        """
        From a knowledge graph and a query graph (both in a Message object), extract a list of Results objects, each containing
        lists of NodeBinding and EdgeBinding objects. Add a list of Results objects to self.message.rseults.

        It is required that `self.parameters` contain the following:
            force_isset_false: a parameter of type `List[set]` containing string `id` fields of query nodes for which the `is_set` property should be set to `false`, overriding whatever the state of `is_set` for each of those nodes in the query graph. Optional.
            ignore_edge_direction: a parameter of type `bool` indicating whether the direction of an edge in the knowledge graph should be taken into account when matching that edge to an edge in the query graph. By default, this parameter is `true`. Set this parameter to false in order to require that an edge in a subgraph of the KG will only match an edge in the QG if both have the same direction (taking into account the source/target node mapping). Optional. 
        """
        assert self.response is not None
        results = self.message.results
        if results is not None and len(results) > 0:
            self.response.error(f"Supplied response has nonzero number of entries. ARAX_resultify expects it to be empty")
            return

        message = self.message
        parameters = self.parameters

        debug_mode = parameters.get('debug', None)
        if debug_mode is not None:
            debug_mode = (debug_mode.lower() == 'true')

        for parameter_name in parameters.keys():
            if parameter_name not in ARAXResultify.ALLOWED_PARAMETERS:
                print(debug_mode)
                error_string = "parameter type is not allowed in ARAXResultify: " + str(parameter_name)
                if not debug_mode:
                    self.response.error(error_string)
                    return
                else:
                    raise ValueError(error_string)

        kg = message.knowledge_graph
        qg = message.query_graph
        qg_nodes_override_treat_is_set_as_false_list = parameters.get('force_isset_false', None)
        if qg_nodes_override_treat_is_set_as_false_list is not None:
            qg_nodes_override_treat_is_set_as_false = set(qg_nodes_override_treat_is_set_as_false_list)
        else:
            qg_nodes_override_treat_is_set_as_false = set()
        ignore_edge_direction = parameters.get('ignore_edge_direction', None)
        if ignore_edge_direction is not None:
            ignore_edge_direction = (ignore_edge_direction.lower() == 'true')
        try:
            results = _get_results_for_kg_by_qg(kg,
                                                qg,
                                                qg_nodes_override_treat_is_set_as_false,
                                                ignore_edge_direction)
            message_code = 'OK'
            code_description = 'Result list computed from KG and QG'
        except Exception as e:
            if not debug_mode:
                code_description = str(e)
                message_code = e.__class__.__name__
                self.response.error(code_description)
                results = []
            else:
                raise e
        message.results = results
        message.n_results = len(results)
        message.code_description = code_description
        message.message_code = message_code


def _make_edge_key(node1_id: str,
                   node2_id: str) -> str:
    return node1_id + '->' + node2_id


def _make_result_from_node_set(kg: KnowledgeGraph,
                               node_ids: Set[str]) -> Result:
    node_bindings = []
    nodes = []
    for node in kg.nodes:
        if node.id in node_ids:
            node_bindings.append(NodeBinding(qg_id=node.qnode_id, kg_id=node.id))
            nodes.append(node)
    edge_bindings = []
    edges = []
    for edge in kg.edges:
        if edge.source_id in node_ids and edge.target_id in node_ids and edge.qedge_id is not None:
            edge_bindings.append(EdgeBinding(qg_id=edge.qedge_id, kg_id=edge.id))
            edges.append(edge)
#    node_bindings = [NodeBinding(qg_id=node.qnode_id, kg_id=node.id) for node in kg.nodes if node.id in node_ids]
#    edge_bindings = [EdgeBinding(qg_id=edge.qedge_id, kg_id=edge.id)
#                     for edge in kg.edges if edge.source_id in node_ids and
#                     edge.target_id in node_ids and
#                     edge.qedge_id is not None]
    result_graph = KnowledgeGraph(nodes=nodes, edges=edges)
    result = Result(node_bindings=node_bindings,
                    edge_bindings=edge_bindings,
                    result_graph=result_graph)
    return result


def _is_specific_query_node(qnode: QNode):
    return (qnode.id is not None and ':' in qnode.id) or \
        (qnode.curie is not None and ':' in qnode.curie)


def _make_adj_maps(graph: Union[QueryGraph, KnowledgeGraph],
                   directed=True,
                   droploops=True) -> Dict[str, Dict[str, Set[str]]]:
    if directed:
        adj_map_in: Dict[str, Set[str]] = {node.id: set() for node in graph.nodes}
        adj_map_out: Dict[str, Set[str]] = {node.id: set() for node in graph.nodes}
    else:
        adj_map: Dict[str, Set[str]] = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        if droploops and edge.target_id == edge.source_id:
            continue
        if directed:
            adj_map_out[edge.source_id].add(edge.target_id)
            adj_map_in[edge.target_id].add(edge.source_id)
        else:
            adj_map[edge.source_id].add(edge.target_id)
            adj_map[edge.target_id].add(edge.source_id)
    if directed:
        ret_dict = {'in': adj_map_in, 'out': adj_map_out}
    else:
        ret_dict = {'both': adj_map}
    return ret_dict


def _bfs_dists(adj_map: Dict[str, Set[str]],
               start_node_id: str) -> Dict[str, int]:
    queue = collections.deque([start_node_id])
    distances = {node_id: math.inf for node_id in adj_map.keys()}
    distances[start_node_id] = 0
    while len(queue) > 0:
        node_id = queue.popleft()
        node_dist = distances[node_id]
        assert not math.isinf(node_dist)
        for neighb_node_id in (adj_map[node_id]):
            if math.isinf(distances[neighb_node_id]):
                distances[neighb_node_id] = node_dist + 1
                queue.append(neighb_node_id)
    return distances


def _get_essence_node_for_qg(qg: QueryGraph) -> str:
    adj_map = _make_adj_maps(qg, directed=False)['both']
    node_ids_list = list(adj_map.keys())
    all_nodes = set(node_ids_list)
    node_degrees = list(map(len, adj_map.values()))
    leaf_nodes = set(node_ids_list[i] for i, k in enumerate(node_degrees) if k == 1)
    is_set_nodes = set(node.id for node in qg.nodes if node.is_set)
    specific_nodes = set(node.id for node in qg.nodes if _is_specific_query_node(node))
    non_specific_nodes = all_nodes - specific_nodes
    non_specific_leaf_nodes = leaf_nodes & non_specific_nodes

    if len(is_set_nodes & specific_nodes) > 0:
        raise ValueError("the following query nodes have specific CURIE IDs but have is_set=true: " + str(is_set_nodes & specific_nodes))
    candidate_essence_nodes = non_specific_leaf_nodes - is_set_nodes
    if len(candidate_essence_nodes) == 0:
        candidate_essence_nodes = non_specific_nodes - is_set_nodes
    if len(candidate_essence_nodes) == 0:
        return None
    elif len(candidate_essence_nodes) == 1:
        return next(iter(candidate_essence_nodes))
    else:
        specific_leaf_nodes = specific_nodes & leaf_nodes
        if len(specific_leaf_nodes) == 0:
            map_node_id_to_pos = {node.id: i for i, node in enumerate(qg.nodes)}
            if len(specific_nodes) == 0:
                # return the node.id of the non-specific node with the rightmost position in the QG node list
                return sorted(candidate_essence_nodes,
                              key=lambda node_id: map_node_id_to_pos[node_id],
                              reverse=True)[0]
            else:
                if len(specific_nodes) == 1:
                    specific_node_id = next(iter(specific_nodes))
                    return sorted(candidate_essence_nodes,
                                  key=lambda node_id: abs(map_node_id_to_pos[node_id] -
                                                          map_node_id_to_pos[specific_node_id]),
                                  reverse=True)[0]
                else:
                    # there are at least two non-specific leaf nodes and at least two specific nodes
                    return sorted(candidate_essence_nodes,
                                  key=lambda node_id: min([abs(map_node_id_to_pos[node_id] -
                                                               map_node_id_to_pos[specific_node_id]) for
                                                           specific_node_id in specific_nodes]),
                                  reverse=True)[0]
        else:
            if len(specific_leaf_nodes) == 1:
                specific_leaf_node_id = next(iter(specific_leaf_nodes))
                map_node_id_to_pos = _bfs_dists(adj_map, specific_leaf_node_id)
            else:
                all_dist_maps_for_spec_leaf_nodes = {node_id: _bfs_dists(adj_map,
                                                                         node_id) for
                                                     node_id in specific_leaf_nodes}
                map_node_id_to_pos = {node.id: min([dist_map[node.id] for dist_map in all_dist_maps_for_spec_leaf_nodes.values()]) for
                                      node in qg.nodes}
            return sorted(candidate_essence_nodes,
                          key=lambda node_id: map_node_id_to_pos[node_id],
                          reverse=True)[0]
    assert False


def _get_results_for_kg_by_qg(kg: KnowledgeGraph,              # all nodes *must* have qnode_id specified
                              qg: QueryGraph,
                              qg_nodes_override_treat_is_set_as_false: set = None,
                              ignore_edge_direction: bool = True) -> List[Result]:

    if len([node.id for node in qg.nodes if node.id is None]) > 0:
        raise ValueError("node has None for node.id in query graph")

    if len([node.id for node in kg.nodes if node.id is None]) > 0:
        raise ValueError("node has None for node.id in knowledge graph")

    kg_node_ids_without_qnode_id = [node.id for node in kg.nodes if node.qnode_id is None]
    if len(kg_node_ids_without_qnode_id) > 0:
        raise ValueError("these node IDs do not have qnode_id set: " + str(kg_node_ids_without_qnode_id))

    if qg_nodes_override_treat_is_set_as_false is None:
        qg_nodes_override_treat_is_set_as_false = set()

    # make a map of KG node IDs to QG node IDs, based on the node binding argument (nb) passed to this function
    node_bindings_map = {node.id: node.qnode_id for node in kg.nodes}

    # make a map of KG edge IDs to QG edge IDs, based on the node binding argument (nb) passed to this function
    edge_bindings_map = {edge.id: edge.qedge_id for edge in kg.edges if edge.qedge_id is not None}

    # make a map of KG node ID to KG edges, by source:
    kg_adj_map_direc = _make_adj_maps(kg, directed=True, droploops=False)
    kg_node_id_incoming_adjacency_map = kg_adj_map_direc['in']
    kg_node_id_outgoing_adjacency_map = kg_adj_map_direc['out']

    kg_adj_map = _make_adj_maps(kg, directed=False, droploops=True)['both']
    qg_adj_map = _make_adj_maps(qg, directed=False, droploops=True)['both']  # can the QG have a self-loop?  not sure

    # build up maps of node IDs to nodes, for both the KG and QG
    kg_nodes_map = {node.id: node for node in kg.nodes}
    qg_nodes_map = {node.id: node for node in qg.nodes}

    missing_node_ids = [node_id for node_id in qg_nodes_override_treat_is_set_as_false if node_id not in qg_nodes_map]
    if len(missing_node_ids) > 0:
        raise ValueError("the following nodes in qg_nodes_override_treat_is_set_as_false are not in the query graph: " +
                         str(missing_node_ids))

    # make an inverse "node bindings" map of QG node IDs to KG node ids
    reverse_node_bindings_map: Dict[str, set] = {node.id: set() for node in qg.nodes}
    for node in kg.nodes:
        reverse_node_bindings_map[node.qnode_id].add(node.id)

    # build up maps of edge IDs to edges, for both the KG and QG
    kg_edges_map = {edge.id: edge for edge in kg.edges}
    qg_edges_map = {edge.id: edge for edge in qg.edges}

    # make a map between QG edge keys and QG edge IDs
    qg_edge_key_to_edge_id_map = {_make_edge_key(edge.source_id, edge.target_id): edge.id for edge in qg.edges}

    kg_undir_edge_keys_set = set(_make_edge_key(edge.source_id, edge.target_id) for edge in kg.edges) |\
        set(_make_edge_key(edge.target_id, edge.source_id) for edge in kg.edges)

    # --------------------- checking for validity of the NodeBindings list --------------
    # we require that every query graph node ID in the "values" slot of the node_bindings_map corresponds to an actual node in the QG
    node_ids_mapped_that_are_not_in_qg = [node_id for node_id in node_bindings_map.values() if node_id not in qg_nodes_map]
    if len(node_ids_mapped_that_are_not_in_qg) > 0:
        raise ValueError("query node ID specified in the NodeBinding list that is not in the QueryGraph: " + str(node_ids_mapped_that_are_not_in_qg))

    # we require that every know. graph node ID in the "keys" slot of the node_bindings_map corresponds to an actual node in the KG
    node_ids_mapped_that_are_not_in_kg = [node_id for node_id in node_bindings_map.keys() if node_id not in kg_nodes_map]
    if len(node_ids_mapped_that_are_not_in_kg) > 0:
        raise ValueError("knowledge graph node ID specified in the NodeBinding list that is not in the KG: " + str(node_ids_mapped_that_are_not_in_kg))

    # --------------------- checking for validity of the EdgeBindings list --------------
    # we require that every query graph edge ID in the "values" slot of the edge_bindings_map corresponds to an actual edge in the QG
    edge_ids_mapped_that_are_not_in_qg = [edge_id for edge_id in edge_bindings_map.values() if edge_id is not None and edge_id not in qg_edges_map]
    if len(edge_ids_mapped_that_are_not_in_qg) > 0:
        raise ValueError("query edge ID specified in the EdgeBinding list that is not in the QueryGraph: " + str(edge_ids_mapped_that_are_not_in_qg))

    # we require that every know. graph edge ID in the "keys" slot of the edge_bindings_map corresponds to an actual edge in the KG
    edge_ids_mapped_that_are_not_in_kg = [edge_id for edge_id in edge_bindings_map.keys() if edge_id not in kg_edges_map]
    if len(edge_ids_mapped_that_are_not_in_kg) > 0:
        raise ValueError("knowledge graph edge ID specified in the EdgeBinding list that is not in the KG: " + str(edge_ids_mapped_that_are_not_in_kg))

    # --------------------- checking that the node bindings cover the query graph --------------
    # check if each node in the query graph are hit by at least one node binding; if not, raise an exception
    qg_ids_hit_by_bindings = {node.qnode_id for node in kg.nodes}
    if len([node for node in qg.nodes if node.id not in qg_ids_hit_by_bindings]) > 0:
        raise ValueError("the node binding list does not cover all nodes in the query graph")

    # --------------------- checking that every KG node is bound to a QG node --------------
    node_ids_of_kg_that_are_not_mapped_to_qg = [node.id for node in kg.nodes if node.id not in node_bindings_map]
    if len(node_ids_of_kg_that_are_not_mapped_to_qg) > 0:
        raise ValueError("KG nodes that are not mapped to QG: " + str(node_ids_of_kg_that_are_not_mapped_to_qg))

    # --------------------- the source ID and target ID of every edge in KG should be a valid KG node ---------------------
    node_ids_for_edges_that_are_not_valid_nodes = [edge.source_id for edge in kg.edges if kg_nodes_map.get(edge.source_id, None) is None] +\
        [edge.target_id for edge in kg.edges if kg_nodes_map.get(edge.target_id, None) is None]
    if len(node_ids_for_edges_that_are_not_valid_nodes) > 0:
        raise ValueError("KG has edges that refer to the following non-existent nodes: " + str(node_ids_for_edges_that_are_not_valid_nodes))

    # --------------------- the source ID and target ID of every edge in QG should be a valid QG node ---------------------
    node_ids_for_edges_that_are_not_valid_nodes = [edge.source_id for edge in qg.edges if qg_nodes_map.get(edge.source_id, None) is None] +\
        [edge.target_id for edge in qg.edges if qg_nodes_map.get(edge.target_id, None) is None]
    if len(node_ids_for_edges_that_are_not_valid_nodes) > 0:
        raise ValueError("QG has edges that refer to the following non-existent nodes: " + str(node_ids_for_edges_that_are_not_valid_nodes))

    # --------------------- check for consistency of edge-to-node relationships, for all edge bindings -----------
    # check that for each bound KG edge, the QG mappings of the KG edges source and target nodes are also the
    # source and target nodes of the QG edge that corresponds to the bound KG edge
    for kg_edge_id in edge_bindings_map:
        kg_edge = kg_edges_map[kg_edge_id]
        kg_source_node_id = kg_edge.source_id
        kg_target_node_id = kg_edge.target_id
        qg_source_node_id = node_bindings_map[kg_source_node_id]
        qg_target_node_id = node_bindings_map[kg_target_node_id]
        if qg_edge_key_to_edge_id_map.get(_make_edge_key(qg_source_node_id, qg_target_node_id), None) is None:
            if not ignore_edge_direction or qg_edge_key_to_edge_id_map.get(_make_edge_key(qg_target_node_id, qg_source_node_id), None) is None:
                raise ValueError("The two nodes for KG edge " + kg_edge.id + ", " + kg_source_node_id + " and " +
                                 kg_target_node_id + ", have no corresponding edge in the QG")

    # ------- check that for every edge in the QG, any KG nodes that are bound to the QG endpoint nodes of the edge are connected in the KG -------
    for qg_edge in qg_edges_map.values():
        source_id_qg = qg_edge.source_id
        target_id_qg = qg_edge.target_id
        source_node_ids_kg = reverse_node_bindings_map[source_id_qg]
        target_node_ids_kg = reverse_node_bindings_map[target_id_qg]
        # for each source node ID, there should be an edge in KG from this source node to one of the nodes in target_node_ids_kg:
        for source_node_id_kg in source_node_ids_kg:
            if len(kg_node_id_outgoing_adjacency_map[source_node_id_kg] | target_node_ids_kg) == 0:
                raise ValueError("Inconsistent with its binding to the QG, the KG node: " + source_node_id_kg +
                                 " is not connected to *any* of the following nodes: " + str(target_node_ids_kg))
        for target_node_id_kg in target_node_ids_kg:
            if len(kg_node_id_incoming_adjacency_map[target_node_id_kg] | source_node_ids_kg) == 0:
                raise ValueError("Inconsistent with its binding to the QG, the KG node: " + target_node_id_kg +
                                 " is not connected to *any* of the following nodes: " + str(source_node_ids_kg))

    node_types_map = {node.id: node.type for node in qg.nodes}
    essence_qnode_id = _get_essence_node_for_qg(qg)
    if essence_qnode_id is not None:
        essence_node_type = node_types_map[essence_qnode_id]
    else:
        essence_node_type = None

    # ============= save until SAR can discuss with {EWD,DMK} whether there can be unmapped nodes in the KG =============
    # # if any node in the KG is not bound to a node in the QG, drop the KG node; redefine "kg" as the filtered KG
    # kg_node_ids_keep = {node.id for node in kg.nodes if node.id in node_bindings_map}
    # kg_nodes_keep_list = [node for node in kg.nodes if node.id in kg_node_ids_keep]
    # kg_edges_keep_list = [edge for edge in kg.edges if not (edge.source_id in kg_node_ids_keep and
    #                                                         edge.target_id in kg_node_ids_keep)]
    # kg = KnowledgeGraph(nodes=kg_nodes_keep_list,
    #                     edges=kg_edges_keep_list)
    # ============= save until SAR can discuss with {EWD,DMK} whether there can be unmapped nodes in the KG =============

    # Our goal is to enumerate all distinct "edge-maximal" subgraphs of the KG that each "covers"
    # the QG. A subgraph of KG that "covers" the QG is one for which all of the following conditions hold:
    # (1) under the KG-to-QG node bindings map, the range of the KG subgraph's nodes is the entire set of nodes in the QG
    # (2) for any QG node that has "is_set=True", *all* KG nodes that are bound to the same QG node are in the subgraph
    # (3) every edge in the QG is "covered" by at least one edge in the KG

    kg_node_ids_with_isset_true: Set[str] = set()
    kg_node_id_lists_for_qg_nodes = []
    # for each node in the query graph:
    for node in qg.nodes:
        if node.is_set is not None and \
           node.is_set and \
           node.id not in qg_nodes_override_treat_is_set_as_false:
            kg_node_ids_with_isset_true |= reverse_node_bindings_map[node.id]
        else:
            kg_node_id_lists_for_qg_nodes.append(list(reverse_node_bindings_map[node.id]))

    results: List[Result] = []
    essence_nodes_in_kg = reverse_node_bindings_map.get(essence_qnode_id, set())
    for node_ids_for_subgraph_from_non_set_nodes in itertools.product(*kg_node_id_lists_for_qg_nodes):
        node_ids_for_subgraph = set(node_ids_for_subgraph_from_non_set_nodes) | kg_node_ids_with_isset_true
        # for all KG nodes with isset_true:
        for kg_node_id in kg_node_ids_with_isset_true:
            qg_node_id = node_bindings_map[kg_node_id]
            # find all edges of this kg_node_id in the KG
            qg_neighbor_nodes_set = qg_adj_map[qg_node_id]
            # for qg_edge_id in nbhd_qg_edge_ids:
            for qg_neighbor_node_id in qg_neighbor_nodes_set:
                kg_nodes_for_qg_neighbor_node = reverse_node_bindings_map[qg_neighbor_node_id]
                found_neighbor_connected_to_kg_node_id = False
                for kg_neighbor_node_id in kg_nodes_for_qg_neighbor_node:
                    if _make_edge_key(kg_node_id, kg_neighbor_node_id) in kg_undir_edge_keys_set and \
                       kg_neighbor_node_id in node_ids_for_subgraph:
                        found_neighbor_connected_to_kg_node_id = True
                        break
                if not found_neighbor_connected_to_kg_node_id and kg_node_id in node_ids_for_subgraph:
                    node_ids_for_subgraph.remove(kg_node_id)
        result = _make_result_from_node_set(kg, node_ids_for_subgraph)
        essence_kg_node_id_set = essence_nodes_in_kg & node_ids_for_subgraph
        if len(essence_kg_node_id_set) == 1:
            essence_kg_node_id = next(iter(essence_kg_node_id_set))
            essence_kg_node = kg_nodes_map[essence_kg_node_id]
            result.essence = essence_kg_node.name
            if result.essence is None:
                result.essence = essence_kg_node_id
            assert result.essence is not None
            if essence_kg_node.symbol is not None:
                result.essence += " (" + str(essence_kg_node.symbol) + ")"
            result.essence_type = essence_node_type
        elif len(essence_kg_node_id_set) == 0:
            result.essence = None
            result.essence_type = None
        else:
            raise ValueError("there are more than two nodes in the KG that are candidates for the essence: " + str(essence_kg_node_id_set))
        results.append(result)

    # Programmatically generating an informative description for each result
    # seems difficult, but having something non-None is required by the
    # database.  Just put in a placeholder for now, as is done by the
    # QueryGraphReasoner
    for result in results:
        result.description = "No description available"  # see issue 642

    return results


def _do_arax_query(query: str) -> List[Union[Response, Message]]:
    from ARAX_query import ARAXQuery
    araxq = ARAXQuery()
    response = araxq.query(query)
    return [response, araxq.message]


def _test01():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'HP:56789',
                     'target_id': 'HP:67890',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': False},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = _get_results_for_kg_by_qg(knowledge_graph,
                                             query_graph)

    assert len(results_list) == 2


def _test02():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'HP:56789',
                     'target_id': 'HP:67890',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = _get_results_for_kg_by_qg(knowledge_graph,
                                             query_graph)
    assert len(results_list) == 2


def _test03():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'HP:56789',
                     'target_id': 'HP:67890',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = _get_results_for_kg_by_qg(knowledge_graph,
                                             query_graph,
                                             ignore_edge_direction=True)
    assert len(results_list) == 2


def _test04():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke08',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = _get_results_for_kg_by_qg(knowledge_graph,
                                             query_graph,
                                             qg_nodes_override_treat_is_set_as_false={'n02'},
                                             ignore_edge_direction=True)
    assert len(results_list) == 2


def _test05():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},    
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke08',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    resultifier = ARAXResultify()
    input_parameters = {'ignore_edge_direction': 'true',
                        'force_isset_false': ['n02']}
    resultifier.apply(message, input_parameters)
    assert resultifier.response.status == 'OK'
    assert len(resultifier.message.results) == 2


def _test06():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},    
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke08',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    resultifier = ARAXResultify()
    input_parameters = {'ignore_edge_direction': 'true',
                        'force_isset_false': ['n07']}
    resultifier.apply(message, input_parameters)
    assert resultifier.response.status != 'OK'
    assert len(resultifier.message.results) == 0


def _test07():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke08',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_id': None})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    response = Response()
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
    actions_list = ['resultify(ignore_edge_direction=true,force_isset_false=[n02])']
    result = actions_parser.parse(actions_list)
    response.merge(result)
    actions = result.data['actions']
    assert result.status == 'OK'
    resultifier = ARAXResultify()
    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    parameters = actions[0]['parameters']
    parameters['debug'] = 'true'
    result = resultifier.apply(message, parameters)
    response.merge(result)
    assert len(message.results) == 2
    assert result.status == 'OK'


def _test08():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(type=disease, curie=DOID:731, id=n00)",
        "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        'resultify(ignore_edge_direction=true, debug=true)',
        "return(message=true, store=false)"]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 3223


def _test09():
    query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:731, id=n00, type=disease, is_set=false)",
            "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            'resultify(ignore_edge_direction=true, debug=true)',
            'filter_results(action=limit_number_of_results, max_results=100)',
            "return(message=true, store=false)"]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 100


def _test10():
    resultifier = ARAXResultify()
    desc = resultifier.describe_me()
    assert 'brief_description' in desc[0]
    assert 'force_isset_false' in desc[0]
    assert 'ignore_edge_direction' in desc[0]


def _test_example1():
    query = {"previous_message_processing_plan": {"processing_actions": [
                                                      'create_message',
                                                      'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
                                                      'add_qnode(id=qg1, type=protein)',
                                                      'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
                                                      'expand(edge_id=qe0)',
                                                      'resultify(ignore_edge_direction=true, debug=true)',
                                                      "filter_results(action=limit_number_of_results, max_results=10)",
                                                      "return(message=true, store=true)",
                                                  ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 10
    assert message.results[0].essence is not None


def _test_example2():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_edge_type=P1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 38
    assert message.results[0].essence is not None


def _test_example3():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(name=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01])",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_edge_type=C1, source_qnode_id=n00, target_qnode_id=n01)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)",
        "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
        "overlay(action=compute_ngd, virtual_edge_type=N1, source_qnode_id=n01, target_qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=ngd, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=true)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None


def _test_bfs():
    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    qg = QueryGraph(qg_nodes, qg_edges)
    adj_map = _make_adj_maps(qg, directed=False, droploops=True)['both']
    bfs_dists = _bfs_dists(adj_map, 'n01')
    assert bfs_dists == {'n01': 0, 'DOID:12345': 1, 'n02': 2}
    bfs_dists = _bfs_dists(adj_map, 'DOID:12345')
    assert bfs_dists == {'n01': 1, 'DOID:12345': 0, 'n02': 1}


def _test_bfs_in_essence_code():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_id': 'n01'},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_id': 'DOID:12345'},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_id': 'HP:56789'},
                    {'id': 'FOO:12345',
                     'type': 'gene',
                     'qnode_id': 'n02'})

    kg_edge_info = ({'edge_id': 'ke01',
                     'target_id': 'UniProtKB:12345',
                     'source_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke02',
                     'target_id': 'UniProtKB:23456',
                     'source_id': 'DOID:12345',
                     'qedge_id': 'qe01'},
                    {'edge_id': 'ke03',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'FOO:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke04',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'FOO:12345',
                     'qedge_id': 'qe02'},
                    {'edge_id': 'ke05',
                     'source_id': 'FOO:12345',
                     'target_id': 'HP:56789',
                     'qedge_id':  'qe03'})

    kg_nodes = [Node(id=node_info['id'],
                     type=[node_info['type']],
                     qnode_id=node_info['qnode_id']) for node_info in kg_node_info]

    kg_edges = [Edge(id=edge_info['edge_id'],
                     source_id=edge_info['source_id'],
                     target_id=edge_info['target_id'],
                     qedge_id=edge_info['qedge_id']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': False},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'gene',
                     'is_set': False})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'n02',
                     'target_id': 'HP:56789'},
                    {'edge_id': 'qe03',
                     'source_id': 'n01',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = _get_results_for_kg_by_qg(knowledge_graph,
                                             query_graph)
    assert len(results_list) == 2
    assert results_list[0].essence is not None


def _test_issue680():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_edge_type=P1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "filter_results(action=limit_number_of_results, max_results=1)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 1
    result = message.results[0]
    resgraph = result.result_graph
    count_drug_prot = 0
    count_disease_prot = 0
    for edge in resgraph.edges:
        if edge.target_id.startswith("CHEMBL.") and edge.source_id.startswith("UniProtKB:"):
            count_drug_prot += 1
        if edge.target_id.startswith("DOID:") and edge.source_id.startswith("UniProtKB:"):
            count_disease_prot += 1
    assert count_drug_prot == count_disease_prot
    assert result.essence is not None


def _test_issue686():
    try:
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'expand(edge_id=qe0)',
            'resultify(ignore_edge_direction=true, debug=true, INVALID_PARAMETER_NAME=true)'
        ]}}
        _do_arax_query(query)
    except Exception:
        return
    assert False


def _test_issue687():
    try:
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'add_qedge(source_id=qg0, target_id=qg1, id=qe1)',
            'expand(edge_id=qe0)',
            'resultify(debug=true)',
            "return(message=true, store=true)"
        ]}}
        _do_arax_query(query)
    except Exception as e:
        print(str(e))
        assert False
    return


def _run_module_level_tests():
    _test01()
    _test02()
    _test03()
    _test04()
    _test_bfs()
    _test_bfs_in_essence_code()


def _run_arax_class_tests():
    _test05()
    _test06()
    _test07()
    _test08()
    _test09()
    _test10()
    _test_example1()
    _test_example2()
    _test_issue680()
    _test_example3()
    _test_issue686()
    _test_issue687()


def main():
    if len(sys.argv) > 1:
        for func_name in sys.argv[1:len(sys.argv)]:
            globals()[func_name]()
    else:
        _run_module_level_tests()
        _run_arax_class_tests()


if __name__ == '__main__':
    main()
