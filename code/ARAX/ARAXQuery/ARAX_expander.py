#!/bin/env python3
import sys
import os
from typing import List, Dict, Tuple, Union

from response import Response
from Expand.expand_utilities import DictKnowledgeGraph
import Expand.expand_utilities as eu

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXExpander:

    def __init__(self):
        self.response = None
        self.message = None
        self.edge_id_parameter_info = {
            "is_required": False,
            "examples": ["e00", "[e00, e01]"],
            "type": "string",
            "description": "A query graph edge ID or list of such IDs to expand (default is to expand entire query graph)."
        }
        self.node_id_parameter_info = {
            "is_required": False,
            "examples": ["n00", "[n00, n01]"],
            "type": "string",
            "description": "A query graph node ID or list of such IDs to expand (default is to expand entire query graph)."
        }
        self.continue_if_no_results_parameter_info = {
            "is_required": False,
            "examples": ["true", "false"],
            "enum": ["true", "false"],
            "default": "false",
            "type": "boolean",
            "description": "Whether to continue execution if no paths are found matching the query graph."
        }
        self.enforce_directionality_parameter_info = {
            "is_required": False,
            "examples": ["true", "false"],
            "enum": ["true", "false"],
            "default": "false",
            "type": "boolean",
            "description": "Whether to obey (vs. ignore) edge directions in the query graph."
        }
        self.use_synonyms_parameter_info = {
            "is_required": False,
            "examples": ["true", "false"],
            "enum": ["true", "false"],
            "default": "true",
            "type": "boolean",
            "description": "Whether to consider curie synonyms and merge synonymous nodes."
        }
        self.command_definitions = {
            "ARAX/KG1": {
                "dsl_command": "expand(kp=ARAX/KG1)",
                "description": "This command reaches out to the RTX KG1 Neo4j instance to find all bioentity subpaths "
                               "that satisfy the query graph.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "enforce_directionality": self.enforce_directionality_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info
                }
            },
            "ARAX/KG2": {
                "dsl_command": "expand(kp=ARAX/KG2)",
                "description": "This command reaches out to the RTX KG2 knowledge graph to find all bioentity subpaths "
                               "that satisfy the query graph. If use_synonyms=true, it uses the KG2canonicalized "
                               "('KG2c') Neo4j instance; otherwise, the regular KG2 Neo4j instance is used.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "enforce_directionality": self.enforce_directionality_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info
                }
            },
            "BTE": {
                "dsl_command": "expand(kp=BTE)",
                "description": "This command uses BioThings Explorer (from the Service Provider) to find all bioentity "
                               "subpaths that satisfy the query graph. Of note, all query nodes must have a type "
                               "specified for BTE queries. In addition, bi-directional queries are only partially "
                               "supported (the ARAX system knows how to ignore edge direction when deciding which "
                               "query node for a query edge will be the 'input' qnode, but BTE itself returns only "
                               "answers matching the input edge direction).",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "enforce_directionality": self.enforce_directionality_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info
                }
            },
            "COHD": {
                "dsl_command": "expand(kp=COHD)",
                "description": "This command uses the Clinical Data Provider (COHD) to find all bioentity subpaths that"
                               " satisfy the query graph.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info,
                    "COHD_method": {
                        "is_required": False,
                        "examples": ["paired_concept_freq", "chi_square"],
                        "enum": ["paired_concept_freq", "observed_expected_ratio", "chi_square"],
                        "default": "paired_concept_freq",
                        "type": "string",
                        "description": "Which measure from COHD should be considered."
                    },
                    "COHD_method_percentile": {
                        "is_required": False,
                        "examples": [95, 80],
                        "min": 0,
                        "max": 100,
                        "default": 99,
                        "type": "integer",
                        "description": "What percentile to use as a cut-off/threshold for the specified COHD method."
                    }
                }
            },
            "GeneticsKP": {
                "dsl_command": "expand(kp=GeneticsKP)",
                "description": "This command reaches out to the Genetics Provider to find all bioentity subpaths that "
                               "satisfy the query graph. It currently can answers questions involving the following "
                               "node types: gene, protein, disease, phenotypic_feature, pathway. Temporarily "
                               "(while the integration is under development), it can only be used as the first hop in"
                               " a query.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info,
                    "include_integrated_score": {
                        "is_required": False,
                        "examples": ["true", "false"],
                        "enum": ["true", "false"],
                        "default": "false",
                        "type": "boolean",
                        "description": "Whether to add genetics-quantile edges (in addition to MAGMA edges) from the Genetics KP."
                    }
                }
            },
            "NGD": {
                "dsl_command": "expand(kp=NGD)",
                "description": "This command uses ARAX's in-house normalized google distance (NGD) database to expand "
                               "a query graph; it returns edges between nodes with an NGD value below a certain "
                               "threshold. This threshold is currently hardcoded as 0.5, though this will be made "
                               "configurable/smarter in the future.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info
                }
            }
        }

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        return list(self.command_definitions.values())

    def apply(self, input_message, input_parameters, response=None):

        if response is None:
            response = Response()
        self.response = response
        self.message = input_message

        # Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # Define a complete set of allowed parameters and their defaults
        kp = input_parameters.get("kp", "ARAX/KG1")
        parameters = {"kp": kp}
        for kp_parameter_name, info_dict in self.command_definitions[kp]["parameters"].items():
            if info_dict["type"] == "boolean":
                parameters[kp_parameter_name] = self._convert_string_to_bool_if_bool(info_dict.get("default", ""))
            else:
                parameters[kp_parameter_name] = info_dict.get("default", None)
        # Override default values for any parameters passed in
        for key, value in input_parameters.items():
            if key and key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                parameters[key] = self._convert_string_to_bool_if_bool(value) if isinstance(value, str) else value

        # Handle situation where 'ARAX/KG2C' is entered as the kp (technically invalid, but we won't error out)
        if parameters['kp'] == "ARAX/KG2C":
            parameters['kp'] = "ARAX/KG2"
            if not parameters['use_synonyms']:
                response.warning(f"KG2C is only used when use_synonyms=true; overriding use_synonyms to True")
                parameters['use_synonyms'] = True

        # Default to expanding the entire query graph if the user didn't specify what to expand
        if not parameters['edge_id'] and not parameters['node_id']:
            parameters['edge_id'] = [edge.id for edge in self.message.query_graph.edges]
            parameters['node_id'] = self._get_orphan_query_node_ids(self.message.query_graph)

        if response.status != 'OK':
            return response

        response.data['parameters'] = parameters
        self.parameters = parameters

        # Do the actual expansion
        response.debug(f"Applying Expand to Message with parameters {parameters}")
        input_edge_ids = eu.convert_string_or_list_to_list(parameters['edge_id'])
        input_node_ids = eu.convert_string_or_list_to_list(parameters['node_id'])
        kp_to_use = self.parameters['kp']
        continue_if_no_results = self.parameters['continue_if_no_results']
        use_synonyms = self.parameters['use_synonyms']
        query_graph = self.message.query_graph
        log = self.response

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_kg = eu.convert_standard_kg_to_dict_kg(self.message.knowledge_graph)

        # Expand any specified edges
        if input_edge_ids:
            query_sub_graph = self._extract_query_subgraph(input_edge_ids, query_graph, log)
            if log.status != 'OK':
                return response
            log.debug(f"Query graph for this Expand() call is: {query_sub_graph.to_dict()}")

            # Expand the query graph edge by edge (much faster for neo4j queries, and allows easy integration with BTE)
            ordered_qedges_to_expand = self._get_order_to_expand_edges_in(query_sub_graph)
            node_usages_by_edges_map = dict()

            for qedge in ordered_qedges_to_expand:
                answer_kg, edge_node_usage_map = self._expand_edge(qedge, kp_to_use, dict_kg, continue_if_no_results,
                                                                   query_graph, use_synonyms, log)
                if log.status != 'OK':
                    return response
                node_usages_by_edges_map[qedge.id] = edge_node_usage_map

                self._merge_answer_into_message_kg(answer_kg, dict_kg, log)
                if log.status != 'OK':
                    return response

                self._prune_dead_end_paths(dict_kg, query_sub_graph, node_usages_by_edges_map, log)
                if log.status != 'OK':
                    return response

        # Expand any specified nodes
        if input_node_ids:
            for qnode_id in input_node_ids:
                answer_kg = self._expand_node(qnode_id, kp_to_use, continue_if_no_results, query_graph, use_synonyms, log)
                if log.status != 'OK':
                    return response

                self._merge_answer_into_message_kg(answer_kg, dict_kg, log)
                if log.status != 'OK':
                    return response

        # Convert message knowledge graph back to API standard format
        self.message.knowledge_graph = eu.convert_dict_kg_to_standard_kg(dict_kg)

        # Override node types so that they match what was asked for in the query graph (where applicable) #987
        self._override_node_types(self.message.knowledge_graph, self.message.query_graph)
        
        # Make sure we don't have any orphan edges
        node_ids = {node.id for node in self.message.knowledge_graph.nodes}
        for edge in self.message.knowledge_graph.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                self.message.knowledge_graph.edges.remove(edge)

        # Return the response and done
        kg = self.message.knowledge_graph
        if not kg.nodes and not continue_if_no_results:
            log.error(f"No paths were found in {kp_to_use} satisfying this query graph", error_code="NoResults")
        else:
            log.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges "
                     f"({eu.get_printable_counts_by_qg_id(dict_kg)})")
        return response

    def _expand_edge(self, qedge: QEdge, kp_to_use: str, dict_kg: DictKnowledgeGraph, continue_if_no_results: bool,
                     query_graph: QueryGraph, use_synonyms: bool, log: Response) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        # This function answers a single-edge (one-hop) query using the specified knowledge provider
        log.info(f"Expanding edge {qedge.id} using {kp_to_use}")
        answer_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Create a query graph for this edge (that uses synonyms as well as curies found in prior steps)
        edge_query_graph = self._get_query_graph_for_edge(qedge, query_graph, dict_kg, log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map
        if not any(qnode for qnode in edge_query_graph.nodes if qnode.curie):
            log.error(f"Cannot expand an edge for which neither end has any curies. (Could not find curies to use from "
                      f"a prior expand step, and neither qnode has a curie specified.)", error_code="InvalidQuery")
            return answer_kg, edge_to_nodes_map

        allowable_kps = set(self.command_definitions.keys())
        if kp_to_use not in allowable_kps:
            log.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are {', '.join(allowable_kps)}",
                      error_code="InvalidKP")
            return answer_kg, edge_to_nodes_map
        else:
            if kp_to_use == 'BTE':
                from Expand.bte_querier import BTEQuerier
                kp_querier = BTEQuerier(log)
            elif kp_to_use == 'COHD':
                from Expand.COHD_querier import COHDQuerier
                kp_querier = COHDQuerier(log)
            elif kp_to_use == 'NGD':
                from Expand.ngd_querier import NGDQuerier
                kp_querier = NGDQuerier(log)
            elif kp_to_use == 'GeneticsKP':
                from Expand.genetics_querier import GeneticsQuerier
                kp_querier = GeneticsQuerier(log)
            else:
                from Expand.kg_querier import KGQuerier
                kp_querier = KGQuerier(log, kp_to_use)
            answer_kg, edge_to_nodes_map = kp_querier.answer_one_hop_query(edge_query_graph)
            if log.status != 'OK':
                return answer_kg, edge_to_nodes_map
            log.debug(f"Query for edge {qedge.id} returned results ({eu.get_printable_counts_by_qg_id(answer_kg)})")

            # Do some post-processing (deduplicate nodes, remove self-edges..)
            if use_synonyms and kp_to_use != 'ARAX/KG2':  # KG2C is already deduplicated
                answer_kg, edge_to_nodes_map = self._deduplicate_nodes(answer_kg, edge_to_nodes_map, log)
            if eu.qg_is_fulfilled(edge_query_graph, answer_kg):
                answer_kg = self._remove_self_edges(answer_kg, edge_to_nodes_map, qedge.id, edge_query_graph.nodes, log)

            # Make sure our query has been fulfilled (unless we're continuing if no results)
            if not eu.qg_is_fulfilled(edge_query_graph, answer_kg):
                if continue_if_no_results:
                    log.warning(f"No paths were found in {kp_to_use} satisfying this query graph")
                else:
                    log.error(f"No paths were found in {kp_to_use} satisfying this query graph", error_code="NoResults")

            return answer_kg, edge_to_nodes_map

    def _expand_node(self, qnode_id: str, kp_to_use: str, continue_if_no_results: bool, query_graph: QueryGraph,
                     use_synonyms: bool, log: Response) -> DictKnowledgeGraph:
        # This function expands a single node using the specified knowledge provider
        log.debug(f"Expanding node {qnode_id} using {kp_to_use}")
        query_node = eu.get_query_node(query_graph, qnode_id)
        answer_kg = DictKnowledgeGraph()
        if log.status != 'OK':
            return answer_kg
        if not query_node.curie:
            log.error(f"Cannot expand a single query node if it doesn't have a curie", error_code="InvalidQuery")
            return answer_kg
        copy_of_qnode = eu.copy_qnode(query_node)

        # Consider both gene and protein when one is given
        if copy_of_qnode.type in ["protein", "gene"]:
            copy_of_qnode.type = ["protein", "gene"]
        log.debug(f"Modified query node is: {copy_of_qnode.to_dict()}")

        # Answer the query using the proper KP
        valid_kps_for_single_node_queries = ["ARAX/KG1", "ARAX/KG2"]
        if kp_to_use in valid_kps_for_single_node_queries:
            from Expand.kg_querier import KGQuerier
            kg_querier = KGQuerier(log, kp_to_use)
            answer_kg = kg_querier.answer_single_node_query(copy_of_qnode)
            log.info(f"Query for node {copy_of_qnode.id} returned results ({eu.get_printable_counts_by_qg_id(answer_kg)})")

            # Make sure all qnodes have been fulfilled (unless we're continuing if no results)
            if log.status == 'OK' and not continue_if_no_results:
                if copy_of_qnode.id not in answer_kg.nodes_by_qg_id or not answer_kg.nodes_by_qg_id[copy_of_qnode.id]:
                    log.error(f"Returned answer KG does not contain any results for QNode {copy_of_qnode.id}",
                              error_code="UnfulfilledQGID")
                    return answer_kg

            if use_synonyms and kp_to_use != 'ARAX/KG2':  # KG2C is already deduplicated
                answer_kg, edge_node_usage_map = self._deduplicate_nodes(dict_kg=answer_kg,
                                                                         edge_to_nodes_map={},
                                                                         log=log)
            return answer_kg
        else:
            log.error(f"Invalid knowledge provider: {kp_to_use}. Valid options for single-node queries are "
                      f"{', '.join(valid_kps_for_single_node_queries)}", error_code="InvalidKP")
            return answer_kg

    def _get_query_graph_for_edge(self, qedge: QEdge, query_graph: QueryGraph, dict_kg: DictKnowledgeGraph, log: Response) -> QueryGraph:
        # This function creates a query graph for the specified qedge, updating its qnodes' curies as needed
        edge_query_graph = QueryGraph(nodes=[], edges=[])
        qnodes = [eu.get_query_node(query_graph, qedge.source_id),
                  eu.get_query_node(query_graph, qedge.target_id)]

        # Add (a copy of) this qedge to our edge query graph
        edge_query_graph.edges.append(eu.copy_qedge(qedge))

        # Update this qedge's qnodes as appropriate and add (copies of) them to the edge query graph
        qedge_has_already_been_expanded = qedge.id in dict_kg.edges_by_qg_id
        for qnode in qnodes:
            qnode_copy = eu.copy_qnode(qnode)
            # Feed in curies from a prior Expand() step as the curie for this qnode as necessary
            qnode_already_fulfilled = qnode_copy.id in dict_kg.nodes_by_qg_id
            if qnode_already_fulfilled and not qnode_copy.curie:
                if qedge_has_already_been_expanded:
                    if self._is_input_qnode(qnode_copy, qedge):
                        qnode_copy.curie = list(dict_kg.nodes_by_qg_id[qnode_copy.id].keys())
                else:
                    qnode_copy.curie = list(dict_kg.nodes_by_qg_id[qnode_copy.id].keys())
            edge_query_graph.nodes.append(qnode_copy)

        # Consider both protein and gene if qnode's type is one of those (since KPs handle these differently)
        for qnode in edge_query_graph.nodes:
            if qnode.type in ['protein', 'gene']:
                qnode.type = ['protein', 'gene']

        # Display a summary of what the modified query graph for this edge looks like
        qnodes_with_curies = [qnode for qnode in edge_query_graph.nodes if qnode.curie]
        input_qnode = qnodes_with_curies[0] if qnodes_with_curies else edge_query_graph.nodes[0]
        output_qnode = next(qnode for qnode in edge_query_graph.nodes if qnode.id != input_qnode.id)
        input_curie_summary = self._get_qnode_curie_summary(input_qnode)
        output_curie_summary = self._get_qnode_curie_summary(output_qnode)
        log.debug(f"Modified QG for this edge is ({input_qnode.id}:{input_qnode.type}{input_curie_summary})-"
                  f"{qedge.type if qedge.type else ''}-({output_qnode.id}:{output_qnode.type}{output_curie_summary})")
        return edge_query_graph

    @staticmethod
    def _deduplicate_nodes(dict_kg: DictKnowledgeGraph, edge_to_nodes_map: Dict[str, Dict[str, str]],
                           log: Response) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        log.debug(f"Deduplicating nodes")
        deduplicated_kg = DictKnowledgeGraph(nodes={qnode_id: dict() for qnode_id in dict_kg.nodes_by_qg_id},
                                             edges={qedge_id: dict() for qedge_id in dict_kg.edges_by_qg_id})
        updated_edge_to_nodes_map = {edge_id: dict() for edge_id in edge_to_nodes_map}
        curie_mappings = dict()

        # First deduplicate the nodes
        for qnode_id, nodes in dict_kg.nodes_by_qg_id.items():
            # Load preferred curie info from NodeSynonymizer for nodes we haven't seen before
            unmapped_node_ids = set(nodes).difference(set(curie_mappings))
            log.debug(f"Getting preferred curies for {qnode_id} nodes returned in this step")
            canonicalized_nodes = eu.get_canonical_curies_dict(list(unmapped_node_ids), log) if unmapped_node_ids else dict()
            if log.status != 'OK':
                return deduplicated_kg, updated_edge_to_nodes_map

            for node_id in unmapped_node_ids:
                # Figure out the preferred curie/name for this node
                node = nodes.get(node_id)
                canonicalized_node = canonicalized_nodes.get(node_id)
                if canonicalized_node:
                    preferred_curie = canonicalized_node.get('preferred_curie', node_id)
                    preferred_name = canonicalized_node.get('preferred_name', node.name)
                    preferred_type = eu.convert_string_or_list_to_list(canonicalized_node.get('preferred_type', node.type))
                    curie_mappings[node_id] = preferred_curie
                else:
                    # Means the NodeSynonymizer didn't recognize this curie
                    preferred_curie = node_id
                    preferred_name = node.name
                    preferred_type = node.type
                    curie_mappings[node_id] = preferred_curie

                # Add this node into our deduplicated KG as necessary # TODO: merge certain fields, like uri?
                if preferred_curie not in deduplicated_kg.nodes_by_qg_id[qnode_id]:
                    node.id = preferred_curie
                    node.name = preferred_name
                    node.type = preferred_type
                    deduplicated_kg.add_node(node, qnode_id)

        # Then update the edges to reflect changes made to the nodes
        for qedge_id, edges in dict_kg.edges_by_qg_id.items():
            for edge_id, edge in edges.items():
                edge.source_id = curie_mappings.get(edge.source_id)
                edge.target_id = curie_mappings.get(edge.target_id)
                if not edge.source_id or not edge.target_id:
                    log.error(f"Could not find preferred curie mappings for edge {edge_id}'s node(s)")
                    return deduplicated_kg, updated_edge_to_nodes_map
                deduplicated_kg.add_edge(edge, qedge_id)

                # Update the edge-to-node map for this edge (used down the line for pruning)
                for qnode_id, corresponding_node_id in edge_to_nodes_map[edge_id].items():
                    updated_edge_to_nodes_map[edge_id][qnode_id] = curie_mappings.get(corresponding_node_id)

        log.debug(f"After deduplication, answer KG counts are: {eu.get_printable_counts_by_qg_id(deduplicated_kg)}")
        return deduplicated_kg, updated_edge_to_nodes_map

    @staticmethod
    def _extract_query_subgraph(qedge_ids_to_expand: List[str], query_graph: QueryGraph, log: Response) -> QueryGraph:
        # This function extracts a sub-query graph containing the provided qedge IDs from a larger query graph
        sub_query_graph = QueryGraph(nodes=[], edges=[])

        for qedge_id in qedge_ids_to_expand:
            # Make sure this query edge actually exists in the query graph
            if not any(qedge.id == qedge_id for qedge in query_graph.edges):
                log.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph",
                          error_code="UnknownValue")
                return None
            qedge = next(qedge for qedge in query_graph.edges if qedge.id == qedge_id)

            # Make sure this qedge's qnodes actually exist in the query graph
            if not eu.get_query_node(query_graph, qedge.source_id):
                log.error(f"Qedge {qedge.id}'s source_id refers to a qnode that does not exist in the query graph: "
                          f"{qedge.source_id}", error_code="InvalidQEdge")
                return None
            if not eu.get_query_node(query_graph, qedge.target_id):
                log.error(f"Qedge {qedge.id}'s target_id refers to a qnode that does not exist in the query graph: "
                          f"{qedge.target_id}", error_code="InvalidQEdge")
                return None
            qnodes = [eu.get_query_node(query_graph, qedge.source_id),
                      eu.get_query_node(query_graph, qedge.target_id)]

            # Add (copies of) this qedge and its two qnodes to our new query sub graph
            qedge_copy = eu.copy_qedge(qedge)
            if not any(qedge.id == qedge_copy.id for qedge in sub_query_graph.edges):
                sub_query_graph.edges.append(qedge_copy)
            for qnode in qnodes:
                qnode_copy = eu.copy_qnode(qnode)
                if not any(qnode.id == qnode_copy.id for qnode in sub_query_graph.nodes):
                    sub_query_graph.nodes.append(qnode_copy)

        return sub_query_graph

    @staticmethod
    def _merge_answer_into_message_kg(answer_dict_kg: DictKnowledgeGraph, dict_kg: DictKnowledgeGraph, log: Response):
        # This function merges an answer KG (from the current edge/node expansion) into the overarching KG
        log.debug("Merging answer into Message.KnowledgeGraph")
        for qnode_id, nodes in answer_dict_kg.nodes_by_qg_id.items():
            for node_key, node in nodes.items():
                dict_kg.add_node(node, qnode_id)
        for qedge_id, edges_dict in answer_dict_kg.edges_by_qg_id.items():
            for edge_key, edge in edges_dict.items():
                dict_kg.add_edge(edge, qedge_id)

    @staticmethod
    def _prune_dead_end_paths(dict_kg: DictKnowledgeGraph, full_query_graph: QueryGraph,
                              node_usages_by_edges_map: Dict[str, Dict[str, Dict[str, str]]], log: Response):
        # This function removes any 'dead-end' paths from the KG. (Because edges are expanded one-by-one, not all edges
        # found in the last expansion will connect to edges in the next one)
        log.debug(f"Pruning any paths that are now dead ends")

        # Create a map of which qnodes are connected to which other qnodes
        # Example qnode_connections_map: {'n00': {'n01'}, 'n01': {'n00', 'n02'}, 'n02': {'n01'}}
        qnode_connections_map = dict()
        for qnode in full_query_graph.nodes:
            qnode_connections_map[qnode.id] = set()
            for qedge in full_query_graph.edges:
                if qedge.source_id == qnode.id or qedge.target_id == qnode.id:
                    connected_qnode_id = qedge.target_id if qedge.target_id != qnode.id else qedge.source_id
                    qnode_connections_map[qnode.id].add(connected_qnode_id)

        # Create a map of which nodes each node is connected to (organized by the qnode_id they're fulfilling)
        # Example node_usages_by_edges_map: {'e00': {'KG1:111221': {'n00': 'CUI:122', 'n01': 'CUI:124'}}}
        # Example node_connections_map: {'CUI:1222': {'n00': {'DOID:122'}, 'n02': {'UniProtKB:22', 'UniProtKB:333'}}}
        node_connections_map = dict()
        for qedge_id, edges_to_nodes_dict in node_usages_by_edges_map.items():
            current_qedge = next(qedge for qedge in full_query_graph.edges if qedge.id == qedge_id)
            qnode_ids = [current_qedge.source_id, current_qedge.target_id]
            for edge_id, node_usages_dict in edges_to_nodes_dict.items():
                for current_qnode_id in qnode_ids:
                    connected_qnode_id = next(qnode_id for qnode_id in qnode_ids if qnode_id != current_qnode_id)
                    current_node_id = node_usages_dict[current_qnode_id]
                    connected_node_id = node_usages_dict[connected_qnode_id]
                    if current_qnode_id not in node_connections_map:
                        node_connections_map[current_qnode_id] = dict()
                    if current_node_id not in node_connections_map[current_qnode_id]:
                        node_connections_map[current_qnode_id][current_node_id] = dict()
                    if connected_qnode_id not in node_connections_map[current_qnode_id][current_node_id]:
                        node_connections_map[current_qnode_id][current_node_id][connected_qnode_id] = set()
                    node_connections_map[current_qnode_id][current_node_id][connected_qnode_id].add(connected_node_id)

        # Iteratively remove all disconnected nodes until there are none left
        qnode_ids_already_expanded = list(node_connections_map.keys())
        found_dead_end = True
        while found_dead_end:
            found_dead_end = False
            for qnode_id in qnode_ids_already_expanded:
                qnode_ids_should_be_connected_to = qnode_connections_map[qnode_id].intersection(qnode_ids_already_expanded)
                for node_id, node_mappings_dict in node_connections_map[qnode_id].items():
                    # Check if any mappings are even entered for all qnode_ids this node should be connected to
                    if set(node_mappings_dict.keys()) != qnode_ids_should_be_connected_to:
                        if node_id in dict_kg.nodes_by_qg_id[qnode_id]:
                            dict_kg.nodes_by_qg_id[qnode_id].pop(node_id)
                            found_dead_end = True
                    else:
                        # Verify that at least one of the entered connections still exists (for each connected qnode_id)
                        for connected_qnode_id, connected_node_ids in node_mappings_dict.items():
                            if not connected_node_ids.intersection(set(dict_kg.nodes_by_qg_id[connected_qnode_id].keys())):
                                if node_id in dict_kg.nodes_by_qg_id[qnode_id]:
                                    dict_kg.nodes_by_qg_id[qnode_id].pop(node_id)
                                    found_dead_end = True

        # Then remove all orphaned edges
        for qedge_id, edges_dict in node_usages_by_edges_map.items():
            for edge_key, node_mappings in edges_dict.items():
                for qnode_id, used_node_id in node_mappings.items():
                    if used_node_id not in dict_kg.nodes_by_qg_id[qnode_id]:
                        if edge_key in dict_kg.edges_by_qg_id[qedge_id]:
                            dict_kg.edges_by_qg_id[qedge_id].pop(edge_key)

    def _get_order_to_expand_edges_in(self, query_graph: QueryGraph) -> List[QEdge]:
        # This function determines what order to expand the edges in a query graph in; it attempts to start with
        # qedges that have a qnode with a specific curie, and move out from there.
        edges_remaining = [edge for edge in query_graph.edges]
        ordered_edges = []
        while edges_remaining:
            if not ordered_edges:
                # Start with an edge that has a node with a curie specified
                edge_with_curie = self._get_edge_with_curie_node(query_graph)
                first_edge = edge_with_curie if edge_with_curie else edges_remaining[0]
                ordered_edges = [first_edge]
                edges_remaining.pop(edges_remaining.index(first_edge))
            else:
                # Add connected edges in a rightward (target) direction if possible
                right_end_edge = ordered_edges[-1]
                edge_connected_to_right_end = self._find_connected_qedge(edges_remaining, right_end_edge)
                if edge_connected_to_right_end:
                    ordered_edges.append(edge_connected_to_right_end)
                    edges_remaining.pop(edges_remaining.index(edge_connected_to_right_end))
                else:
                    left_end_edge = ordered_edges[0]
                    edge_connected_to_left_end = self._find_connected_qedge(edges_remaining, left_end_edge)
                    if edge_connected_to_left_end:
                        ordered_edges.insert(0, edge_connected_to_left_end)
                        edges_remaining.pop(edges_remaining.index(edge_connected_to_left_end))
        return ordered_edges

    def _is_input_qnode(self, qnode: QNode, qedge: QEdge) -> bool:
        all_ordered_qedges = self._get_order_to_expand_edges_in(self.message.query_graph)
        current_qedge_index = all_ordered_qedges.index(qedge)
        previous_qedge = all_ordered_qedges[current_qedge_index - 1] if current_qedge_index > 0 else None
        if previous_qedge and qnode.id in {previous_qedge.source_id, previous_qedge.target_id}:
            return True
        else:
            return False

    @staticmethod
    def _remove_self_edges(kg: DictKnowledgeGraph, edge_to_nodes_map: Dict[str, Dict[str, str]], qedge_id: QEdge,
                           qnodes: List[QNode], log: Response) -> DictKnowledgeGraph:
        log.debug(f"Removing any self-edges from the answer KG")
        # Remove any self-edges
        edges_to_remove = []
        for edge_key, edge in kg.edges_by_qg_id[qedge_id].items():
            if edge.source_id == edge.target_id:
                edges_to_remove.append(edge_key)
        for edge_id in edges_to_remove:
            kg.edges_by_qg_id[qedge_id].pop(edge_id)

        # Remove any nodes that may have been orphaned as a result of removing self-edges
        for qnode in qnodes:
            node_ids_used_by_edges_for_this_qnode_id = set()
            for edge in kg.edges_by_qg_id[qedge_id].values():
                node_ids_used_by_edges_for_this_qnode_id.add(edge_to_nodes_map[edge.id][qnode.id])
            orphan_node_ids_for_this_qnode_id = set(kg.nodes_by_qg_id[qnode.id].keys()).difference(node_ids_used_by_edges_for_this_qnode_id)
            for node_id in orphan_node_ids_for_this_qnode_id:
                kg.nodes_by_qg_id[qnode.id].pop(node_id)

        log.debug(f"After removing self-edges, answer KG counts are: {eu.get_printable_counts_by_qg_id(kg)}")
        return kg

    @staticmethod
    def _override_node_types(kg: KnowledgeGraph, qg: QueryGraph):
        # This method overrides KG nodes' types to match those requested in the QG, where possible (issue #987)
        qnode_id_to_type_map = {qnode.id: qnode.type for qnode in qg.nodes}
        for node in kg.nodes:
            corresponding_qnode_types = {qnode_id_to_type_map.get(qnode_id) for qnode_id in node.qnode_ids}
            non_none_types = [node_type for node_type in corresponding_qnode_types if node_type]
            if non_none_types:
                node.type = non_none_types

    @staticmethod
    def _get_orphan_query_node_ids(query_graph: QueryGraph):
        node_ids_used_by_edges = set()
        node_ids = set()
        for edge in query_graph.edges:
            node_ids_used_by_edges.add(edge.source_id)
            node_ids_used_by_edges.add(edge.target_id)
        for node in query_graph.nodes:
            node_ids.add(node.id)
        return list(node_ids.difference(node_ids_used_by_edges))

    @staticmethod
    def _get_edge_with_curie_node(query_graph: QueryGraph):
        for edge in query_graph.edges:
            source_qnode = eu.get_query_node(query_graph, edge.source_id)
            target_qnode = eu.get_query_node(query_graph, edge.target_id)
            if source_qnode.curie or target_qnode.curie:
                return edge
        return None

    @staticmethod
    def _find_connected_qedge(edge_list: List[QEdge], edge: QEdge) -> QEdge:
        edge_node_ids = {edge.source_id, edge.target_id}
        for potential_connected_edge in edge_list:
            potential_connected_edge_node_ids = {potential_connected_edge.source_id, potential_connected_edge.target_id}
            if edge_node_ids.intersection(potential_connected_edge_node_ids):
                return potential_connected_edge
        return None

    @staticmethod
    def _convert_string_to_bool_if_bool(bool_string: str) -> Union[bool, str]:
        if bool_string.lower() in {"true", "t"}:
            return True
        elif bool_string.lower() in {"false", "f"}:
            return False
        else:
            return bool_string

    @staticmethod
    def _get_number_of_curies(qnode: QNode) -> int:
        if qnode.curie and isinstance(qnode.curie, list):
            return len(qnode.curie)
        elif qnode.curie and isinstance(qnode.curie, str):
            return 1
        else:
            return 0

    def _get_qnode_curie_summary(self, qnode: QNode) -> str:
        num_curies = self._get_number_of_curies(qnode)
        if num_curies == 1:
            return f" {qnode.curie if isinstance(qnode.curie, str) else qnode.curie[0]}"
        elif num_curies > 1:
            return f" [{num_curies} curies]"
        else:
            return ""


def main():
    # Note that most of this is just manually doing what ARAXQuery() would normally do for you
    response = Response()
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
        "add_qnode(id=n01, type=protein, is_set=true)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]

    # Parse the raw action_list into commands and parameters
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    from ARAX_messenger import ARAXMessenger
    messenger = ARAXMessenger()
    expander = ARAXExpander()
    for action in actions:
        if action['command'] == 'create_message':
            result = messenger.create_message()
            message = result.data['message']
            response.data = result.data
        elif action['command'] == 'add_qnode':
            result = messenger.add_qnode(message, action['parameters'])
        elif action['command'] == 'add_qedge':
            result = messenger.add_qedge(message, action['parameters'])
        elif action['command'] == 'expand':
            result = expander.apply(message, action['parameters'])
        elif action['command'] == 'return':
            break
        else:
            response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
            print(response.show(level=Response.DEBUG))
            return response

        # Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    # Show the final response
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))
    print(response.show(level=Response.DEBUG))


if __name__ == "__main__":
    main()
