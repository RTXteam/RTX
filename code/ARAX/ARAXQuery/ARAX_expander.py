#!/bin/env python3
import asyncio
import copy
import logging
import multiprocessing
import pickle
import sys
import os
import time
import traceback
from collections import defaultdict
from typing import List, Dict, Tuple, Union, Set, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_decorator import ARAXDecorator
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../BiolinkHelper/")
from biolink_helper import BiolinkHelper
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
from openapi_server.models.query_constraint import QueryConstraint


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


def trim_to_size(input_list, length):
    if input_list is None:
        return None
    if len(input_list) > length+1:
        n_more = len(input_list) - length
        output_list = input_list[:length]
        output_list.append(f"+{n_more}")
        return output_list
    else:
        return input_list


class ARAXExpander:

    def __init__(self):
        self.logger = logging.getLogger('log')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.dirname(os.path.abspath(__file__)) + "/Expand/expand.log")
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.kp_command_definitions = eu.get_kp_command_definitions()
        self.bh = BiolinkHelper()
        # Keep record of which constraints we support (format is: {constraint_id: {value: {operators}}})
        self.supported_qnode_constraints = {"biolink:highest_FDA_approval_status": {"regular approval": {"=="}}}
        self.supported_qedge_constraints = dict()

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        considered_kps = sorted(list(set(self.kp_command_definitions)))
        kp_less = {
                "dsl_command": "expand()",
                "description": f"This command will expand (aka, answer/fill) your query graph in an edge-by-edge "
                               f"fashion, intelligently selecting which KPs to use for each edge. Candidate KPs are: "
                               f"{', '.join(considered_kps)}. It selects KPs based on the meta information provided by "
                               f"their TRAPI APIs (when available) as well as a few heuristics aimed to ensure quick "
                               f"but useful answers. For each QEdge, it queries the selected KPs in parallel; it will "
                               f"timeout for a particular KP if it decides it's taking too long to respond.",
                "parameters": eu.get_standard_parameters()
            }
        return [kp_less] + list(self.kp_command_definitions.values())

    def apply(self, response, input_parameters, mode: str = "ARAX", user_timeout: Optional[int] = None):
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
        query_graph = copy.deepcopy(message.query_graph)

        # Verify we understand all constraints
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.constraints:
                for constraint in qnode.constraints:
                    if not self.is_supported_constraint(constraint, self.supported_qnode_constraints):
                        log.error(f"Unsupported constraint(s) detected on qnode {qnode_key}: \n{constraint}\n"
                                  f"Don't know how to handle! Supported qnode constraints are: "
                                  f"{self.supported_qnode_constraints}", error_code="UnsupportedConstraint")
        for qedge_key, qedge in query_graph.edges.items():
            if qedge.constraints:
                for constraint in qedge.constraints:
                    if not self.is_supported_constraint(constraint, self.supported_qedge_constraints):
                        log.error(f"Unsupported constraint(s) detected on qedge {qedge_key}: \n{constraint}\n"
                                  f"Don't know how to handle! Supported qedge constraints are: "
                                  f"{self.supported_qedge_constraints}", error_code="UnsupportedConstraint")

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

        # Add in any category equivalencies to the QG (e.g., protein == gene, since KPs handle these differently)
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.ids and not qnode.categories:
                # Infer categories for expand's internal use (in KP selection and etc.)
                qnode.categories = eu.get_preferred_categories(qnode.ids, log)
                log.debug(f"Inferred category for qnode {qnode_key} is {qnode.categories}")
            elif not qnode.categories:
                # Default to NamedThing if no category was specified
                qnode.categories = [self.bh.get_root_category()]
            qnode.categories = self.bh.add_conflations(qnode.categories)
        # Make sure QG only uses canonical predicates
        if mode == "ARAX":
            log.debug(f"Making sure QG only uses canonical predicates")
            qedge_keys = set(query_graph.edges)
            for qedge_key in qedge_keys:
                qedge = query_graph.edges[qedge_key]
                if qedge.predicates:
                    # Convert predicates to their canonical form as needed/possible
                    qedge_predicates = set(qedge.predicates)
                    symmetric_predicates = {predicate for predicate in qedge_predicates
                                            if self.bh.is_symmetric(predicate)}
                    asymmetric_predicates = qedge_predicates.difference(symmetric_predicates)
                    canonical_predicates = set(self.bh.get_canonical_predicates(qedge.predicates))
                    if canonical_predicates != qedge_predicates:
                        asymmetric_non_canonical = asymmetric_predicates.difference(canonical_predicates)
                        asymmetric_canonical = asymmetric_predicates.intersection(canonical_predicates)
                        symmetric_non_canonical = symmetric_predicates.difference(canonical_predicates)
                        if symmetric_non_canonical:
                            # Switch to canonical predicates, but no need to flip the qedge since they're symmetric
                            log.debug(f"Converting symmetric predicates {symmetric_non_canonical} on {qedge_key} to "
                                      f"their canonical forms.")
                            converted_symmetric = self.bh.get_canonical_predicates(symmetric_non_canonical)
                            qedge.predicates = list(qedge_predicates.difference(symmetric_non_canonical).union(converted_symmetric))
                        if asymmetric_non_canonical and asymmetric_canonical:
                            log.error(f"Qedge {qedge_key} has asymmetric predicates in both canonical and non-canonical"
                                      f" forms, which isn't allowed. Non-canonical asymmetric predicates are: "
                                      f"{asymmetric_non_canonical}", error_code="InvalidPredicates")
                        elif asymmetric_non_canonical:
                            # Flip the qedge in this case (OK to do since only other predicates are symmetric)
                            log.debug(f"Converting {qedge_key}'s asymmetric non-canonical predicates to canonical "
                                      f"form; requires flipping the qedge, but this is OK since there are no "
                                      f"asymmetric canonical predicates on this qedge.")
                            converted_asymmetric = self.bh.get_canonical_predicates(asymmetric_non_canonical)
                            final_predicates = set(qedge.predicates).difference(asymmetric_non_canonical).union(converted_asymmetric)
                            eu.flip_qedge(qedge, list(final_predicates))
                    # Handle special situation where user entered treats edge in wrong direction
                    if qedge.predicates == ["biolink:treats"]:
                        subject_qnode = query_graph.nodes[qedge.subject]
                        if "biolink:Disease" in self.bh.get_descendants(subject_qnode.categories):
                            log.warning(f"{qedge_key} seems to be pointing in the wrong direction (you have "
                                        f"(disease-like node)-[treats]->(something)). Will flip this qedge.")
                            eu.flip_qedge(qedge, qedge.predicates)
                else:
                    # Default to related_to if no predicate was specified
                    qedge.predicates = [self.bh.get_root_predicate()]

        # Expand any specified edges
        if input_qedge_keys:
            query_sub_graph = self._extract_query_subgraph(input_qedge_keys, query_graph, log)
            if log.status != 'OK':
                return response
            log.debug(f"Query graph for this Expand() call is: {query_sub_graph.to_dict()}")

            ordered_qedge_keys_to_expand = self._get_order_to_expand_qedges_in(query_sub_graph, log)

            # Pre-populate the query plan with an entry for each qedge that will be expanded in this Expand() call
            all_kps = set(self.kp_command_definitions)
            for qedge_key in ordered_qedge_keys_to_expand:
                qedge = query_sub_graph.edges[qedge_key]
                response.update_query_plan(qedge_key, 'edge_properties', 'status', 'Waiting')
                subject_qnode = query_sub_graph.nodes[qedge.subject]
                object_qnode = query_sub_graph.nodes[qedge.object]
                subject_details = subject_qnode.ids if subject_qnode.ids else subject_qnode.categories
                object_details = object_qnode.ids if object_qnode.ids else object_qnode.categories
                subject_details = trim_to_size(subject_details, 5)
                object_details = trim_to_size(object_details, 5)
                predicate_details = trim_to_size(qedge.predicates, 5)
                response.update_query_plan(qedge_key, 'edge_properties', 'subject', subject_details)
                response.update_query_plan(qedge_key, 'edge_properties', 'object', object_details)
                response.update_query_plan(qedge_key, 'edge_properties', 'predicate', predicate_details)
                for kp in all_kps:
                    response.update_query_plan(qedge_key, kp, 'Waiting', 'Waiting for previous expansion step')

            # Expand the query graph edge-by-edge
            for qedge_key in ordered_qedge_keys_to_expand:
                log.debug(f"Expanding qedge {qedge_key}")
                response.update_query_plan(qedge_key, 'edge_properties', 'status', 'Expanding')
                qedge = query_graph.edges[qedge_key]
                # Create a query graph for this edge (that uses curies found in prior steps)
                one_hop_qg = self._get_query_graph_for_edge(qedge_key, query_graph, overarching_kg, log)

                # Figure out the prune threshold (use what user provided or otherwise do something intelligent)
                if parameters.get("prune_threshold"):
                    pre_prune_threshold = parameters["prune_threshold"]
                else:
                    pre_prune_threshold = self._get_prune_threshold(one_hop_qg)
                # Prune back any nodes with more than the specified max of answers
                if mode == "ARAX":
                    log.debug(f"For {qedge_key}, pre-prune threshold is {pre_prune_threshold}")
                    fulfilled_qnode_keys = set(one_hop_qg.nodes).intersection(set(overarching_kg.nodes_by_qg_id))
                    for qnode_key in fulfilled_qnode_keys:
                        num_kg_nodes = len(overarching_kg.nodes_by_qg_id[qnode_key])
                        if num_kg_nodes > pre_prune_threshold:
                            overarching_kg = self._prune_kg(qnode_key, pre_prune_threshold, overarching_kg, query_graph, log)
                            # Re-formulate the QG for this edge now that the KG has been slimmed down
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
                    all_kps = set(self.kp_command_definitions)
                    for kp in all_kps.difference(kps_to_query):
                        skipped_message = f"Expand was told to use {', '.join(kps_to_query)}"
                        response.update_query_plan(qedge_key, kp, "Skipped", skipped_message)
                kps_to_query = list(kps_to_query)

                use_asyncio = True  # Flip this to False if you want to use multiprocessing instead

                # Use a non-concurrent method to expand with KG2 when bypassing the KG2 API
                if kps_to_query == ["RTX-KG2"] and mode == "RTXKG2":
                    kp_answers = [self._expand_edge_kg2_local(one_hop_qg, log)]
                # Otherwise concurrently send this query to each KP selected to answer it
                elif kps_to_query:
                    kp_selector = KPSelector(log)
                    if use_asyncio:
                        kps_to_query = eu.sort_kps_for_asyncio(kps_to_query, log)
                        log.debug(f"Will use asyncio to run KP queries concurrently")
                        loop = asyncio.new_event_loop()  # Need to create NEW event loop for threaded environments
                        asyncio.set_event_loop(loop)
                        tasks = [self._expand_edge_async(one_hop_qg, kp_to_use, input_parameters, user_specified_kp,
                                                         user_timeout, force_local, kp_selector, log, multiple_kps=True)
                                 for kp_to_use in kps_to_query]
                        task_group = asyncio.gather(*tasks)
                        kp_answers = loop.run_until_complete(task_group)
                        loop.close()
                    else:
                        # Use multiprocessing (which forks behind the scenes) TODO: Delete once fully commit to asyncio
                        log.debug(f"Will use multiprocessing to run KP queries in parallel")
                        for kp in kps_to_query:
                            num_input_curies = max([len(eu.convert_to_list(qnode.ids)) for qnode in one_hop_qg.nodes.values()])
                            waiting_message = f"Query with {num_input_curies} curies sent: waiting for response"
                            response.update_query_plan(qedge_key, kp, "Waiting", waiting_message)
                        log.debug(f"Waiting for all KP processes to finish..")
                        empty_log = ARAXResponse()  # We'll have to merge processes' logs together afterwards
                        self.logger.info(f"PID {os.getpid()}: BEFORE pool: About to create {len(kps_to_query)} child processes from {multiprocessing.current_process()}")
                        with multiprocessing.Pool(len(kps_to_query)) as pool:
                            kp_answers = pool.starmap(self._expand_edge, [[one_hop_qg, kp_to_use, input_parameters,
                                                                           user_specified_kp, user_timeout, force_local,
                                                                           kp_selector, empty_log, True]
                                                                          for kp_to_use in kps_to_query])
                        self.logger.info(f"PID {os.getpid()}: AFTER pool: Pool of {len(kps_to_query)} processes is done, back in {multiprocessing.current_process()}")
                        # Merge the processes' individual logs and update the query plan
                        for index, response_tuple in enumerate(kp_answers):
                            kp = kps_to_query[index]
                            answer_kg = response_tuple[0]
                            kp_log = response_tuple[1]
                            wait_time = kp_log.wait_time if hasattr(kp_log, "wait_time") else "unknown"
                            # Update the query plan with KPs' results
                            if kp_log.status == 'OK':
                                if hasattr(kp_log, "timed_out"):
                                    timeout_message = f"Query timed out after {kp_log.timed_out} seconds"
                                    response.update_query_plan(qedge_key, kp, "Timed out", timeout_message)
                                elif hasattr(kp_log, "http_error"):
                                    error_message = f"Returned error {kp_log.http_error} after {wait_time} seconds"
                                    response.update_query_plan(qedge_key, kp, "Error", error_message)
                                else:
                                    done_message = f"Query returned {len(answer_kg.edges_by_qg_id.get(qedge_key, dict()))} " \
                                                   f"edges in {wait_time} seconds"
                                    response.update_query_plan(qedge_key, kp, "Done", done_message)
                            else:
                                response.update_query_plan(qedge_key, kp, "Error",
                                                           f"Process returned error {kp_log.status}")
                            # Merge KP logs as needed, since processes can't share the main log
                            if len(kps_to_query) > 1 and kp_log.status != 'OK':
                                kp_log.status = 'OK'  # We don't want to halt just because one KP reported an error #1500
                            log.merge(kp_log)
                            if response.status != 'OK':
                                return response
                else:
                    log.error(f"Expand could not find any KPs to answer {qedge_key} with.", error_code="NoResults")
                    return response

                # Merge KPs' answers into our overarching KG
                log.debug(f"Got answers from all KPs; merging them into one KG")
                for index, response_tuple in enumerate(kp_answers):
                    answer_kg = response_tuple[0]
                    # Store any kryptonite edge answers as needed
                    if mode == "ARAX" and qedge.exclude and not answer_kg.is_empty():
                        self._store_kryptonite_edge_info(answer_kg, qedge_key, message.query_graph,
                                                         message.encountered_kryptonite_edges_info, response)
                    # Otherwise just merge the answer into the overarching KG
                    else:
                        self._merge_answer_into_message_kg(answer_kg, overarching_kg, message.query_graph, mode, response)
                    if response.status != 'OK':
                        return response
                log.debug(f"After merging KPs' answers, total KG counts are: {eu.get_printable_counts_by_qg_id(overarching_kg)}")

                # Handle any constraints for this qedge and/or its qnodes (that require post-filtering)
                qnode_keys = {qedge.subject, qedge.object}
                qnode_keys_with_answers = qnode_keys.intersection(set(overarching_kg.nodes_by_qg_id))
                for qnode_key in qnode_keys_with_answers:
                    qnode = query_graph.nodes[qnode_key]
                    if qnode.constraints:
                        for constraint in qnode.constraints:
                            if constraint.id == "biolink:highest_FDA_approval_status" and constraint.operator == "==" and constraint.value == "regular approval":
                                log.info(f"Applying qnode {qnode_key} constraint: {'NOT ' if constraint._not else ''}"
                                         f"biolink:highest_FDA_approval_status == regular approval")
                                fda_approved_drug_ids = self._load_fda_approved_drug_ids()
                                answer_node_ids = set(overarching_kg.nodes_by_qg_id[qnode_key])
                                if constraint._not:
                                    nodes_to_remove = answer_node_ids.intersection(fda_approved_drug_ids)
                                else:
                                    nodes_to_remove = answer_node_ids.difference(fda_approved_drug_ids)
                                log.debug(f"Removing {len(nodes_to_remove)} nodes fulfilling {qnode_key} for FDA "
                                          f"approval constraint ({round((len(nodes_to_remove) / len(answer_node_ids)) * 100)}%)")
                                overarching_kg.remove_nodes(nodes_to_remove, qnode_key, query_graph)

                if mode == "ARAX":
                    # Apply any kryptonite ("not") qedges
                    self._apply_any_kryptonite_edges(overarching_kg, message.query_graph,
                                                     message.encountered_kryptonite_edges_info, response)
                    # Remove any paths that are now dead-ends
                    overarching_kg = self._remove_dead_end_paths(query_graph, overarching_kg, response)
                    if response.status != 'OK':
                        return response

                # Declare that we are done expanding this qedge
                response.update_query_plan(qedge_key, 'edge_properties', 'status', 'Done')

                # Make sure we found at least SOME answers for this edge
                if not eu.qg_is_fulfilled(one_hop_qg, overarching_kg) and not qedge.exclude and not qedge.option_group_id:
                    log.warning(f"No paths were found in {kps_to_query} satisfying qedge {qedge_key}")
                    return response

        # Expand any specified nodes
        if input_qnode_keys:
            kp_to_use = parameters["kp"] if user_specified_kp else "RTX-KG2"  # Only KG2 does single-node queries
            for qnode_key in input_qnode_keys:
                answer_kg = self._expand_node(qnode_key, kp_to_use, query_graph, mode, user_specified_kp, user_timeout,
                                              force_local, log)
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
            decorator.decorate_nodes(response)
            decorator.decorate_edges(response, kind="RTX-KG2")

        # Map canonical curies back to the input curies in the QG (where applicable) #1622
        self._map_back_to_input_curies(message.knowledge_graph, query_graph, log)

        # Return the response and done
        kg = message.knowledge_graph
        log.info(f"After Expand, the KG has {len(kg.nodes)} nodes and {len(kg.edges)} edges "
                 f"({eu.get_printable_counts_by_qg_id(overarching_kg)})")

        return response

    async def _expand_edge_async(self, edge_qg: QueryGraph, kp_to_use: str, input_parameters: Dict[str, any],
                                 user_specified_kp: bool, user_timeout: Optional[int], force_local: bool,
                                 kp_selector: KPSelector, log: ARAXResponse, multiple_kps: bool = False) -> Tuple[QGOrganizedKnowledgeGraph, ARAXResponse]:
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
        try:
            use_custom_querier = kp_to_use in {'DTD', 'NGD'}
            if use_custom_querier:
                num_input_curies = max([len(eu.convert_to_list(qnode.ids)) for qnode in edge_qg.nodes.values()])
                waiting_message = f"Query with {num_input_curies} curies sent: waiting for response"
                log.update_query_plan(qedge_key, kp_to_use, "Waiting", waiting_message)
                start = time.time()
                if kp_to_use == 'DTD':
                    from Expand.DTD_querier import DTDQuerier
                    kp_querier = DTDQuerier(log)
                else:
                    from Expand.ngd_querier import NGDQuerier
                    kp_querier = NGDQuerier(log)
                answer_kg = kp_querier.answer_one_hop_query(edge_qg)
                wait_time = round(time.time() - start)
                if log.status == 'OK':
                    done_message = f"Returned {len(answer_kg.edges_by_qg_id.get(qedge_key, dict()))} edges in {wait_time} seconds"
                    log.update_query_plan(qedge_key, kp_to_use, "Done", done_message)
                else:
                    log.update_query_plan(qedge_key, kp_to_use, "Error", f"Process error-ed out with {log.status} after {wait_time} seconds")
                    return answer_kg, log
            else:
                # This is a general purpose querier for use with any KPs that we query via their TRAPI API
                from Expand.trapi_querier import TRAPIQuerier
                kp_querier = TRAPIQuerier(response_object=log,
                                          kp_name=kp_to_use,
                                          user_specified_kp=user_specified_kp,
                                          user_timeout=user_timeout,
                                          kp_selector=kp_selector,
                                          force_local=force_local)
                answer_kg = await kp_querier.answer_one_hop_query_async(edge_qg)
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            if user_specified_kp:
                log.error(f"An uncaught error was thrown while trying to Expand using {kp_to_use}. Error was: {tb}",
                          error_code=f"UncaughtError")
            else:
                log.warning(f"An uncaught error was thrown while trying to Expand using {kp_to_use}, so I couldn't "
                            f"get answers from that KP. Error was: {tb}")
            log.update_query_plan(qedge_key, kp_to_use, "Error", f"Process error-ed out with {log.status}")
            return QGOrganizedKnowledgeGraph(), log

        if log.status != 'OK':
            if multiple_kps:
                log.status = 'OK'  # We don't want to halt just because one KP reported an error #1500
            return answer_kg, log

        log.info(f"{kp_to_use}: Query for edge {qedge_key} completed ({eu.get_printable_counts_by_qg_id(answer_kg)})")

        # Do some post-processing (deduplicate nodes, remove self-edges..)
        if kp_to_use != 'RTX-KG2':  # KG2c is already deduplicated and uses canonical predicates
            answer_kg = eu.check_for_canonical_predicates(answer_kg, kp_to_use, log)
            answer_kg = self._deduplicate_nodes(answer_kg, kp_to_use, log)
        if eu.qg_is_fulfilled(edge_qg, answer_kg):
            answer_kg = self._remove_self_edges(answer_kg, kp_to_use, qedge_key, qedge, log)

        return answer_kg, log

    def _expand_edge_kg2_local(self, one_hop_qg: QueryGraph, log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, ARAXResponse]:
        qedge_key = next(qedge_key for qedge_key in one_hop_qg.edges)
        qedge = one_hop_qg.edges[qedge_key]
        log.debug(f"Expanding {qedge_key} by querying Plover directly")
        answer_kg = QGOrganizedKnowledgeGraph()

        from Expand.kg2_querier import KG2Querier
        kg2_querier = KG2Querier(log)
        try:
            answer_kg = kg2_querier.answer_one_hop_query(one_hop_qg)
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"An uncaught error was thrown while trying to Expand using RTX-KG2 (local). Error was: {tb}",
                      error_code=f"UncaughtError")

        if log.status != 'OK':
            return answer_kg, log

        if eu.qg_is_fulfilled(one_hop_qg, answer_kg):
            answer_kg = self._remove_self_edges(answer_kg, "RTX-KG2", qedge_key, qedge, log)

        return answer_kg, log

    def _expand_edge(self, edge_qg: QueryGraph, kp_to_use: str, input_parameters: Dict[str, any],
                     user_specified_kp: bool, user_timeout: Optional[int], force_local: bool, kp_selector: KPSelector,
                     log: ARAXResponse, multiprocessed: bool = False) -> Tuple[QGOrganizedKnowledgeGraph, ARAXResponse]:
        # TODO: Delete this method once we're ready to let go of the multiprocessing (vs. asyncio) option
        if multiprocessed:
            self.logger.info(f"PID {os.getpid()}: {kp_to_use}: Entered child process {multiprocessing.current_process()}")
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
        try:
            if kp_to_use == 'DTD':
                from Expand.DTD_querier import DTDQuerier
                kp_querier = DTDQuerier(log)
            elif kp_to_use == 'NGD':
                from Expand.ngd_querier import NGDQuerier
                kp_querier = NGDQuerier(log)
            else:
                # This is a general purpose querier for use with any KPs that we query via their TRAPI 1.0+ API
                from Expand.trapi_querier import TRAPIQuerier
                kp_querier = TRAPIQuerier(response_object=log,
                                          kp_name=kp_to_use,
                                          user_specified_kp=user_specified_kp,
                                          user_timeout=user_timeout,
                                          kp_selector=kp_selector,
                                          force_local=force_local)
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
            if multiprocessed:
                self.logger.info(f"PID {os.getpid()}: {kp_to_use}: Exiting child process {multiprocessing.current_process()} (it errored out)")
            return QGOrganizedKnowledgeGraph(), log

        if log.status != 'OK':
            if multiprocessed:
                self.logger.info(f"PID {os.getpid()}: {kp_to_use}: Exiting child process {multiprocessing.current_process()} (it errored out)")
            return answer_kg, log

        log.info(f"{kp_to_use}: Query for edge {qedge_key} completed ({eu.get_printable_counts_by_qg_id(answer_kg)})")

        # Do some post-processing (deduplicate nodes, remove self-edges..)
        if kp_to_use != 'RTX-KG2':  # KG2c is already deduplicated and uses canonical predicates
            answer_kg = eu.check_for_canonical_predicates(answer_kg, kp_to_use, log)
            answer_kg = self._deduplicate_nodes(answer_kg, kp_to_use, log)
        if eu.qg_is_fulfilled(edge_qg, answer_kg):
            answer_kg = self._remove_self_edges(answer_kg, kp_to_use, qedge_key, qedge, log)

        if multiprocessed:
            self.logger.info(f"PID {os.getpid()}: {kp_to_use}: Exiting child process {multiprocessing.current_process()}")
        return answer_kg, log

    def _expand_node(self, qnode_key: str, kp_to_use: str, query_graph: QueryGraph, mode: str,
                     user_specified_kp: bool, user_timeout: Optional[int], force_local: bool, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
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
                kp_querier = TRAPIQuerier(response_object=log,
                                          kp_name=kp_to_use,
                                          user_specified_kp=user_specified_kp,
                                          user_timeout=user_timeout,
                                          force_local=force_local)
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
        edge_qg.edges[qedge_key] = copy.deepcopy(qedge)

        # Update this qedge's qnodes as appropriate and add (copies of) them to the edge query graph
        required_qedge_keys = {qe_key for qe_key, qe in full_qg.edges.items() if not qe.option_group_id}
        expanded_qedge_keys = set(overarching_kg.edges_by_qg_id)
        qedge_has_already_been_expanded = qedge_key in expanded_qedge_keys
        qedge_is_required = qedge_key in required_qedge_keys
        for qnode_key in qnode_keys:
            qnode = full_qg.nodes[qnode_key]
            qnode_copy = copy.deepcopy(qnode)
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
            qedge_copy = copy.deepcopy(qedge)
            if qedge_key not in sub_query_graph.edges:
                sub_query_graph.edges[qedge_key] = qedge_copy
            for qnode_key in [qedge_copy.subject, qedge_copy.object]:
                qnode_copy = copy.deepcopy(query_graph.nodes[qnode_key])
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
            num_orphan_edges_removed = 0
            qedge = overarching_qg.edges[qedge_key]
            for edge_key, edge in edges_dict.items():
                if (edge.subject in overarching_kg.nodes_by_qg_id[qedge.subject] and
                    edge.object in overarching_kg.nodes_by_qg_id[qedge.object]) or \
                        (edge.subject in overarching_kg.nodes_by_qg_id[qedge.object] and
                         edge.object in overarching_kg.nodes_by_qg_id[qedge.subject]):
                    overarching_kg.add_edge(edge_key, edge, qedge_key)
                else:
                    num_orphan_edges_removed += 1
            log.debug(f"Removed {num_orphan_edges_removed} edges fulfilling {qedge_key} from the KG because they were orphaned")

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
    def _prune_kg(qnode_key_to_prune: str, prune_threshold: int, kg: QGOrganizedKnowledgeGraph,
                  qg: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        log.info(f"Pruning back {qnode_key_to_prune} nodes because there are more than {prune_threshold}")
        kg_copy = copy.deepcopy(kg)
        qg_expanded_thus_far = eu.get_qg_expanded_thus_far(qg, kg)
        qg_expanded_thus_far.nodes[qnode_key_to_prune].is_set = False  # Necessary for assessment of answer quality
        num_edges_in_kg = sum([len(edges) for edges in kg.edges_by_qg_id.values()])
        overlay_fet = True if num_edges_in_kg < 100000 else False
        # Use fisher exact test and the ranker to prune down answers for this qnode
        intermediate_results_response = eu.create_results(qg_expanded_thus_far, kg_copy, log,
                                                          rank_results=True, overlay_fet=overlay_fet,
                                                          qnode_key_to_prune=qnode_key_to_prune)
        log.debug(f"A total of {len(intermediate_results_response.envelope.message.results)} "
                  f"intermediate results were created/ranked")
        if intermediate_results_response.status == "OK":
            # Filter down so we only keep the top X nodes
            results = intermediate_results_response.envelope.message.results
            results.sort(key=lambda x: x.score, reverse=True)
            kept_nodes = set()
            scores = []
            counter = 0
            while len(kept_nodes) < prune_threshold and counter < len(results):
                current_result = intermediate_results_response.envelope.message.results[counter]
                scores.append(current_result.score)
                kept_nodes.update({binding.id for binding in current_result.node_bindings[qnode_key_to_prune]})
                counter += 1
            log.info(f"Kept top {len(kept_nodes)} answers for {qnode_key_to_prune}. "
                     f"Best score was {round(max(scores), 5)}, worst kept was {round(min(scores), 5)}.")
            # Actually eliminate them from the KG

            nodes_to_delete = set(kg.nodes_by_qg_id[qnode_key_to_prune]).difference(kept_nodes)
            kg.remove_nodes(nodes_to_delete, qnode_key_to_prune, qg_expanded_thus_far)
        else:
            log.error(f"Ran into an issue using Resultify when trying to prune {qnode_key_to_prune} answers: "
                      f"{intermediate_results_response.show()}", error_code="PruneError")

        log.debug(f"After pruning {qnode_key_to_prune} nodes, KG counts are: {eu.get_printable_counts_by_qg_id(kg)}")
        return kg

    @staticmethod
    def _remove_dead_end_paths(full_qg: QueryGraph, kg: QGOrganizedKnowledgeGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        """
        This function removes any 'dead-end' paths from the KG. (Because edges are expanded one-by-one, not all edges
        found in the last expansion will connect to edges in the next one)
        """
        log.debug(f"Pruning any paths that are now dead ends (with help of Resultify)")
        qg_expanded_thus_far = eu.get_qg_expanded_thus_far(full_qg, kg)
        for qnode in qg_expanded_thus_far.nodes.values():
            qnode.is_set = True  # This makes resultify run faster and doesn't hurt in this case
        resultify_response = eu.create_results(qg_expanded_thus_far, kg, log)
        if resultify_response.status == "OK":
            pruned_kg = eu.convert_standard_kg_to_qg_organized_kg(resultify_response.envelope.message.knowledge_graph)
        else:
            pruned_kg = QGOrganizedKnowledgeGraph()
            log.error(f"Ran into an issue trying to prune using Resultify: {resultify_response.show()}",
                      error_code="PruneError")
        log.debug(f"After removing dead-end paths, KG counts are: {eu.get_printable_counts_by_qg_id(pruned_kg)}")
        return pruned_kg

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

        # First set parameters to their defaults
        for kp_parameter_name, info_dict in self.kp_command_definitions[kp]["parameters"].items():
            if info_dict["type"] == "boolean":
                parameters[kp_parameter_name] = self._convert_bool_string_to_bool(info_dict.get("default", ""))
            else:
                parameters[kp_parameter_name] = info_dict.get("default", None)

        # Then override default values for any parameters passed in
        parameter_names_for_all_kps = {param for kp_documentation in self.kp_command_definitions.values() for param in
                                       kp_documentation["parameters"]}
        for param_name, value in input_parameters.items():
            if param_name and param_name not in parameters:
                kp_specific_message = f"when kp={kp}" if param_name in parameter_names_for_all_kps else "for Expand"
                log.error(f"Supplied parameter {param_name} is not permitted {kp_specific_message}",
                          error_code="InvalidParameter")
            elif param_name in self.kp_command_definitions[kp]["parameters"]:
                param_info_dict = self.kp_command_definitions[kp]["parameters"][param_name]
                if param_info_dict.get("type") == "boolean":
                    parameters[param_name] = self._convert_bool_string_to_bool(value) if isinstance(value, str) else value
                elif param_info_dict.get("type") == "integer":
                    parameters[param_name] = int(value)
                else:
                    parameters[param_name] = value

        return parameters

    @staticmethod
    def is_supported_constraint(constraint: QueryConstraint, supported_constraints_map: Dict[str, Dict[str, Set[str]]]) -> bool:
        if constraint.id not in supported_constraints_map:
            return False
        elif constraint.value not in supported_constraints_map[constraint.id]:
            return False
        elif constraint.operator not in supported_constraints_map[constraint.id][constraint.value]:
            return False
        else:
            return True

    @staticmethod
    def _load_fda_approved_drug_ids() -> Set[str]:
        # Determine the local path to the FDA-approved drugs pickle
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        pickle_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources'])
        pickle_name = rtxc.fda_approved_drugs_path.split('/')[-1]
        pickle_file_path = f"{pickle_dir_path}{os.path.sep}{pickle_name}"
        # Load the pickle's data
        with open(pickle_file_path, "rb") as fda_pickle:
            fda_approved_drug_ids = pickle.load(fda_pickle)
        return fda_approved_drug_ids

    @staticmethod
    def _override_node_categories(kg: KnowledgeGraph, qg: QueryGraph):
        # This method overrides KG nodes' types to match those requested in the QG, where possible (issue #987)
        for node in kg.nodes.values():
            corresponding_qnode_categories = {category for qnode_key in node.qnode_keys for category in
                                              eu.convert_to_list(qg.nodes[qnode_key].categories)}
            if corresponding_qnode_categories:
                node.categories = list(corresponding_qnode_categories)

    @staticmethod
    def _map_back_to_input_curies(kg: KnowledgeGraph, qg: QueryGraph, log: ARAXResponse):
        """
        This method remaps nodes/edges in the knowledge graph to refer to any 'input' curies (i.e., the specific curies
        listed in the query graph) instead of the canonical curies for those concepts. See issue #1622.
        NOTE: If two input curies map to the same canonical curie, we record only ONE of those mappings. We decided at
              a Sep. 2021 mini-hackathon that that was the least bad option vs. copying nodes/edges in such a situation.
        """
        # First create a lookup map of the curies we'll need to remap
        canonical_to_input_curie_map = dict()
        for qnode_key, qnode in qg.nodes.items():
            if qnode.ids:
                canonical_nodes_info = eu.get_canonical_curies_dict(qnode.ids, log)
                for input_curie, canonical_node_info in canonical_nodes_info.items():
                    if canonical_node_info:
                        canonical_curie = canonical_node_info["preferred_curie"]
                        if input_curie != canonical_curie:
                            canonical_to_input_curie_map[canonical_curie] = input_curie

        # Then remap nodes to use the input curies (and their corresponding names) instead of canonical curies
        if canonical_to_input_curie_map:
            log.debug(f"Mapping {len(canonical_to_input_curie_map)} canonical curies back to their corresponding "
                      f"'input' curies (listed in the QG)")
            input_curie_names_map = eu.get_curie_names(list(canonical_to_input_curie_map.values()), log)
            for canonical_curie, input_curie in canonical_to_input_curie_map.items():
                if canonical_curie in kg.nodes:  # Curies may have already been remapped on a prior expand() call
                    node = kg.nodes[canonical_curie]
                    node.name = input_curie_names_map.get(input_curie, node.name)
                    kg.nodes[input_curie] = node
                    del kg.nodes[canonical_curie]
                    # Remap any edges that refer to the nodes we just remapped
                    connected_edge_keys = {edge_key for edge_key, edge in kg.edges.items()
                                           if edge.subject == canonical_curie or edge.object == canonical_curie}
                    for edge_key in connected_edge_keys:
                        edge = kg.edges[edge_key]
                        if edge.subject == canonical_curie:
                            edge.subject = input_curie
                        if edge.object == canonical_curie:
                            edge.object = input_curie
        else:
            log.debug(f"No KG nodes found that use a different curie than was asked for in the QG")

    @staticmethod
    def _get_prune_threshold(one_hop_qg: QueryGraph) -> int:
        """
        Returns the prune threshold for the given qedge (i.e., the max number of nodes allowed to be fed in as 'input'
        curies for this qedge expansion).
        """
        qedge = next(qedge for qedge in one_hop_qg.edges.values())
        qnode_a = one_hop_qg.nodes[qedge.subject]
        qnode_b = one_hop_qg.nodes[qedge.object]
        large_categories = {"biolink:NamedThing", "biolink:ChemicalEntity"}
        # Handle (curie(s))--(curie(s)) queries
        if qnode_a.ids and qnode_b.ids:
            # Be lenient for input qnode since it will be constrained by output qnode's curies
            return 5000
        # Handle (curie(s))--(>=0 categories) queries
        else:
            open_ended_qnode_categories = set(qnode_a.categories) if not qnode_a.ids else set(qnode_b.categories)
            if (not open_ended_qnode_categories or open_ended_qnode_categories.intersection(large_categories)) and \
                    (not qedge.predicates or "biolink:related_to" in qedge.predicates):
                # Be more strict when such broad categories/predicates are used
                return 100
            elif not open_ended_qnode_categories or open_ended_qnode_categories.intersection(large_categories):
                return 200
            else:
                return 500

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
