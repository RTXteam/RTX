#!/bin/env python3
import multiprocessing
import sys
import os
import traceback
from collections import defaultdict
from typing import List, Dict, Tuple, Union, Set, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_decorator import ARAXDecorator
from ARAX_resultify import ARAXResultify
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand/")
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
from kp_selector import KPSelector
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.edge import Edge
from openapi_server.models.message import Message
from openapi_server.models.response import Response


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXExpander:

    def __init__(self):
        self.category_equivalencies = {"biolink:Protein": {"biolink:Gene"},
                                       "biolink:Gene": {"biolink:Protein"},
                                       "biolink:Drug": {"biolink:ChemicalSubstance"},
                                       "biolink:ChemicalSubstance": {"biolink:Drug"},
                                       "biolink:Disease": {"biolink:PhenotypicFeature",
                                                           "biolink:DiseaseOrPhenotypicFeature"},
                                       "biolink:PhenotypicFeature": {"biolink:Disease",
                                                                     "biolink:DiseaseOrPhenotypicFeature"},
                                       "biolink:DiseaseOrPhenotypicFeature": {"biolink:Disease",
                                                                              "biolink:PhenotypicFeature"}}
        self.kp_command_definitions = eu.get_kp_command_definitions()

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        considered_kps = sorted(list(set(self.kp_command_definitions)))
        kg2_definition = self.kp_command_definitions["RTX-KG2"]
        kp_less = {
                "dsl_command": "expand()",
                "description": f"This command will expand (aka, answer/fill) your query graph in an edge-by-edge "
                               f"fashion, intelligently selecting which KPs to use for each edge. Candidate KPs are: "
                               f"{', '.join(considered_kps)}. It selects KPs based on the meta information provided by "
                               f"their TRAPI APIs (when available) as well as a few heuristics aimed to ensure quick "
                               f"but useful answers. For each QEdge, it queries the selected KPs in parallel; it will "
                               f"timeout for a particular KP if it decides it's taking too long to respond.",
                "parameters": {
                    "edge_key": kg2_definition["parameters"]["edge_key"],
                    "node_key": kg2_definition["parameters"]["node_key"],
                    "enforce_directionality": kg2_definition["parameters"]["enforce_directionality"]
                }
            }
        return [kp_less] + list(self.kp_command_definitions.values())

    def apply(self, response, input_parameters, mode="ARAX"):
        force_local = False  # Flip this to make your machine act as the KG2 'API' (do not commit! for local use only)
        message = response.envelope.message
        # Initiate an empty knowledge graph if one doesn't already exist
        if message.knowledge_graph is None:
            message.knowledge_graph = KnowledgeGraph(nodes=dict(), edges=dict())
        log = response

        # If this is a query for the KG2 API, ignore all option_group_id and exclude properties (only does one-hop)
        if mode == "RTXKG2":
            log.debug(f"Ignoring all 'option_group_id' and 'exclude' properties on qnodes/qedges since we're in RTXKG2 mode")
            for qnode in message.query_graph.nodes.values():
                qnode.option_group_id = None
            for qedge in message.query_graph.edges.values():
                qedge.option_group_id = None
                qedge.exclude = None

        # Make sure the QG structure appears to be valid (cannot be disjoint, unless it consists only of qnodes)
        required_portion_of_qg = eu.get_required_portion_of_qg(message.query_graph)
        if required_portion_of_qg.edges and eu.qg_is_disconnected(required_portion_of_qg):
            log.error(f"Required portion of QG is disconnected. This is not allowed.", error_code="InvalidQG")
            return response

        # Create global slots to store some info that needs to persist between expand() calls
        if not hasattr(message, "encountered_kryptonite_edges_info"):
            message.encountered_kryptonite_edges_info = dict()

        # Basic checks on arguments
        if not isinstance(input_parameters, dict):
            log.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # Define a complete set of allowed parameters and their defaults (if the user specified a particular KP to use)
        kp = input_parameters.get("kp")
        if kp and kp not in self.kp_command_definitions:
            log.error(f"Invalid KP. Options are: {set(self.kp_command_definitions)}", error_code="InvalidKP")
            return response
        parameters = self._set_and_validate_parameters(kp, input_parameters, log)

        # Handle situation where 'RTX-KG2c' is entered as the kp (technically invalid, but we won't error out)
        if kp and parameters['kp'].upper() == "RTX-KG2C":
            parameters['kp'] = "RTX-KG2"

        # Default to expanding the entire query graph if the user didn't specify what to expand
        if not parameters['edge_key'] and not parameters['node_key']:
            parameters['edge_key'] = list(message.query_graph.edges)
            parameters['node_key'] = self._get_orphan_qnode_keys(message.query_graph)

        # We'll use a copy of the QG because we modify it for internal use within Expand
        query_graph = eu.copy_qg(message.query_graph)

        # Verify we understand all constraints (right now we don't support any)
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.constraints:
                constraint_ids = {constraint.id for constraint in qnode.constraints}
                log.error(f"Unsupported constraint(s) detected on qnode {qnode_key} for {constraint_ids}. "
                          f"Don't know how to handle these!", error_code="UnsupportedConstraint")
        for qedge_key, qedge in query_graph.edges.items():
            if qedge.constraints:
                constraint_ids = {constraint.id for constraint in qedge.constraints}
                log.error(f"Unsupported constraint(s) detected on qedge {qedge_key} for {constraint_ids}. "
                          f"Don't know how to handle these!", error_code="UnsupportedConstraint")

        if response.status != 'OK':
            return response

        response.data['parameters'] = parameters

        # Do the actual expansion
        log.debug(f"Applying Expand to Message with parameters {parameters}")
        input_qedge_keys = eu.convert_to_list(parameters['edge_key'])
        input_qnode_keys = eu.convert_to_list(parameters['node_key'])
        user_specified_kp = True if parameters['kp'] else False

        # Convert message knowledge graph to format organized by QG keys, for faster processing
        overarching_kg = eu.convert_standard_kg_to_qg_organized_kg(message.knowledge_graph)
        canonical_predicates_map = eu.load_canonical_predicates_map(log)

        # Add in any category equivalencies to the QG (e.g., protein == gene, since KPs handle these differently)
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.ids and not qnode.categories:
                # Infer categories for expand's internal use (in KP selection and etc.)
                qnode.categories = eu.get_preferred_categories(qnode.ids, log)
                log.debug(f"Inferred category for qnode {qnode_key} is {qnode.categories}")
            if qnode.categories and set(qnode.categories).intersection(self.category_equivalencies):
                equivalent_categories = {equivalent_category for category in qnode.categories
                                         for equivalent_category in self.category_equivalencies.get(category, [])}
                qnode.categories = list(set(qnode.categories).union(equivalent_categories))
                log.debug(f"Expand will consider qnode {qnode_key}'s category to be {qnode.categories}")
        # Make sure QG only uses canonical predicates
        if mode == "ARAX":
            log.debug(f"Making sure QG only uses canonical predicates")
            for qedge in query_graph.edges.values():
                if qedge.predicates:
                    canonical_predicates = {canonical_predicates_map.get(predicate, predicate) for predicate in qedge.predicates}
                    qedge.predicates = list(canonical_predicates)

        # Expand any specified edges
        if input_qedge_keys:
            query_sub_graph = self._extract_query_subgraph(input_qedge_keys, query_graph, log)
            if log.status != 'OK':
                return response
            log.debug(f"Query graph for this Expand() call is: {query_sub_graph.to_dict()}")

            # Expand the query graph edge-by-edge
            ordered_qedge_keys_to_expand = self._get_order_to_expand_qedges_in(query_sub_graph, log)
            for qedge_key in ordered_qedge_keys_to_expand:
                qedge = query_graph.edges[qedge_key]
                # Create a query graph for this edge (that uses curies found in prior steps)
                one_hop_qg = self._get_query_graph_for_edge(qedge_key, query_graph, overarching_kg, log)
                if log.status != 'OK':
                    return response

                # Figure out which KPs would be best to expand this edge with (if no KP was specified)
                if not user_specified_kp:
                    kp_selector = KPSelector(log)
                    kps_to_query = kp_selector.get_kps_for_single_hop_qg(one_hop_qg)
                    log.info(f"The KPs Expand decided to answer {qedge_key} with are: {kps_to_query}")
                else:
                    kps_to_query = {parameters["kp"]}

                # Send this query to each KP selected to answer it (in parallel)
                if len(kps_to_query) > 1:
                    num_cpus = multiprocessing.cpu_count()
                    empty_log = ARAXResponse()  # We'll have to merge processes' logs together afterwards
                    kp_selector = KPSelector(empty_log)
                    with multiprocessing.Pool(num_cpus) as pool:
                        kp_answers = pool.starmap(self._expand_edge, [[one_hop_qg, kp_to_use, input_parameters,
                                                                       mode, user_specified_kp,
                                                                       force_local, canonical_predicates_map,
                                                                       kp_selector, empty_log]
                                                                      for kp_to_use in kps_to_query])
                elif len(kps_to_query) == 1:
                    # Don't bother creating separate processes if we only selected one KP
                    kp_to_use = next(kp_to_use for kp_to_use in kps_to_query)
                    kp_selector = KPSelector(log)
                    kp_answers = [self._expand_edge(one_hop_qg, kp_to_use, input_parameters, mode,
                                                    user_specified_kp, force_local, canonical_predicates_map,
                                                    kp_selector, log)]
                else:
                    log.error(f"Expand could not find any KPs to answer {qedge_key} with.", error_code="NoResults")
                    return response

                # Post-process all the KPs' answers and merge into our overarching KG
                for answer_kg, kp_log in kp_answers:
                    if len(kps_to_query) > 1:
                        if kp_log.status != 'OK':
                            kp_log.status = 'OK'  # We don't want to halt just because one KP reported an error #1500
                        log.merge(kp_log)  # Processes can't share the main log, so we merge their individual logs here
                    if response.status != 'OK':
                        return response
                    if mode == "ARAX" and qedge.exclude and not answer_kg.is_empty():
                        self._store_kryptonite_edge_info(answer_kg, qedge_key, message.query_graph,
                                                         message.encountered_kryptonite_edges_info, response)
                    else:
                        self._merge_answer_into_message_kg(answer_kg, overarching_kg, message.query_graph, mode, response)
                    if response.status != 'OK':
                        return response

                # Do some pruning and apply kryptonite edges (only if we're not in KG2 mode)
                if mode == "ARAX":
                    self._apply_any_kryptonite_edges(overarching_kg, message.query_graph,
                                                     message.encountered_kryptonite_edges_info, response)
                    overarching_kg = self._prune_dead_end_paths(overarching_kg, query_graph, response)
                    if response.status != 'OK':
                        return response

                # Make sure we found at least SOME answers for this edge
                if not eu.qg_is_fulfilled(one_hop_qg, overarching_kg) and not qedge.exclude and not qedge.option_group_id:
                    log.warning(f"No paths were found in {kps_to_query} satisfying qedge {qedge_key}")
                    return response

        # Expand any specified nodes
        if input_qnode_keys:
            kp_to_use = parameters["kp"] if user_specified_kp else "RTX-KG2"  # Only KG2 does single-node queries
            for qnode_key in input_qnode_keys:
                answer_kg = self._expand_node(qnode_key, kp_to_use, query_graph, mode, user_specified_kp, force_local, log)
                if log.status != 'OK':
                    return response
                self._merge_answer_into_message_kg(answer_kg, overarching_kg, message.query_graph, mode, log)
                if log.status != 'OK':
                    return response

        # Convert message knowledge graph back to standard TRAPI
        message.knowledge_graph = eu.convert_qg_organized_kg_to_standard_kg(overarching_kg)

        # Override node types so that they match what was asked for in the query graph (where applicable) #987
        self._override_node_categories(message.knowledge_graph, message.query_graph)

        # Decorate all nodes with additional attributes info from KG2c (iri, description, etc.)
        if mode == "ARAX":  # Skip doing this for KG2 (until can pass minimal_metadata param)
            decorator = ARAXDecorator()
            decorator.apply(response)

        # Return the response and done
        kg = message.knowledge_graph
        log.info(f"After Expand, the KG has {len(kg.nodes)} nodes and {len(kg.edges)} edges "
                 f"({eu.get_printable_counts_by_qg_id(overarching_kg)})")

        return response

    def _expand_edge(self, edge_qg: QueryGraph, kp_to_use: str, input_parameters: Dict[str, any], mode: str,
                     user_specified_kp: bool, force_local: bool, canonical_predicates_map: Dict[str, str],
                     kp_selector: KPSelector, log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, ARAXResponse]:
        # This function answers a single-edge (one-hop) query using the specified knowledge provider
        qedge_key = next(qedge_key for qedge_key in edge_qg.edges)
        qedge = edge_qg.edges[qedge_key]
        log.info(f"Expanding qedge {qedge_key} using {kp_to_use}")
        answer_kg = QGOrganizedKnowledgeGraph()

        # Make sure we have all default parameters set specific to the KP we'll be using
        log.data["parameters"] = self._set_and_validate_parameters(kp_to_use, input_parameters, log)

        # Make sure at least one of the qnodes has a curie specified
        if not any(qnode for qnode in edge_qg.nodes.values() if qnode.ids):
            log.error(f"Cannot expand an edge for which neither end has any curies. (Could not find curies to use from "
                      f"a prior expand step, and neither qnode has a curie specified.)", error_code="InvalidQuery")
            return answer_kg, log
        # Make sure the specified KP is a valid option
        allowable_kps = set(self.kp_command_definitions.keys())
        if kp_to_use not in allowable_kps:
            log.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are {', '.join(allowable_kps)}",
                      error_code="InvalidKP")
            return answer_kg, log

        # Route this query to the proper place depending on the KP
        from Expand.kg2_querier import KG2Querier
        try:
            if kp_to_use == 'COHD':
                from Expand.COHD_querier import COHDQuerier
                kp_querier = COHDQuerier(log)
            elif kp_to_use == 'DTD':
                from Expand.DTD_querier import DTDQuerier
                kp_querier = DTDQuerier(log)
            elif kp_to_use == 'CHP':
                from Expand.CHP_querier import CHPQuerier
                kp_querier = CHPQuerier(log)
                # This is done in TRAPIQuerier for other KPs
                edge_qg = eu.make_qg_use_supported_prefixes(kp_selector, edge_qg, kp_to_use, log)
                if not edge_qg:  # Means no curies had prefixes CHP supports
                    return QGOrganizedKnowledgeGraph(), log
            elif kp_to_use == 'NGD':
                from Expand.ngd_querier import NGDQuerier
                kp_querier = NGDQuerier(log)
            elif kp_to_use == 'RTX-KG2' and mode == 'RTXKG2':
                kp_querier = KG2Querier(log)
            else:
                # This is a general purpose querier for use with any KPs that we query via their TRAPI 1.0+ API
                from Expand.trapi_querier import TRAPIQuerier
                kp_querier = TRAPIQuerier(log, kp_to_use, user_specified_kp, kp_selector, force_local)

            # Actually answer the query using the Querier we identified above
            answer_kg = kp_querier.answer_one_hop_query(edge_qg)
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            if user_specified_kp:
                log.error(f"An uncaught error was thrown while trying to Expand using {kp_to_use}. Error was: {tb}",
                          error_code=f"UncaughtError")
            else:
                log.warning(f"An uncaught error was thrown while trying to Expand using {kp_to_use}, so I couldn't "
                            f"get answers from that KP. Error was: {tb}")
            return QGOrganizedKnowledgeGraph(), log

        if log.status != 'OK':
            return answer_kg, log

        # Make sure the KP's answer only uses canonical predicates (KG2 already does this, so no need to check it)
        if not isinstance(kp_querier, KG2Querier):
            answer_kg = eu.check_for_canonical_predicates(answer_kg, canonical_predicates_map, kp_to_use, log)

        log.info(f"{kp_to_use}: Query for edge {qedge_key} completed ({eu.get_printable_counts_by_qg_id(answer_kg)})")

        # Do some post-processing (deduplicate nodes, remove self-edges..)
        if kp_to_use != 'RTX-KG2':  # KG2c is already deduplicated
            answer_kg = self._deduplicate_nodes(answer_kg, kp_to_use, log)
        if eu.qg_is_fulfilled(edge_qg, answer_kg):
            answer_kg = self._remove_self_edges(answer_kg, kp_to_use, qedge_key, qedge, log)

        return answer_kg, log

    def _expand_node(self, qnode_key: str, kp_to_use: str, query_graph: QueryGraph, mode: str, user_specified_kp: bool,
                     force_local: bool, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        # This function expands a single node using the specified knowledge provider
        log.debug(f"Expanding node {qnode_key} using {kp_to_use}")
        qnode = query_graph.nodes[qnode_key]
        single_node_qg = QueryGraph(nodes={qnode_key: qnode}, edges=dict())
        answer_kg = QGOrganizedKnowledgeGraph()
        if log.status != 'OK':
            return answer_kg
        if not qnode.ids:
            log.error(f"Cannot expand a single query node if it doesn't have a curie", error_code="InvalidQuery")
            return answer_kg

        # Answer the query using the proper KP (only our own KP answers single-node queries)
        valid_kps_for_single_node_queries = ["RTX-KG2"]
        if kp_to_use in valid_kps_for_single_node_queries:
            if kp_to_use == 'RTX-KG2' and mode == 'RTXKG2':
                from Expand.kg2_querier import KG2Querier
                kp_querier = KG2Querier(log)
            else:
                from Expand.trapi_querier import TRAPIQuerier
                kp_querier = TRAPIQuerier(log, kp_to_use, user_specified_kp, force_local)
            answer_kg = kp_querier.answer_single_node_query(single_node_qg)
            log.info(f"Query for node {qnode_key} returned results ({eu.get_printable_counts_by_qg_id(answer_kg)})")

            if kp_to_use != 'RTX-KG2':  # KG2c is already deduplicated
                answer_kg = self._deduplicate_nodes(answer_kg, kp_to_use, log)

            return answer_kg
        else:
            log.error(f"Invalid knowledge provider: {kp_to_use}. Valid options for single-node queries are "
                      f"{', '.join(valid_kps_for_single_node_queries)}", error_code="InvalidKP")
            return answer_kg

    def _get_query_graph_for_edge(self, qedge_key: str, full_qg: QueryGraph, overarching_kg: QGOrganizedKnowledgeGraph, log: ARAXResponse) -> QueryGraph:
        # This function creates a query graph for the specified qedge, updating its qnodes' curies as needed
        edge_qg = QueryGraph(nodes=dict(), edges=dict())
        qedge = full_qg.edges[qedge_key]
        qnode_keys = [qedge.subject, qedge.object]

        # Add (a copy of) this qedge to our edge query graph
        edge_qg.edges[qedge_key] = eu.copy_qedge(qedge)

        # Update this qedge's qnodes as appropriate and add (copies of) them to the edge query graph
        required_qedge_keys = {qe_key for qe_key, qe in full_qg.edges.items() if not qe.option_group_id}
        expanded_qedge_keys = set(overarching_kg.edges_by_qg_id)
        qedge_has_already_been_expanded = qedge_key in expanded_qedge_keys
        qedge_is_required = qedge_key in required_qedge_keys
        for qnode_key in qnode_keys:
            qnode = full_qg.nodes[qnode_key]
            qnode_copy = eu.copy_qnode(qnode)
            # Feed in curies from a prior Expand() step as the curie for this qnode as necessary
            qnode_already_fulfilled = qnode_key in overarching_kg.nodes_by_qg_id
            if qnode_already_fulfilled and not qnode_copy.ids:
                existing_curies_for_this_qnode_key = list(overarching_kg.nodes_by_qg_id[qnode_key])
                if qedge_has_already_been_expanded:
                    # Feed in curies only for 'input' qnodes if we're re-expanding this edge (i.e., with another KP)
                    if self._is_input_qnode(qnode_key, qedge_key, full_qg, log):
                        qnode_copy.ids = existing_curies_for_this_qnode_key
                elif qedge_is_required:
                    # Only feed in curies to required qnodes if it was expansion of a REQUIRED qedge that grabbed them
                    qedge_keys_connected_to_qnode = eu.get_connected_qedge_keys(qnode_key, full_qg)
                    was_populated_by_required_edge = qedge_keys_connected_to_qnode.intersection(required_qedge_keys, expanded_qedge_keys)
                    if was_populated_by_required_edge:
                        qnode_copy.ids = existing_curies_for_this_qnode_key
                else:
                    qnode_copy.ids = existing_curies_for_this_qnode_key
            edge_qg.nodes[qnode_key] = qnode_copy

        # Display a summary of what the modified query graph for this edge looks like
        qnodes_with_curies = [qnode_key for qnode_key, qnode in edge_qg.nodes.items() if qnode.ids]
        qnodes_without_curies = [qnode_key for qnode_key in edge_qg.nodes if qnode_key not in qnodes_with_curies]
        input_qnode_key = qnodes_with_curies[0] if qnodes_with_curies else qnodes_without_curies[0]
        output_qnode_key = list(set(edge_qg.nodes).difference({input_qnode_key}))[0]
        input_qnode = edge_qg.nodes[input_qnode_key]
        output_qnode = edge_qg.nodes[output_qnode_key]
        input_curie_summary = self._get_qnode_curie_summary(input_qnode)
        output_curie_summary = self._get_qnode_curie_summary(output_qnode)
        log.debug(f"Modified QG for this qedge is ({input_qnode_key}:{input_qnode.categories}{input_curie_summary})-"
                  f"{qedge.predicates if qedge.predicates else ''}-({output_qnode_key}:{output_qnode.categories}{output_curie_summary})")
        return edge_qg

    @staticmethod
    def _deduplicate_nodes(answer_kg: QGOrganizedKnowledgeGraph, kp_name: str, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        log.debug(f"{kp_name}: Deduplicating nodes")
        deduplicated_kg = QGOrganizedKnowledgeGraph(nodes={qnode_key: dict() for qnode_key in answer_kg.nodes_by_qg_id},
                                                    edges={qedge_key: dict() for qedge_key in answer_kg.edges_by_qg_id})
        curie_mappings = dict()

        # First deduplicate the nodes
        for qnode_key, nodes in answer_kg.nodes_by_qg_id.items():
            # Load preferred curie info from NodeSynonymizer
            log.debug(f"{kp_name}: Getting preferred curies for {qnode_key} nodes returned in this step")
            canonicalized_nodes = eu.get_canonical_curies_dict(list(nodes), log) if nodes else dict()
            if log.status != 'OK':
                return deduplicated_kg

            for node_key in nodes:
                # Figure out the preferred curie/name for this node
                node = nodes.get(node_key)
                canonicalized_node = canonicalized_nodes.get(node_key)
                if canonicalized_node:
                    preferred_curie = canonicalized_node.get('preferred_curie', node_key)
                    preferred_name = canonicalized_node.get('preferred_name', node.name)
                    preferred_type = canonicalized_node.get('preferred_type')
                    preferred_categories = eu.convert_to_list(preferred_type) if preferred_type else node.categories
                    curie_mappings[node_key] = preferred_curie
                else:
                    # Means the NodeSynonymizer didn't recognize this curie
                    preferred_curie = node_key
                    preferred_name = node.name
                    preferred_categories = node.categories
                    curie_mappings[node_key] = preferred_curie

                # Add this node into our deduplicated KG as necessary
                if preferred_curie not in deduplicated_kg.nodes_by_qg_id[qnode_key]:
                    node_key = preferred_curie
                    node.name = preferred_name
                    node.categories = preferred_categories
                    deduplicated_kg.add_node(node_key, node, qnode_key)

        # Then update the edges to reflect changes made to the nodes
        for qedge_key, edges in answer_kg.edges_by_qg_id.items():
            for edge_key, edge in edges.items():
                edge.subject = curie_mappings.get(edge.subject)
                edge.object = curie_mappings.get(edge.object)
                if not edge.subject or not edge.object:
                    log.error(f"{kp_name}: Could not find preferred curie mappings for edge {edge_key}'s node(s)")
                    return deduplicated_kg
                deduplicated_kg.add_edge(edge_key, edge, qedge_key)

        log.debug(f"{kp_name}: After deduplication, answer KG counts are: {eu.get_printable_counts_by_qg_id(deduplicated_kg)}")
        return deduplicated_kg

    @staticmethod
    def _extract_query_subgraph(qedge_keys_to_expand: List[str], query_graph: QueryGraph, log: ARAXResponse) -> QueryGraph:
        # This function extracts a sub-query graph containing the provided qedge IDs from a larger query graph
        sub_query_graph = QueryGraph(nodes=dict(), edges=dict())

        for qedge_key in qedge_keys_to_expand:
            # Make sure this query edge actually exists in the query graph
            if qedge_key not in query_graph.edges:
                log.error(f"An edge with ID '{qedge_key}' does not exist in Message.QueryGraph",
                          error_code="UnknownValue")
                return None
            qedge = query_graph.edges[qedge_key]

            # Make sure this qedge's qnodes actually exist in the query graph
            if not query_graph.nodes.get(qedge.subject):
                log.error(f"Qedge {qedge_key}'s subject refers to a qnode that does not exist in the query graph: "
                          f"{qedge.subject}", error_code="InvalidQEdge")
                return None
            if not query_graph.nodes.get(qedge.object):
                log.error(f"Qedge {qedge_key}'s object refers to a qnode that does not exist in the query graph: "
                          f"{qedge.object}", error_code="InvalidQEdge")
                return None

            # Add (copies of) this qedge and its two qnodes to our new query sub graph
            qedge_copy = eu.copy_qedge(qedge)
            if qedge_key not in sub_query_graph.edges:
                sub_query_graph.edges[qedge_key] = qedge_copy
            for qnode_key in [qedge_copy.subject, qedge_copy.object]:
                qnode_copy = eu.copy_qnode(query_graph.nodes[qnode_key])
                if qnode_key not in sub_query_graph.nodes:
                    sub_query_graph.nodes[qnode_key] = qnode_copy

        return sub_query_graph

    @staticmethod
    def _merge_answer_into_message_kg(answer_kg: QGOrganizedKnowledgeGraph, overarching_kg: QGOrganizedKnowledgeGraph,
                                      overarching_qg: QueryGraph, mode: str, log: ARAXResponse):
        # This function merges an answer KG (from the current edge/node expansion) into the overarching KG
        log.debug("Merging answer into Message.KnowledgeGraph")
        pinned_curies_map = defaultdict(set)
        for qnode_key, qnode in overarching_qg.nodes.items():
            if qnode.ids:
                # Get canonicalized versions of any curies in the QG, as appropriate
                curies = eu.get_canonical_curies_list(qnode.ids, log)
                for curie in curies:
                    pinned_curies_map[curie].add(qnode_key)

        for qnode_key, nodes in answer_kg.nodes_by_qg_id.items():
            for node_key, node in nodes.items():
                # Exclude nodes that correspond to a 'pinned' curie in the QG but are fulfilling a different qnode
                if mode == "ARAX" and node_key in pinned_curies_map:
                    if qnode_key in pinned_curies_map[node_key]:
                        overarching_kg.add_node(node_key, node, qnode_key)
                    else:
                        log.debug(f"Not letting node {node_key} fulfill qnode {qnode_key} because it's a pinned curie "
                                  f"for {pinned_curies_map[node_key]}")
                else:
                    overarching_kg.add_node(node_key, node, qnode_key)
        for qedge_key, edges_dict in answer_kg.edges_by_qg_id.items():
            qedge = overarching_qg.edges[qedge_key]
            for edge_key, edge in edges_dict.items():
                if (edge.subject in overarching_kg.nodes_by_qg_id[qedge.subject] and
                    edge.object in overarching_kg.nodes_by_qg_id[qedge.object]) or \
                        (edge.subject in overarching_kg.nodes_by_qg_id[qedge.object] and
                         edge.object in overarching_kg.nodes_by_qg_id[qedge.subject]):
                    overarching_kg.add_edge(edge_key, edge, qedge_key)
                else:
                    log.debug(f"Removing edge {edge_key} (fulfilling {qedge_key}) from the KG because it's orphaned")

    @staticmethod
    def _store_kryptonite_edge_info(kryptonite_kg: QGOrganizedKnowledgeGraph, kryptonite_qedge_key: str, qg: QueryGraph,
                                    encountered_kryptonite_edges_info: Dict[str, Dict[str, Set[str]]], log: ARAXResponse):
        """
        This function adds the IDs of nodes found by expansion of the given kryptonite ("not") edge to the global
        encountered_kryptonite_edges_info dictionary, which is organized by QG IDs. This allows Expand to "remember"
        which kryptonite edges/nodes it found previously, without adding them to the KG.
        Example of encountered_kryptonite_edges_info: {"e01": {"n00": {"MONDO:1"}, "n01": {"PR:1", "PR:2"}}}
        """
        log.debug(f"Storing info for kryptonite edges found")
        kryptonite_qedge = qg.edges[kryptonite_qedge_key]
        # First just initiate empty nested dictionaries/sets as needed
        if kryptonite_qedge_key not in encountered_kryptonite_edges_info:
            encountered_kryptonite_edges_info[kryptonite_qedge_key] = dict()
        kryptonite_nodes_dict = encountered_kryptonite_edges_info[kryptonite_qedge_key]
        if kryptonite_qedge.subject not in kryptonite_nodes_dict:
            kryptonite_nodes_dict[kryptonite_qedge.subject] = set()
        if kryptonite_qedge.object not in kryptonite_nodes_dict:
            kryptonite_nodes_dict[kryptonite_qedge.object] = set()
        # Then add the nodes we found during this kryptonite expansion into our global record
        node_keys_fulfilling_kryptonite_subject = set(kryptonite_kg.nodes_by_qg_id[kryptonite_qedge.subject])
        node_keys_fulfilling_kryptonite_object = set(kryptonite_kg.nodes_by_qg_id[kryptonite_qedge.object])
        kryptonite_nodes_dict[kryptonite_qedge.subject].update(node_keys_fulfilling_kryptonite_subject)
        kryptonite_nodes_dict[kryptonite_qedge.object].update(node_keys_fulfilling_kryptonite_object)
        log.debug(f"Stored {len(node_keys_fulfilling_kryptonite_subject)} {kryptonite_qedge.subject} nodes and "
                  f"{len(node_keys_fulfilling_kryptonite_object)} {kryptonite_qedge.object} nodes from "
                  f"{kryptonite_qedge_key} kryptonite edges")

    @staticmethod
    def _apply_any_kryptonite_edges(organized_kg: QGOrganizedKnowledgeGraph, full_query_graph: QueryGraph,
                                    encountered_kryptonite_edges_info: Dict[str, Dict[str, Set[str]]], log):
        """
        This function breaks any paths in the KG for which a "not" (exclude=True) condition has been met; the remains
        of the broken paths not used in other paths in the KG are cleaned up during later pruning of dead ends. The
        paths are broken by removing edges (vs. nodes) in order to help ensure that nodes that may also be used in
        valid paths are not accidentally removed from the KG. Optional kryptonite qedges are applied only to the option
        group they belong in; required kryptonite qedges are applied to all.
        """
        for qedge_key, edges in organized_kg.edges_by_qg_id.items():
            current_qedge = full_query_graph.edges[qedge_key]
            current_qedge_qnode_keys = {current_qedge.subject, current_qedge.object}
            # Find kryptonite qedges that share one or more qnodes in common with our current qedge
            linked_kryptonite_qedge_keys = [qe_key for qe_key, qe in full_query_graph.edges.items()
                                            if qe.exclude and {qe.subject, qe.object}.intersection(current_qedge_qnode_keys)]
            # Apply kryptonite edges only to edges within their same group (but apply required ones no matter what)
            linked_kryptonite_qedge_keys_to_apply = [qe_key for qe_key in linked_kryptonite_qedge_keys if
                                                     full_query_graph.edges[qe_key].option_group_id == current_qedge.option_group_id or
                                                     full_query_graph.edges[qe_key].option_group_id is None]
            edge_keys_to_remove = set()
            # Look for paths to blow away based on each (already expanded) kryptonite qedge in the same group
            for kryptonite_qedge_key in linked_kryptonite_qedge_keys_to_apply:
                kryptonite_qedge = full_query_graph.edges[kryptonite_qedge_key]
                if kryptonite_qedge_key in encountered_kryptonite_edges_info:
                    # Mark edges for destruction if they match the kryptonite edge for all qnodes they have in common
                    kryptonite_qedge_qnode_keys = {kryptonite_qedge.subject, kryptonite_qedge.object}
                    qnode_keys_in_common = list(current_qedge_qnode_keys.intersection(kryptonite_qedge_qnode_keys))
                    for edge_key, edge in edges.items():
                        nodes_in_common = []
                        for qnode_key in qnode_keys_in_common:
                            # Figure out whether this qnode_key corresponds to this edge's subject or object
                            other_qnode_key = current_qedge.object if qnode_key == current_qedge.subject else current_qedge.subject
                            if edge.subject in organized_kg.nodes_by_qg_id[qnode_key] and edge.object in organized_kg.nodes_by_qg_id[other_qnode_key]:
                                node_key_to_check = edge.subject
                            else:
                                node_key_to_check = edge.object
                            # Record whether this node was found by the kryptonite expansion
                            if node_key_to_check in encountered_kryptonite_edges_info[kryptonite_qedge_key][qnode_key]:
                                nodes_in_common.append(node_key_to_check)
                        if len(nodes_in_common) == len(qnode_keys_in_common):  # Can only range in size from 0 to 2
                            edge_keys_to_remove.add(edge_key)

            # Actually remove the edges we've marked for destruction
            if edge_keys_to_remove:
                log.debug(f"Blowing away {len(edge_keys_to_remove)} {qedge_key} edges because they lie on a path with a "
                          f"'not' condition met (kryptonite)")
                for edge_key in edge_keys_to_remove:
                    organized_kg.edges_by_qg_id[qedge_key].pop(edge_key)

    @staticmethod
    def _prune_dead_end_paths(organized_kg: QGOrganizedKnowledgeGraph, qg: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        # This function removes any 'dead-end' paths from the KG. (Because edges are expanded one-by-one, not all edges
        # found in the last expansion will connect to edges in the next one)
        log.debug(f"Pruning any paths that are now dead ends (with help of Resultify)")
        expanded_qnodes = {qnode_key for qnode_key in qg.nodes if organized_kg.nodes_by_qg_id.get(qnode_key)}
        expanded_qedges = {qedge_key for qedge_key in qg.edges if organized_kg.edges_by_qg_id.get(qedge_key)}
        qg_expanded_thus_far = QueryGraph(nodes={qnode_key: qg.nodes[qnode_key] for qnode_key in expanded_qnodes},
                                          edges={qedge_key: qg.edges[qedge_key] for qedge_key in expanded_qedges})
        regular_format_kg = eu.convert_qg_organized_kg_to_standard_kg(organized_kg)

        # Use resultify to remove dead ends from our (thus far) KG
        resultifier = ARAXResultify()
        prune_response = ARAXResponse()
        prune_response.envelope = Response()
        prune_response.envelope.message = Message()
        prune_message = prune_response.envelope.message
        prune_message.query_graph = qg_expanded_thus_far
        prune_message.knowledge_graph = regular_format_kg
        resultify_response = resultifier.apply(prune_response, {})
        if resultify_response.status == "OK":
            pruned_organized_kg = eu.convert_standard_kg_to_qg_organized_kg(prune_message.knowledge_graph)
        else:
            pruned_organized_kg = QGOrganizedKnowledgeGraph()
            log.error(f"Ran into an issue trying to prune using Resultify: {prune_response.show()}", error_code="PruneError")

        log.debug(f"After pruning, KG counts are: {eu.get_printable_counts_by_qg_id(organized_kg)}")
        return pruned_organized_kg

    @staticmethod
    def _add_node_connection_to_map(qnode_key_a: str, qnode_key_b: str, edge: Edge,
                                    node_connections_map: Dict[str, Dict[str, Dict[str, Set[str]]]]):
        # This is a helper function that's used when building a map of which nodes are connected to which
        # Example node_connections_map: {'n01': {'UMLS:1222': {'n00': {'DOID:122'}, 'n02': {'UniProtKB:22'}}}, ...}
        # Initiate entries for this edge's nodes as needed
        if edge.subject not in node_connections_map[qnode_key_a]:
            node_connections_map[qnode_key_a][edge.subject] = dict()
        if edge.object not in node_connections_map[qnode_key_b]:
            node_connections_map[qnode_key_b][edge.object] = dict()
        # Initiate empty sets for the qnode keys connected to each of the nodes as needed
        if qnode_key_b not in node_connections_map[qnode_key_a][edge.subject]:
            node_connections_map[qnode_key_a][edge.subject][qnode_key_b] = set()
        if qnode_key_a not in node_connections_map[qnode_key_b][edge.object]:
            node_connections_map[qnode_key_b][edge.object][qnode_key_a] = set()
        # Add each node to the other's connections
        node_connections_map[qnode_key_a][edge.subject][qnode_key_b].add(edge.object)
        node_connections_map[qnode_key_b][edge.object][qnode_key_a].add(edge.subject)

    def _get_order_to_expand_qedges_in(self, query_graph: QueryGraph, log: ARAXResponse) -> List[str]:
        """
        This function determines what order to expand the edges in a query graph in; it aims to start with a required,
        non-kryptonite qedge that has a qnode with a curie specified. It then looks for a qedge connected to that
        starting qedge, and so on.
        """
        qedge_keys_remaining = [qedge_key for qedge_key in query_graph.edges]
        ordered_qedge_keys = []
        while qedge_keys_remaining:
            if not ordered_qedge_keys:
                # Try to start with a required, non-kryptonite qedge that has a qnode with a curie specified
                qedge_keys_with_curie = self._get_qedges_with_curie_qnode(query_graph)
                required_curie_qedge_keys = [qedge_key for qedge_key in qedge_keys_with_curie
                                             if not query_graph.edges[qedge_key].option_group_id]
                non_kryptonite_required_curie_qedge_keys = [qedge_key for qedge_key in required_curie_qedge_keys
                                                            if not query_graph.edges[qedge_key].exclude]
                if non_kryptonite_required_curie_qedge_keys:
                    first_qedge_key = non_kryptonite_required_curie_qedge_keys[0]
                elif required_curie_qedge_keys:
                    first_qedge_key = required_curie_qedge_keys[0]
                elif qedge_keys_with_curie:
                    first_qedge_key = qedge_keys_with_curie[0]
                else:
                    first_qedge_key = qedge_keys_remaining[0]
                ordered_qedge_keys = [first_qedge_key]
                qedge_keys_remaining.remove(first_qedge_key)
            else:
                # Look for a qedge connected to the "subgraph" of qedges we've already added to our ordered list
                connected_qedge_key = self._find_qedge_connected_to_subgraph(ordered_qedge_keys, qedge_keys_remaining, query_graph)
                if connected_qedge_key:
                    ordered_qedge_keys.append(connected_qedge_key)
                    qedge_keys_remaining.remove(connected_qedge_key)
                else:
                    log.error(f"Query graph is disconnected (has more than one component)", error_code="UnsupportedQG")
                    return []
        return ordered_qedge_keys

    @staticmethod
    def _find_qedge_connected_to_subgraph(subgraph_qedge_keys: List[str], qedge_keys_to_choose_from: List[str],
                                          qg: QueryGraph) -> Optional[str]:
        qnode_keys_in_subgraph = {qnode_key for qedge_key in subgraph_qedge_keys for qnode_key in
                                  {qg.edges[qedge_key].subject, qg.edges[qedge_key].object}}
        connected_qedge_keys = [qedge_key for qedge_key in qedge_keys_to_choose_from if
                                qnode_keys_in_subgraph.intersection({qg.edges[qedge_key].subject, qg.edges[qedge_key].object})]
        required_qedge_keys = [qedge_key for qedge_key in connected_qedge_keys if not qg.edges[qedge_key].option_group_id]
        required_kryptonite_qedge_keys = [qedge_key for qedge_key in required_qedge_keys if qg.edges[qedge_key].exclude]
        optional_kryptonite_qedge_keys = [qedge_key for qedge_key in connected_qedge_keys
                                          if qg.edges[qedge_key].option_group_id and qg.edges[qedge_key].exclude]
        if required_kryptonite_qedge_keys:
            return required_kryptonite_qedge_keys[0]
        elif required_qedge_keys:
            return required_qedge_keys[0]
        elif optional_kryptonite_qedge_keys:
            return optional_kryptonite_qedge_keys[0]
        elif connected_qedge_keys:
            return connected_qedge_keys[0]
        else:
            return None

    def _is_input_qnode(self, qnode_key: str, qedge_key: str, qg: QueryGraph, log: ARAXResponse) -> bool:
        all_ordered_qedge_keys = self._get_order_to_expand_qedges_in(qg, log)
        current_qedge_index = all_ordered_qedge_keys.index(qedge_key)
        previous_qedge_key = all_ordered_qedge_keys[current_qedge_index - 1] if current_qedge_index > 0 else None
        if previous_qedge_key and qnode_key in {qg.edges[previous_qedge_key].subject,
                                                qg.edges[previous_qedge_key].object}:
            return True
        else:
            return False

    @staticmethod
    def _remove_self_edges(kg: QGOrganizedKnowledgeGraph, kp_name: str, qedge_key: str, qedge: QEdge, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        log.debug(f"{kp_name}: Removing any self-edges from the answer KG")
        # Remove any self-edges (subject is same as object)
        edges_to_remove = []
        for edge_key, edge in kg.edges_by_qg_id[qedge_key].items():
            if edge.subject == edge.object:
                edges_to_remove.append(edge_key)
        for edge_key in edges_to_remove:
            del kg.edges_by_qg_id[qedge_key][edge_key]

        # Remove any nodes that may have been orphaned as a result of removing self-edges
        if edges_to_remove:
            node_keys_used_by_remaining_edges = {node_key for edge in kg.edges_by_qg_id[qedge_key].values()
                                                 for node_key in {edge.subject, edge.object}}
            all_node_keys = set(kg.nodes_by_qg_id[qedge.subject]).union(set(kg.nodes_by_qg_id[qedge.object]))
            orphaned_node_keys = all_node_keys.difference(node_keys_used_by_remaining_edges)
            for node_key in orphaned_node_keys:
                kg.nodes_by_qg_id[qedge.subject].pop(node_key, None)
                kg.nodes_by_qg_id[qedge.object].pop(node_key, None)

        log.debug(f"{kp_name}: After removing self-edges, answer KG counts are: {eu.get_printable_counts_by_qg_id(kg)}")
        return kg

    def _set_and_validate_parameters(self, kp: Optional[str], input_parameters: Dict[str, any], log: ARAXResponse) -> Dict[str, any]:
        parameters = {"kp": kp}
        if not kp:
            kp = "RTX-KG2"  # We'll use a standard set of parameters (like for KG2)
        for kp_parameter_name, info_dict in self.kp_command_definitions[kp]["parameters"].items():
            if info_dict["type"] == "boolean":
                parameters[kp_parameter_name] = self._convert_bool_string_to_bool(info_dict.get("default", ""))
            else:
                parameters[kp_parameter_name] = info_dict.get("default", None)

        # Override default values for any parameters passed in
        parameter_names_for_all_kps = {param for kp_documentation in self.kp_command_definitions.values() for param in
                                       kp_documentation["parameters"]}
        for param_name, value in input_parameters.items():
            if param_name and param_name not in parameters:
                kp_specific_message = f"when kp={kp}" if param_name in parameter_names_for_all_kps else "for Expand"
                log.error(f"Supplied parameter {param_name} is not permitted {kp_specific_message}",
                          error_code="InvalidParameter")
            else:
                parameters[param_name] = self._convert_bool_string_to_bool(value) if isinstance(value, str) else value

        return parameters

    @staticmethod
    def _override_node_categories(kg: KnowledgeGraph, qg: QueryGraph):
        # This method overrides KG nodes' types to match those requested in the QG, where possible (issue #987)
        for node in kg.nodes.values():
            corresponding_qnode_categories = {category for qnode_key in node.qnode_keys for category in
                                              eu.convert_to_list(qg.nodes[qnode_key].categories)}
            if corresponding_qnode_categories:
                node.categories = list(corresponding_qnode_categories)

    @staticmethod
    def _get_orphan_qnode_keys(query_graph: QueryGraph):
        qnode_keys_used_by_qedges = {qnode_key for qedge in query_graph.edges.values() for qnode_key in {qedge.subject, qedge.object}}
        all_qnode_keys = set(query_graph.nodes)
        return list(all_qnode_keys.difference(qnode_keys_used_by_qedges))

    @staticmethod
    def _get_qedges_with_curie_qnode(query_graph: QueryGraph) -> List[str]:
        return [qedge_key for qedge_key, qedge in query_graph.edges.items()
                if query_graph.nodes[qedge.subject].ids or query_graph.nodes[qedge.object].ids]

    @staticmethod
    def _find_connected_qedge(qedge_choices: List[QEdge], qedge: QEdge) -> QEdge:
        qedge_qnode_keys = {qedge.subject, qedge.object}
        connected_qedges = []
        for other_qedge in qedge_choices:
            other_qedge_qnode_keys = {other_qedge.subject, other_qedge.object}
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
    def _get_qnode_curie_summary(qnode: QNode) -> str:
        num_curies = len(qnode.ids) if qnode.ids else 0
        if num_curies == 1:
            return f" {qnode.ids}"
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
        "add_qnode(key=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
        "add_qnode(key=n01, category=protein, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=BTE)",
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
