#!/bin/env python3
import sys
import os
from typing import List, Dict, Tuple, Union, Set, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand/")
import expand_utilities as eu
from expand_utilities import DictKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.edge import Edge


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXExpander:

    def __init__(self):
        self.default_kp = "ARAX/KG2"
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
            "enum": ["true", "false", "True", "False", "t", "f", "T", "F"],
            "default": "false",
            "type": "boolean",
            "description": "Whether to continue execution if no paths are found matching the query graph."
        }
        self.enforce_directionality_parameter_info = {
            "is_required": False,
            "examples": ["true", "false"],
            "enum": ["true", "false", "True", "False", "t", "f", "T", "F"],
            "default": "false",
            "type": "boolean",
            "description": "Whether to obey (vs. ignore) edge directions in the query graph."
        }
        self.use_synonyms_parameter_info = {
            "is_required": False,
            "examples": ["true", "false"],
            "enum": ["true", "false", "True", "False", "t", "f", "T", "F"],
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
                               "satisfy the query graph. It currently can answer questions involving the following "
                               "node types: gene, protein, disease, phenotypic_feature, pathway. QNode types are "
                               "required for GeneticsKP queries and it is sensitive to the use of disease vs. "
                               "phenotypic_feature. Note that QEdge types are irrelevant for GeneticsKP queries, since "
                               "GeneticsKP only outputs edges with a type of 'associated' (so Expand always uses that "
                               "as the QEdge type behind the scenes). Only MAGMA p-value edges are added by default, "
                               "but setting 'include_all_scores=true' will return all edges/scores the GeneticsKP "
                               "returns, including genetics-quantile scores.",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info,
                    "include_all_scores": {
                        "is_required": False,
                        "examples": ["true", "false"],
                        "enum": ["true", "false", "True", "False", "t", "f", "T", "F"],
                        "default": "false",
                        "type": "boolean",
                        "description": "Whether to return all scores/edges returned from the GeneticsKP (including "
                                       "genetics-quantile edges) or only MAGMA p-value edges."
                    }
                }
            },
            "MolePro": {
                "dsl_command": "expand(kp=MolePro)",
                "description": "This command reaches out to MolePro (the Molecular Provider) to find all bioentity "
                               "subpaths that satisfy the query graph. It currently can answer questions involving "
                               "the following node types: gene, protein, disease, chemical_substance. QNode types are "
                               "required for MolePro queries. Generally you should not specify a QEdge type for "
                               "MolePro queries (Expand uses 'correlated_with' by default behind the scenes, which is "
                               "the primary edge type of interest for ARAX in MolePro).",
                "parameters": {
                    "edge_id": self.edge_id_parameter_info,
                    "node_id": self.node_id_parameter_info,
                    "continue_if_no_results": self.continue_if_no_results_parameter_info,
                    "use_synonyms": self.use_synonyms_parameter_info,
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

    def apply(self, input_parameters, response=None):
        message = response.envelope.message
        log = response
        # Make sure the QG structure appears to be valid (cannot be disjoint, unless it consists only of qnodes)
        required_portion_of_qg = eu.get_required_portion_of_qg(message.query_graph)
        if required_portion_of_qg.edges and eu.qg_is_disconnected(required_portion_of_qg):
            log.error(f"Required portion of QG is disconnected. This is not allowed.", error_code="InvalidQG")
            return response

        # Create global slots to store some info that needs to persist between expand() calls
        if not hasattr(message, "encountered_kryptonite_edges_info"):
            message.encountered_kryptonite_edges_info = dict()
        encountered_kryptonite_edges_info = message.encountered_kryptonite_edges_info
        if not hasattr(message, "node_usages_by_edges_map"):
            message.node_usages_by_edges_map = dict()
        node_usages_by_edges_map = message.node_usages_by_edges_map

        # Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # Define a complete set of allowed parameters and their defaults
        kp = input_parameters.get("kp", self.default_kp)
        if kp not in self.command_definitions:
            response.error(f"Invalid KP. Options are: {set(self.command_definitions)}", error_code="InvalidKP")
            return response
        parameters = {"kp": kp}
        for kp_parameter_name, info_dict in self.command_definitions[kp]["parameters"].items():
            if info_dict["type"] == "boolean":
                parameters[kp_parameter_name] = self._convert_bool_string_to_bool(info_dict.get("default", ""))
            else:
                parameters[kp_parameter_name] = info_dict.get("default", None)

        # Override default values for any parameters passed in
        parameter_names_for_all_kps = {param for kp_documentation in self.command_definitions.values() for param in kp_documentation["parameters"]}
        for param_name, value in input_parameters.items():
            if param_name and param_name not in parameters:
                kp_specific_message = f"when kp={kp}" if param_name in parameter_names_for_all_kps else "for Expand"
                response.error(f"Supplied parameter {param_name} is not permitted {kp_specific_message}", error_code="InvalidParameter")
            else:
                parameters[param_name] = self._convert_bool_string_to_bool(value) if isinstance(value, str) else value

        # Handle situation where 'ARAX/KG2c' is entered as the kp (technically invalid, but we won't error out)
        if parameters['kp'].upper() == "ARAX/KG2C":
            parameters['kp'] = "ARAX/KG2"
            if not parameters['use_synonyms']:
                response.warning(f"KG2c is only used when use_synonyms=true; overriding use_synonyms to True")
                parameters['use_synonyms'] = True

        # Default to expanding the entire query graph if the user didn't specify what to expand
        if not parameters['edge_id'] and not parameters['node_id']:
            parameters['edge_id'] = [edge.id for edge in message.query_graph.edges]
            parameters['node_id'] = self._get_orphan_qnode_keys(message.query_graph)

        if response.status != 'OK':
            return response

        response.data['parameters'] = parameters
        self.parameters = parameters

        # Do the actual expansion
        response.debug(f"Applying Expand to Message with parameters {parameters}")
        input_qedge_ids = eu.convert_string_or_list_to_list(parameters['edge_id'])
        input_qnode_keys = eu.convert_string_or_list_to_list(parameters['node_id'])
        kp_to_use = self.parameters['kp']
        continue_if_no_results = self.parameters['continue_if_no_results']
        use_synonyms = self.parameters['use_synonyms']
        query_graph = message.query_graph

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_kg = eu.convert_standard_kg_to_qg_organized_kg(message.knowledge_graph)

        # Expand any specified edges
        if input_qedge_ids:
            query_sub_graph = self._extract_query_subgraph(input_qedge_ids, query_graph, log)
            if log.status != 'OK':
                return response
            log.debug(f"Query graph for this Expand() call is: {query_sub_graph.to_dict()}")

            # Expand the query graph edge by edge (much faster for neo4j queries, and allows easy integration with BTE)
            ordered_qedges_to_expand = self._get_order_to_expand_qedges_in(query_sub_graph)

            for qedge in ordered_qedges_to_expand:
                answer_kg, edge_node_usage_map = self._expand_edge(qedge, kp_to_use, dict_kg, continue_if_no_results,
                                                                   query_graph, use_synonyms, log)
                if log.status != 'OK':
                    return response
                elif qedge.exclude and not answer_kg.is_empty():
                    self._store_kryptonite_edge_info(edge_node_usage_map, qedge, encountered_kryptonite_edges_info, log)
                else:
                    # Update our map of which qnodes each of an edge's nodes fulfill (differs from source vs. target)
                    if qedge.id not in node_usages_by_edges_map:
                        node_usages_by_edges_map[qedge.id] = dict()
                    node_usages_by_edges_map[qedge.id].update(edge_node_usage_map)
                    self._merge_answer_into_message_kg(answer_kg, dict_kg, log)
                if log.status != 'OK':
                    return response

                self._apply_any_kryptonite_edges(dict_kg, query_graph, node_usages_by_edges_map, encountered_kryptonite_edges_info, log)
                self._prune_dead_end_paths(dict_kg, query_sub_graph, node_usages_by_edges_map, qedge, log)
                if log.status != 'OK':
                    return response

        # Expand any specified nodes
        if input_qnode_keys:
            for qnode_key in input_qnode_keys:
                answer_kg = self._expand_node(qnode_key, kp_to_use, continue_if_no_results, query_graph, use_synonyms, log)
                if log.status != 'OK':
                    return response

                self._merge_answer_into_message_kg(answer_kg, dict_kg, log)
                if log.status != 'OK':
                    return response

        # Convert message knowledge graph back to API standard format
        message.knowledge_graph = eu.convert_qg_organized_kg_to_standard_kg(dict_kg)

        # Override node types so that they match what was asked for in the query graph (where applicable) #987
        self._override_node_types(message.knowledge_graph, message.query_graph)
        
        # Make sure we don't have any orphan edges
        node_ids = {node.id for node in message.knowledge_graph.nodes}
        for edge in message.knowledge_graph.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                message.knowledge_graph.edges.remove(edge)

        # Return the response and done
        kg = message.knowledge_graph
        only_kryptonite_qedges_expanded = all([eu.get_query_edge(query_graph, qedge_id).exclude for qedge_id in input_qedge_ids])
        if not kg.nodes and not continue_if_no_results and not only_kryptonite_qedges_expanded:
            log.error(f"No paths were found in {kp_to_use} satisfying this query graph", error_code="NoResults")
        else:
            log.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges "
                     f"({eu.get_printable_counts_by_qg_id(dict_kg)})")
        return response

    def _expand_edge(self, qedge: QEdge, kp_to_use: str, dict_kg: DictKnowledgeGraph, continue_if_no_results: bool,
                     query_graph: QueryGraph, use_synonyms: bool, log: ARAXResponse) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        # This function answers a single-edge (one-hop) query using the specified knowledge provider
        log.info(f"Expanding qedge {qedge.id} using {kp_to_use}")
        answer_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Create a query graph for this edge (that uses synonyms as well as curies found in prior steps)
        edge_query_graph = self._get_query_graph_for_edge(qedge, query_graph, dict_kg, log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map
        if not any(qnode for qnode in edge_query_graph.nodes.values() if qnode.curie):
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
            elif kp_to_use == 'MolePro':
                from Expand.molepro_querier import MoleProQuerier
                kp_querier = MoleProQuerier(log)
            else:
                from Expand.kg_querier import KGQuerier
                kp_querier = KGQuerier(log, kp_to_use)
            answer_kg, edge_to_nodes_map = kp_querier.answer_one_hop_query(edge_query_graph)
            if log.status != 'OK':
                return answer_kg, edge_to_nodes_map
            log.debug(f"Query for edge {qedge.id} returned results ({eu.get_printable_counts_by_qg_id(answer_kg)})")

            # Do some post-processing (deduplicate nodes, remove self-edges..)
            if use_synonyms and kp_to_use != 'ARAX/KG2':  # KG2c is already deduplicated
                answer_kg, edge_to_nodes_map = self._deduplicate_nodes(answer_kg, edge_to_nodes_map, log)
            if eu.qg_is_fulfilled(edge_query_graph, answer_kg):
                answer_kg = self._remove_self_edges(answer_kg, edge_to_nodes_map, qedge.id, set(edge_query_graph.nodes), log)

            # Make sure our query has been fulfilled (unless we're continuing if no results)
            if not eu.qg_is_fulfilled(edge_query_graph, answer_kg) and not qedge.exclude and not qedge.option_group_id:
                if continue_if_no_results:
                    log.warning(f"No paths were found in {kp_to_use} satisfying qedge {qedge.id}")
                else:
                    log.error(f"No paths were found in {kp_to_use} satisfying qedge {qedge.id}", error_code="NoResults")

            return answer_kg, edge_to_nodes_map

    def _expand_node(self, qnode_key: str, kp_to_use: str, continue_if_no_results: bool, query_graph: QueryGraph,
                     use_synonyms: bool, log: ARAXResponse) -> DictKnowledgeGraph:
        # This function expands a single node using the specified knowledge provider
        log.debug(f"Expanding node {qnode_key} using {kp_to_use}")
        qnode = query_graph.nodes[qnode_key]
        single_node_qg = QueryGraph(nodes={qnode_key: qnode}, edges=dict())
        answer_kg = DictKnowledgeGraph()
        if log.status != 'OK':
            return answer_kg
        if not qnode.curie:
            log.error(f"Cannot expand a single query node if it doesn't have a curie", error_code="InvalidQuery")
            return answer_kg
        copy_of_qnode = eu.copy_qnode(qnode)

        # Consider both gene and protein when one is given
        if copy_of_qnode.type in ["protein", "gene"]:
            copy_of_qnode.type = ["protein", "gene"]
        log.debug(f"Modified query node is: {copy_of_qnode.to_dict()}")

        # Answer the query using the proper KP
        valid_kps_for_single_node_queries = ["ARAX/KG1", "ARAX/KG2"]
        if kp_to_use in valid_kps_for_single_node_queries:
            from Expand.kg_querier import KGQuerier
            kg_querier = KGQuerier(log, kp_to_use)
            answer_kg = kg_querier.answer_single_node_query(single_node_qg)
            log.info(f"Query for node {qnode_key} returned results ({eu.get_printable_counts_by_qg_id(answer_kg)})")

            # Make sure all qnodes have been fulfilled (unless we're continuing if no results)
            if log.status == 'OK' and not continue_if_no_results:
                if not answer_kg.nodes_by_qg_id.get(qnode_key):
                    log.error(f"Returned answer KG does not contain any results for QNode {qnode_key}",
                              error_code="UnfulfilledQGID")
                    return answer_kg

            if use_synonyms and kp_to_use != 'ARAX/KG2':  # KG2c is already deduplicated
                answer_kg, edge_node_usage_map = self._deduplicate_nodes(dict_kg=answer_kg,
                                                                         edge_to_nodes_map={},
                                                                         log=log)
            return answer_kg
        else:
            log.error(f"Invalid knowledge provider: {kp_to_use}. Valid options for single-node queries are "
                      f"{', '.join(valid_kps_for_single_node_queries)}", error_code="InvalidKP")
            return answer_kg

    def _get_query_graph_for_edge(self, qedge: QEdge, full_qg: QueryGraph, dict_kg: DictKnowledgeGraph, log: ARAXResponse) -> QueryGraph:
        # This function creates a query graph for the specified qedge, updating its qnodes' curies as needed
        edge_qg = QueryGraph(nodes=[], edges=[])
        qnode_keys = [qedge.source_id, qedge.target_id]

        # Add (a copy of) this qedge to our edge query graph
        edge_qg.edges.append(eu.copy_qedge(qedge))

        # Update this qedge's qnodes as appropriate and add (copies of) them to the edge query graph
        required_qedge_ids = {qedge.id for qedge in full_qg.edges if not qedge.option_group_id}
        expanded_qedge_ids = set(dict_kg.edges_by_qg_id)
        qedge_has_already_been_expanded = qedge.id in expanded_qedge_ids
        qedge_is_required = qedge.id in required_qedge_ids
        for qnode_key in qnode_keys:
            qnode = full_qg.nodes[qnode_key]
            qnode_copy = eu.copy_qnode(qnode)
            # Feed in curies from a prior Expand() step as the curie for this qnode as necessary
            qnode_already_fulfilled = qnode_copy.id in dict_kg.nodes_by_qg_id
            if qnode_already_fulfilled and not qnode_copy.curie:
                existing_curies_for_this_qnode_key = list(dict_kg.nodes_by_qg_id[qnode_copy.id])
                if qedge_has_already_been_expanded:
                    # Feed in curies only for 'input' qnodes if we're re-expanding this edge (i.e., with another KP)
                    if self._is_input_qnode(qnode_copy, qedge, full_qg):
                        qnode_copy.curie = existing_curies_for_this_qnode_key
                elif qedge_is_required:
                    # Only feed in curies to required qnodes if it was expansion of a REQUIRED qedge that grabbed them
                    qedge_ids_connected_to_qnode = eu.get_connected_qedge_keys(qnode_key, full_qg)
                    was_populated_by_required_edge = qedge_ids_connected_to_qnode.intersection(required_qedge_ids, expanded_qedge_ids)
                    if was_populated_by_required_edge:
                        qnode_copy.curie = existing_curies_for_this_qnode_key
                else:
                    qnode_copy.curie = existing_curies_for_this_qnode_key
            edge_qg.nodes[qnode_key] = qnode_copy

        # Consider both protein and gene if qnode's type is one of those (since KPs handle these differently)
        for qnode in edge_qg.nodes.values():
            if qnode.type in {'protein', 'gene'}:
                qnode.type = ['protein', 'gene']

        # Display a summary of what the modified query graph for this edge looks like
        qnodes_with_curies = [qnode_key for qnode_key, qnode in edge_qg.nodes.items() if qnode.curie]
        qnodes_without_curies = [qnode_key for qnode_key in edge_qg if qnode_key not in qnodes_with_curies]
        input_qnode_key = qnodes_with_curies[0] if qnodes_with_curies else qnodes_without_curies[0]
        output_qnode_key = set(edge_qg.nodes).difference({input_qnode_key})
        input_qnode = edge_qg[input_qnode_key]
        output_qnode = edge_qg[output_qnode_key]
        input_curie_summary = self._get_qnode_curie_summary(input_qnode)
        output_curie_summary = self._get_qnode_curie_summary(output_qnode)
        log.debug(f"Modified QG for this qedge is ({input_qnode_key}:{input_qnode.type}{input_curie_summary})-"
                  f"{qedge.type if qedge.type else ''}-({output_qnode_key}:{output_qnode.type}{output_curie_summary})")
        return edge_qg

    @staticmethod
    def _deduplicate_nodes(dict_kg: DictKnowledgeGraph, edge_to_nodes_map: Dict[str, Dict[str, str]],
                           log: ARAXResponse) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        log.debug(f"Deduplicating nodes")
        deduplicated_kg = DictKnowledgeGraph(nodes={qnode_key: dict() for qnode_key in dict_kg.nodes_by_qg_id},
                                             edges={qedge_id: dict() for qedge_id in dict_kg.edges_by_qg_id})
        updated_edge_to_nodes_map = {edge_id: dict() for edge_id in edge_to_nodes_map}
        curie_mappings = dict()

        # First deduplicate the nodes
        for qnode_key, nodes in dict_kg.nodes_by_qg_id.items():
            # Load preferred curie info from NodeSynonymizer for nodes we haven't seen before
            unmapped_node_ids = set(nodes).difference(set(curie_mappings))
            log.debug(f"Getting preferred curies for {qnode_key} nodes returned in this step")
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
                if preferred_curie not in deduplicated_kg.nodes_by_qg_id[qnode_key]:
                    node.id = preferred_curie
                    node.name = preferred_name
                    node.type = preferred_type
                    deduplicated_kg.add_node(node, qnode_key)

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
                for qnode_key, corresponding_node_id in edge_to_nodes_map[edge_id].items():
                    updated_edge_to_nodes_map[edge_id][qnode_key] = curie_mappings.get(corresponding_node_id)

        log.debug(f"After deduplication, answer KG counts are: {eu.get_printable_counts_by_qg_id(deduplicated_kg)}")
        return deduplicated_kg, updated_edge_to_nodes_map

    @staticmethod
    def _extract_query_subgraph(qedge_ids_to_expand: List[str], query_graph: QueryGraph, log: ARAXResponse) -> QueryGraph:
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
            if not query_graph.nodes.get(qedge.source_id):
                log.error(f"Qedge {qedge.id}'s source_id refers to a qnode that does not exist in the query graph: "
                          f"{qedge.source_id}", error_code="InvalidQEdge")
                return None
            if not query_graph.nodes.get(qedge.target_id):
                log.error(f"Qedge {qedge.id}'s target_id refers to a qnode that does not exist in the query graph: "
                          f"{qedge.target_id}", error_code="InvalidQEdge")
                return None

            # Add (copies of) this qedge and its two qnodes to our new query sub graph
            qedge_copy = eu.copy_qedge(qedge)
            if not any(qedge.id == qedge_copy.id for qedge in sub_query_graph.edges):
                sub_query_graph.edges.append(qedge_copy)
            for qnode_key in [qedge.source_id, qedge.target_id]:
                qnode_copy = eu.copy_qnode(query_graph[qnode_key])
                if qnode_key not in sub_query_graph.nodes:
                    sub_query_graph.nodes[qnode_key] = qnode_copy

        return sub_query_graph

    @staticmethod
    def _merge_answer_into_message_kg(answer_dict_kg: DictKnowledgeGraph, dict_kg: DictKnowledgeGraph, log: ARAXResponse):
        # This function merges an answer KG (from the current edge/node expansion) into the overarching KG
        log.debug("Merging answer into Message.KnowledgeGraph")
        for qnode_key, nodes in answer_dict_kg.nodes_by_qg_id.items():
            for node_key, node in nodes.items():
                dict_kg.add_node(node, qnode_key)
        for qedge_id, edges_dict in answer_dict_kg.edges_by_qg_id.items():
            for edge_key, edge in edges_dict.items():
                dict_kg.add_edge(edge, qedge_id)

    @staticmethod
    def _store_kryptonite_edge_info(edge_node_usage_map: Dict[str, Dict[str, str]], kryptonite_qedge: QEdge,
                                    encountered_kryptonite_edges_info: Dict[str, Dict[str, Set[str]]], log: ARAXResponse):
        """
        This function adds the IDs of nodes found by expansion of the given kryptonite ("not") edge to the global
        encountered_kryptonite_edges_info dictionary, which is organized by QG IDs. This allows Expand to "remember"
        which kryptonite edges/nodes it found previously, without adding them to the KG.
        Example of encountered_kryptonite_edges_info: {"e01": {"n00": {"MONDO:1"}, "n01": {"PR:1", "PR:2"}}}
        """
        log.debug(f"Storing info for kryptonite edges found")
        qnode_a_id = kryptonite_qedge.source_id
        qnode_b_id = kryptonite_qedge.target_id
        node_ids_fulfilling_qnode_a = {node_usages_dict[qnode_a_id] for node_usages_dict in edge_node_usage_map.values()}
        node_ids_fulfilling_qnode_b = {node_usages_dict[qnode_b_id] for node_usages_dict in edge_node_usage_map.values()}
        if kryptonite_qedge.id not in encountered_kryptonite_edges_info:
            encountered_kryptonite_edges_info[kryptonite_qedge.id] = dict()
        kryptonite_nodes_dict = encountered_kryptonite_edges_info[kryptonite_qedge.id]
        if qnode_a_id not in kryptonite_nodes_dict:
            kryptonite_nodes_dict[qnode_a_id] = set()
        if qnode_b_id not in kryptonite_nodes_dict:
            kryptonite_nodes_dict[qnode_b_id] = set()
        kryptonite_nodes_dict[qnode_a_id].update(node_ids_fulfilling_qnode_a)
        kryptonite_nodes_dict[qnode_b_id].update(node_ids_fulfilling_qnode_b)
        log.debug(f"Stored {len(node_ids_fulfilling_qnode_a)} {qnode_a_id} nodes and "
                  f"{len(node_ids_fulfilling_qnode_b)} {qnode_b_id} nodes from {kryptonite_qedge.id} kryptonite edges")

    @staticmethod
    def _apply_any_kryptonite_edges(dict_kg: DictKnowledgeGraph, full_query_graph: QueryGraph,
                                    node_usages_by_edges_map: Dict[str, Dict[str, Dict[str, str]]],
                                    encountered_kryptonite_edges_info: Dict[str, Dict[str, Set[str]]], log):
        """
        This function breaks any paths in the KG for which a "not" (exclude=True) condition has been met; the remains
        of the broken paths not used in other paths in the KG are cleaned up during later pruning of dead ends. The
        paths are broken by removing edges (vs. nodes) in order to help ensure that nodes that may also be used in
        valid paths are not accidentally removed from the KG. Optional kryptonite qedges are applied only to the option
        group they belong in; required kryptonite qedges are applied to all.
        """
        for qedge_id, edge_node_usage_map in node_usages_by_edges_map.items():
            current_qedge = eu.get_query_edge(full_query_graph, qedge_id)
            current_qedge_qnode_keys = {current_qedge.source_id, current_qedge.target_id}
            # Find kryptonite qedges that share one or more qnodes in common with our current qedge
            linked_kryptonite_qedges = [qedge for qedge in full_query_graph.edges if qedge.exclude and
                                        {qedge.source_id, qedge.target_id}.intersection(current_qedge_qnode_keys)]
            # Apply kryptonite edges only to edges within their same group (but apply required ones no matter what)
            linked_kryptonite_qedges_to_apply = [qedge for qedge in linked_kryptonite_qedges if
                                                 qedge.option_group_id == current_qedge.option_group_id or
                                                 qedge.option_group_id is None]
            edge_ids_to_remove = set()
            # Look for paths to blow away based on each (already expanded) kryptonite qedge in the same group
            for kryptonite_qedge in linked_kryptonite_qedges_to_apply:
                if kryptonite_qedge.id in encountered_kryptonite_edges_info:
                    # Mark edges for destruction if they match the kryptonite edge for all qnodes they have in common
                    kryptonite_qedge_qnode_keys = {kryptonite_qedge.source_id, kryptonite_qedge.target_id}
                    qnode_keys_in_common = list(current_qedge_qnode_keys.intersection(kryptonite_qedge_qnode_keys))
                    for edge_id, node_usages in edge_node_usage_map.items():
                        identical_nodes = [node_usages[qnode_key] for qnode_key in qnode_keys_in_common if node_usages[qnode_key]
                                           in encountered_kryptonite_edges_info[kryptonite_qedge.id][qnode_key]]
                        if len(identical_nodes) == len(qnode_keys_in_common):
                            edge_ids_to_remove.add(edge_id)

            # Actually remove the edges we've marked for destruction
            if edge_ids_to_remove:
                log.debug(f"Blowing away {len(edge_ids_to_remove)} {qedge_id} edges because they lie on a path with a "
                          f"'not' condition met (kryptonite)")
                for edge_id in edge_ids_to_remove:
                    node_usages_by_edges_map[qedge_id].pop(edge_id)
                    dict_kg.edges_by_qg_id[qedge_id].pop(edge_id)

    @staticmethod
    def _prune_dead_end_paths(dict_kg: DictKnowledgeGraph, query_graph: QueryGraph,
                              node_usages_by_edges_map: Dict[str, Dict[str, Dict[str, str]]], qedge_expanded: QEdge,
                              log: ARAXResponse):
        # This function removes any 'dead-end' paths from the KG. (Because edges are expanded one-by-one, not all edges
        # found in the last expansion will connect to edges in the next one)
        log.debug(f"Pruning any paths that are now dead ends")

        # Grab the part of the QG the most recently expanded qedge belongs to ('required' part or an option group)
        if qedge_expanded.option_group_id:
            group_qnode_keys = {qnode_key for qnode_key, qnode in query_graph.nodes.items()
                                if qnode.option_group_id == qedge_expanded.option_group_id}
            group_qedges = [qedge for qedge in query_graph.edges if qedge.option_group_id == qedge_expanded.option_group_id]
            sub_qg_qedge_ids = {qedge.id for qedge in group_qedges}
            qnode_keys_used_by_group_qedges = {qnode_key for qedge in group_qedges for qnode_key in {qedge.source_id, qedge.target_id}}
            sub_qg_qnode_keys = group_qnode_keys.union(qnode_keys_used_by_group_qedges)
            sub_qg = QueryGraph(nodes=[query_graph.nodes[qnode_key] for qnode_key in sub_qg_qnode_keys],
                                edges=[qedge for qedge in query_graph.edges if qedge.id in sub_qg_qedge_ids])
        else:
            required_qnode_keys = {qnode_key for qnode_key, qnode in query_graph.nodes.items() if not qnode.option_group_id}
            sub_qg_qedge_ids = {qedge.id for qedge in query_graph.edges if not qedge.option_group_id}
            sub_qg = QueryGraph(nodes={qnode_key: qnode for qnode_key, qnode in query_graph.nodes.items() if qnode_key in required_qnode_keys},
                                edges={qedge_key: qedge for qedge_key, qedge in query_graph.edges.items() if qedge_key in sub_qg_qedge_ids})
            sub_qg_qnode_keys = required_qnode_keys

        # Create a map of which qnodes are connected to which other qnodes (only for the relevant portion of the QG)
        # Example qnode_connections_map: {'n00': {'n01'}, 'n01': {'n00', 'n02'}, 'n02': {'n01'}}
        qnode_connections_map = dict()
        for qnode_key, qnode in sub_qg.nodes.items():
            qnode_connections_map[qnode_key] = set()
            for qedge in sub_qg.edges:
                if qedge.source_id == qnode_key or qedge.target_id == qnode_key:
                    other_qnode_key = qedge.target_id if qedge.target_id != qnode_key else qedge.source_id
                    qnode_connections_map[qnode_key].add(other_qnode_key)

        # Create a map of which nodes each node is connected to (organized by the qnode_key they're fulfilling)
        # Example node_usages_by_edges_map: {'e00': {'KG1:111221': {'n00': 'UMLS:122', 'n01': 'UMLS:124'}}}
        # Example node_connections_map: {'n01': {'UMLS:1222': {'n00': {'DOID:122'}, 'n02': {'UniProtKB:22'}}}, ...}
        node_connections_map = dict()
        for qedge_id, edges_to_nodes_dict in node_usages_by_edges_map.items():
            if qedge_id in sub_qg_qedge_ids:  # Only collect info for edges in the portion of the QG we're considering
                current_qedge = eu.get_query_edge(sub_qg, qedge_id)
                edges_to_nodes_dict = node_usages_by_edges_map[current_qedge.id]
                current_qedges_qnode_keys = {current_qedge.source_id, current_qedge.target_id}
                for edge_id, node_usages_dict in edges_to_nodes_dict.items():
                    for current_qnode_key in current_qedges_qnode_keys:
                        other_qnode_key = list(current_qedges_qnode_keys.difference({current_qnode_key}))[0]
                        current_node_id = node_usages_dict[current_qnode_key]
                        other_node_id = node_usages_dict[other_qnode_key]
                        if current_qnode_key not in node_connections_map:
                            node_connections_map[current_qnode_key] = dict()
                        if current_node_id not in node_connections_map[current_qnode_key]:
                            node_connections_map[current_qnode_key][current_node_id] = dict()
                        if other_qnode_key not in node_connections_map[current_qnode_key][current_node_id]:
                            node_connections_map[current_qnode_key][current_node_id][other_qnode_key] = set()
                        node_connections_map[current_qnode_key][current_node_id][other_qnode_key].add(other_node_id)

        # Iteratively remove all disconnected nodes until there are none left (for the relevant portion of the QG)
        qnode_keys_already_expanded = set(node_connections_map)
        qnode_keys_to_prune = qnode_keys_already_expanded.intersection(sub_qg_qnode_keys)
        found_dead_end = True
        while found_dead_end:
            found_dead_end = False
            for qnode_key in qnode_keys_to_prune:
                qnode_keys_should_be_connected_to = qnode_connections_map[qnode_key].intersection(qnode_keys_already_expanded)
                for node_id, node_mappings_dict in node_connections_map[qnode_key].items():
                    # Check if any mappings are even entered for all qnode_keys this node should be connected to
                    if set(node_mappings_dict.keys()) != qnode_keys_should_be_connected_to:
                        if node_id in dict_kg.nodes_by_qg_id[qnode_key]:
                            dict_kg.nodes_by_qg_id[qnode_key].pop(node_id)
                            found_dead_end = True
                    else:
                        # Verify that at least one of the entered connections still exists (for each connected qnode_key)
                        for other_qnode_key, connected_node_ids in node_mappings_dict.items():
                            if not connected_node_ids.intersection(set(dict_kg.nodes_by_qg_id[other_qnode_key].keys())):
                                if node_id in dict_kg.nodes_by_qg_id[qnode_key]:
                                    dict_kg.nodes_by_qg_id[qnode_key].pop(node_id)
                                    found_dead_end = True

        # Then remove all orphaned edges
        for qedge_id, edges_dict in node_usages_by_edges_map.items():
            for edge_key, node_mappings in edges_dict.items():
                for qnode_key, used_node_id in node_mappings.items():
                    if used_node_id not in dict_kg.nodes_by_qg_id[qnode_key]:
                        if edge_key in dict_kg.edges_by_qg_id[qedge_id]:
                            dict_kg.edges_by_qg_id[qedge_id].pop(edge_key)

        # And remove all orphaned nodes (that aren't supposed to be orphans - some qnodes may be orphans by design)
        qnode_keys_used_by_qedges = {qnode_key for qedge in query_graph.edges for qnode_key in {qedge.source_id, qedge.target_id}}
        non_orphan_qnode_keys = set(query_graph.nodes).intersection(qnode_keys_used_by_qedges)
        node_ids_used_by_edges = dict_kg.get_all_node_ids_used_by_edges()
        for non_orphan_qnode_key in non_orphan_qnode_keys:
            node_ids_in_kg = set(dict_kg.nodes_by_qg_id.get(non_orphan_qnode_key, []))
            orphan_node_ids = node_ids_in_kg.difference(node_ids_used_by_edges)
            for orphan_node_id in orphan_node_ids:
                dict_kg.nodes_by_qg_id[non_orphan_qnode_key].pop(orphan_node_id)

        log.debug(f"After pruning, KG counts are: {eu.get_printable_counts_by_qg_id(dict_kg)}")

    def _get_order_to_expand_qedges_in(self, query_graph: QueryGraph, log: ARAXResponse) -> List[QEdge]:
        """
        This function determines what order to expand the edges in a query graph in; it aims to start with a required,
        non-kryptonite qedge that has a qnode with a curie specified. It then looks for a qedge connected to that
        starting qedge, and so on.
        """
        qedges_remaining = [edge for edge in query_graph.edges]
        ordered_qedges = []
        while qedges_remaining:
            if not ordered_qedges:
                # Try to start with a required, non-kryptonite qedge that has a qnode with a curie specified
                qedges_with_curie = self._get_qedges_with_curie_qnode(query_graph)
                required_curie_qedges = [qedge for qedge in qedges_with_curie if not qedge.option_group_id]
                non_kryptonite_required_curie_qedges = [qedge for qedge in required_curie_qedges if not qedge.exclude]
                if non_kryptonite_required_curie_qedges:
                    first_qedge = non_kryptonite_required_curie_qedges[0]
                elif required_curie_qedges:
                    first_qedge = required_curie_qedges[0]
                elif qedges_with_curie:
                    first_qedge = qedges_with_curie[0]
                else:
                    first_qedge = qedges_remaining[0]
                ordered_qedges = [first_qedge]
                qedges_remaining.pop(qedges_remaining.index(first_qedge))
            else:
                # Add look for a qedge connected to the "subgraph" of qedges we've already added to our ordered list
                connected_qedge = self._find_qedge_connected_to_subgraph(ordered_qedges, qedges_remaining)
                if connected_qedge:
                    ordered_qedges.append(connected_qedge)
                    qedges_remaining.pop(qedges_remaining.index(connected_qedge))
                else:
                    log.error(f"Query graph is disconnected (has more than one component)", error_code="UnsupportedQG")
                    return []
        return ordered_qedges

    @staticmethod
    def _find_qedge_connected_to_subgraph(subgraph_qedge_list: List[QEdge], qedges_to_choose_from: List[QEdge]) -> Optional[QEdge]:
        qnode_keys_in_subgraph = {qnode_key for qedge in subgraph_qedge_list for qnode_key in {qedge.source_id, qedge.target_id}}
        connected_qedges = [qedge for qedge in qedges_to_choose_from if
                            qnode_keys_in_subgraph.intersection({qedge.source_id, qedge.target_id})]
        required_qedges = [qedge for qedge in connected_qedges if not qedge.option_group_id]
        required_kryptonite_qedges = [qedge for qedge in required_qedges if qedge.exclude]
        optional_kryptonite_qedges = [qedge for qedge in connected_qedges if qedge.option_group_id and qedge.exclude]
        if required_kryptonite_qedges:
            return required_kryptonite_qedges[0]
        elif required_qedges:
            return required_qedges[0]
        elif optional_kryptonite_qedges:
            return optional_kryptonite_qedges[0]
        elif connected_qedges:
            return connected_qedges[0]
        else:
            return None

    def _is_input_qnode(self, qnode_key: str, qedge: QEdge, qg: QueryGraph) -> bool:
        all_ordered_qedges = self._get_order_to_expand_qedges_in(qg)
        current_qedge_index = all_ordered_qedges.index(qedge)
        previous_qedge = all_ordered_qedges[current_qedge_index - 1] if current_qedge_index > 0 else None
        if previous_qedge and qnode_key in {previous_qedge.source_id, previous_qedge.target_id}:
            return True
        else:
            return False

    @staticmethod
    def _remove_self_edges(kg: DictKnowledgeGraph, edge_to_nodes_map: Dict[str, Dict[str, str]], qedge_id: QEdge,
                           qnode_keys: Set[str], log: ARAXResponse) -> DictKnowledgeGraph:
        log.debug(f"Removing any self-edges from the answer KG")
        # Remove any self-edges
        edges_to_remove = []
        for edge_key, edge in kg.edges_by_qg_id[qedge_id].items():
            if edge.source_id == edge.target_id:
                edges_to_remove.append(edge_key)
        for edge_id in edges_to_remove:
            kg.edges_by_qg_id[qedge_id].pop(edge_id)

        # Remove any nodes that may have been orphaned as a result of removing self-edges
        for qnode_key in qnode_keys:
            node_ids_used_by_edges_for_this_qnode_key = set()
            for edge in kg.edges_by_qg_id[qedge_id].values():
                node_ids_used_by_edges_for_this_qnode_key.add(edge_to_nodes_map[edge.id][qnode_key])
            orphan_node_ids_for_this_qnode_key = set(kg.nodes_by_qg_id[qnode_key]).difference(node_ids_used_by_edges_for_this_qnode_key)
            for node_id in orphan_node_ids_for_this_qnode_key:
                kg.nodes_by_qg_id[qnode_key].pop(node_id)

        log.debug(f"After removing self-edges, answer KG counts are: {eu.get_printable_counts_by_qg_id(kg)}")
        return kg

    @staticmethod
    def _override_node_types(kg: KnowledgeGraph, qg: QueryGraph):
        # This method overrides KG nodes' types to match those requested in the QG, where possible (issue #987)
        for node in kg.nodes:
            corresponding_qnode_types = {qg.nodes[qnode_key].type for qnode_key in node.qnode_keys}
            non_none_types = [node_type for node_type in corresponding_qnode_types if node_type]
            if non_none_types:
                node.type = non_none_types

    @staticmethod
    def _get_orphan_qnode_keys(query_graph: QueryGraph):
        qnode_keys_used_by_qedges = {qnode_key for qedge in query_graph.edges.values() for qnode_key in {qedge.source_id, qedge.target_id}}
        all_qnode_keys = set(query_graph.nodes)
        return list(all_qnode_keys.difference(qnode_keys_used_by_qedges))

    @staticmethod
    def _get_qedges_with_curie_qnode(query_graph: QueryGraph) -> List[QEdge]:
        return [qedge for qedge in query_graph.edges
                if query_graph.nodes[qedge.source_id].curie or query_graph.nodes[qedge.target_id].curie]

    @staticmethod
    def _find_connected_qedge(qedge_choices: List[QEdge], qedge: QEdge) -> QEdge:
        qedge_qnode_keys = {qedge.source_id, qedge.target_id}
        connected_qedges = []
        for other_qedge in qedge_choices:
            other_qedge_qnode_keys = {other_qedge.source_id, other_qedge.target_id}
            if qedge_qnode_keys.intersection(other_qedge_qnode_keys):
                connected_qedges.append(other_qedge)
        if connected_qedges:
            non_kryptonite_qedges = [connected_qedge for connected_qedge in connected_qedges if not connected_qedge.exclude]
            return non_kryptonite_qedges[0] if non_kryptonite_qedges else connected_qedges[0]
        else:
            return None

    @staticmethod
    def _convert_bool_string_to_bool(bool_string: str) -> Union[bool, str]:
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
    response = ARAXResponse()
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
        print(response.show(level=ARAXResponse.DEBUG))
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
            print(response.show(level=ARAXResponse.DEBUG))
            return response

        # Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=ARAXResponse.DEBUG))
            return response

    # Show the final response
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))
    print(response.show(level=ARAXResponse.DEBUG))


if __name__ == "__main__":
    main()
