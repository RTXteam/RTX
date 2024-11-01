#!/bin/env python3
import copy
import json
import sys
import os
import time
from collections import defaultdict

import aiohttp
import asyncio
import requests
from typing import List, Dict, Set, Union, Optional, Tuple

import requests_cache

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import Expand.expand_utilities as eu
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
from Expand.kp_selector import KPSelector
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_query import ARAXQuery
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.result import Result
from openapi_server.models.attribute import Attribute
from openapi_server.models.retrieval_source import RetrievalSource


class TRAPIQuerier:

    def __init__(self, response_object: ARAXResponse, kp_name: str, user_specified_kp: bool, kp_timeout: Optional[int],
                 kp_selector: KPSelector = None, force_local: bool = False):
        self.log = response_object
        self.kp_infores_curie = kp_name
        self.user_specified_kp = user_specified_kp
        self.kp_timeout = kp_timeout
        self.force_local = force_local
        if kp_selector is None:
            kp_selector = KPSelector()
        self.kp_selector = kp_selector
        self.kp_endpoint = kp_selector.kp_urls[self.kp_infores_curie]
        self.qnodes_with_single_id = dict()  # This is set during the processing of each query
        self.arax_infores_curie = "infores:arax"
        self.arax_retrieval_source = RetrievalSource(resource_id=self.arax_infores_curie,
                                                     resource_role="aggregator_knowledge_source",
                                                     upstream_resource_ids=[self.kp_infores_curie])

    async def answer_one_hop_query_async(self, query_graph: QueryGraph,
                                         alter_kg2_treats_edges: bool = False) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :param alter_kg2_treats_edges: If true, will query KG2 for higher-level treats-type predicates instead of just
                                        'treats'. Any higher-level returned edges will later be altered to have 'treats'
                                        predicates in ARAX_expander.py.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(query_graph)  # Create a copy so we don't modify the original
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)
        self.qnodes_with_single_id = {qnode_key: qnode.ids[0] for qnode_key, qnode in query_graph.nodes.items()
                                      if qnode.ids and len(qnode.ids) == 1}
        if self.qnodes_with_single_id:
            self.log.debug(f"{self.kp_infores_curie}: Qnodes with an implied parent query ID are: {self.qnodes_with_single_id}")

        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Verify that the KP accepts these predicates/categories/prefixes
        if self.kp_infores_curie != "infores:rtx-kg2":
            if self.user_specified_kp:  # This is already done if expand chose the KP itself
                if not self.kp_selector.kp_accepts_single_hop_qg(qg_copy, self.kp_infores_curie):
                    log.error(f"{self.kp_infores_curie} cannot answer queries with the specified categories/predicates",
                              error_code="UnsupportedQG")
                    return final_kg

        # Convert the QG so that it uses curies with prefixes the KP likes
        qg_copy = self.kp_selector.make_qg_use_supported_prefixes(qg_copy, self.kp_infores_curie, log)
        if not qg_copy:  # Means no equivalent curies with supported prefixes were found
            skipped_message = f"No equivalent curies with supported prefixes found"
            log.update_query_plan(qedge_key, self.kp_infores_curie, "Skipped", skipped_message)
            return final_kg

        # Patch to address lack of answers from KG2 for treats queries after treats refactor #2328
        if alter_kg2_treats_edges and self.kp_infores_curie == "infores:rtx-kg2":
            for qedge in qg_copy.edges.values():  # Note there's only ever one qedge per QG here
                qedge.predicates = list(set(qedge.predicates).union({"biolink:treats_or_applied_or_studied_to_treat"}))
                log.info(f"For querying infores:rtx-kg2, edited {qedge_key} to use higher treats-type predicate: "
                         f"{qedge.predicates}")

        # Answer the query using the KP and load its answers into our object model
        final_kg = await self._answer_query_using_kp_async(qg_copy)

        return final_kg

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        # TODO: Delete this method once we're ready to let go of the multiprocessing (vs. asyncio) option
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(query_graph)  # Create a copy so we don't modify the original
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)

        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Verify that the KP accepts these predicates/categories/prefixes
        if self.kp_infores_curie != "infores:rtx-kg2":
            if self.user_specified_kp:  # This is already done if expand chose the KP itself
                if not self.kp_selector.kp_accepts_single_hop_qg(qg_copy, self.kp_infores_curie):
                    log.error(f"{self.kp_infores_curie} cannot answer queries with the specified categories/predicates",
                              error_code="UnsupportedQG")
                    return final_kg

        # Convert the QG so that it uses curies with prefixes the KP likes
        qg_copy = self.kp_selector.make_qg_use_supported_prefixes(qg_copy, self.kp_infores_curie, log)
        if not qg_copy:  # Means no equivalent curies with supported prefixes were found
            skipped_message = f"No equivalent curies with supported prefixes found"
            log.update_query_plan(qedge_key, self.kp_infores_curie, "Skipped", skipped_message)
            return final_kg

        # Answer the query using the KP and load its answers into our object model
        final_kg = self._answer_query_using_kp(qg_copy)
        return final_kg

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a single-node (edge-less) query using the specified KP.
        :param single_node_qg: A TRAPI query graph containing a single node (no edges).
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
           results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(single_node_qg)

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_single_node_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Answer the query using the KP and load its answers into our object model
        final_kg = self._answer_query_using_kp(qg_copy)
        return final_kg

    def _verify_is_one_hop_query_graph(self, query_graph: QueryGraph):
        if len(query_graph.edges) != 1:
            self.log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) > 2:
            self.log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) < 2:
            self.log.error(f"answer_one_hop_query() was passed a query graph with less than two nodes: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _verify_is_single_node_query_graph(self, query_graph: QueryGraph):
        if len(query_graph.edges) > 0:
            self.log.error(f"answer_single_node_query() was passed a query graph that has edges: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _get_kg_to_qg_mappings_from_results(self, results: List[Result], qg: QueryGraph) -> Tuple[Dict[str, Dict[str, Set[str]]], Dict[str, Set[str]]]:
        """
        This function returns a dictionary in which one can lookup which qnode_keys/qedge_keys a given node/edge
        fulfills. Like: {"nodes": {"PR:11": {"n00"}, "MESH:22": {"n00", "n01"} ... }, "edges": { ... }}
        """
        qnodes_with_multiple_ids = {qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.ids and len(qnode.ids) > 1}
        qnodes_with_single_id = {qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.ids and len(qnode.ids) == 1}
        qnode_key_mappings = defaultdict(set)
        kg_id_to_parent_query_id_map = defaultdict(set)
        qedge_key_mappings = defaultdict(set)
        for result in results:
            # Record mappings from the returned node to the parent curie listed in the QG that it is fulfilling
            for qnode_key, node_bindings in result.node_bindings.items():
                query_node_ids = set(eu.convert_to_list(qg.nodes[qnode_key].ids))
                for node_binding in node_bindings:
                    kg_id = node_binding.id
                    qnode_key_mappings[kg_id].add(qnode_key)
                    # Handle case where the KP does return a query_id
                    if node_binding.query_id:
                        if node_binding.query_id in query_node_ids:
                            kg_id_to_parent_query_id_map[kg_id].add(node_binding.query_id)
                        else:
                            self.log.warning(f"{self.kp_infores_curie} returned a NodeBinding.query_id ({node_binding.query_id})"
                                             f" for {qnode_key} that is not in {qnode_key}'s ids in the QG sent "
                                             f"to {self.kp_infores_curie}. This is invalid TRAPI. Skipping this binding.")
                    # Handle case where KP does NOT return a query_id (may or may not be valid TRAPI)
                    else:
                        if qnode_key in qnodes_with_single_id:
                            implied_parent_id = list(query_node_ids)[0]
                            kg_id_to_parent_query_id_map[kg_id].add(implied_parent_id)
                        elif qnode_key in qnodes_with_multiple_ids:
                            if kg_id in query_node_ids:
                                implied_parent_id = kg_id
                                kg_id_to_parent_query_id_map[kg_id].add(implied_parent_id)
                            else:
                                self.log.warning(f"{self.kp_infores_curie} returned a node binding for {qnode_key} that does "
                                                 f"not include a query_id, and {qnode_key} has multiple ids in the "
                                                 f"query sent to {self.kp_infores_curie}, none of which are the KG ID ({kg_id})."
                                                 f" This is invalid TRAPI. Skipping this binding.")

            for analysis in result.analyses:  # TODO: Maybe later extract Analysis support graphs from KPs?
                if analysis.edge_bindings:
                    for qedge_key, edge_bindings in analysis.edge_bindings.items():
                        for edge_binding in edge_bindings:
                            kg_id = edge_binding.id
                            qedge_key_mappings[kg_id].add(qedge_key)

        if not self.kp_infores_curie == "infores:rtx-kg2":
            # Convert parent curie mappings back to canonical form (we send KPs synonyms sometimes..)
            raw_parent_query_ids = {parent_curie for kg_id, query_ids in kg_id_to_parent_query_id_map.items()
                                    for parent_curie in query_ids}
            canonical_parent_query_ids = eu.get_canonical_curies_dict(list(raw_parent_query_ids), self.log)
            for kg_id in set(kg_id_to_parent_query_id_map):
                canonical_query_ids = {canonical_parent_query_ids[raw_parent_id]["preferred_curie"]
                                       if canonical_parent_query_ids.get(raw_parent_id) else raw_parent_id
                                       for raw_parent_id in kg_id_to_parent_query_id_map.get(kg_id, set())}
                kg_id_to_parent_query_id_map[kg_id] = canonical_query_ids

        return {"nodes": qnode_key_mappings, "edges": qedge_key_mappings}, kg_id_to_parent_query_id_map

    async def _answer_query_using_kp_async(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        request_body = self._get_prepped_request_body(query_graph)
        query_sent = copy.deepcopy(request_body)
        query_timeout = self._get_query_timeout_length()
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)

        # Avoid calling the KG2 TRAPI endpoint if the 'force_local' flag is set (used only for testing/dev work)
        num_input_curies = max([len(eu.convert_to_list(qnode.ids)) for qnode in query_graph.nodes.values()])
        waiting_message = f"Query with {num_input_curies} curies sent: waiting for response"
        self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Waiting", waiting_message, query=query_sent)
        start = time.time()
        if self.force_local and self.kp_infores_curie == 'infores:rtx-kg2':
            json_response = self._answer_query_force_local(request_body)
        # Otherwise send the query graph to the KP's TRAPI API
        else:
            self.log.debug(f"{self.kp_infores_curie}: Sending query to {self.kp_infores_curie} API ({self.kp_endpoint})")
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                try:
                    async with session.post(f"{self.kp_endpoint}/query",
                                            json=request_body,
                                            headers={'accept': 'application/json'},
                                            timeout=query_timeout) as response:
                        if response.status == 200:
                            json_response = await response.json()
                        else:
                            wait_time = round(time.time() - start)
                            http_error_message = f"Returned HTTP error {response.status} after {wait_time} seconds"
                            self.log.warning(f"{self.kp_infores_curie}: {http_error_message}. Query sent to KP was: {request_body}")
                            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", http_error_message)
                            return QGOrganizedKnowledgeGraph()
                except asyncio.exceptions.TimeoutError:
                    timeout_message = f"Query timed out after {query_timeout} seconds"
                    self.log.warning(f"{self.kp_infores_curie}: {timeout_message}")
                    self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Timed out", timeout_message)
                    return QGOrganizedKnowledgeGraph()
                except Exception as ex:
                    wait_time = round(time.time() - start)
                    exception_message = f"Request threw exception after {wait_time} seconds: {type(ex)}"
                    self.log.warning(f"{self.kp_infores_curie}: {exception_message}")
                    self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", exception_message)
                    return QGOrganizedKnowledgeGraph()

        wait_time = round(time.time() - start)
        answer_kg = self._load_kp_json_response(json_response, query_graph)
        done_message = f"Returned {len(answer_kg.edges_by_qg_id.get(qedge_key, dict()))} edges in {wait_time} seconds"
        self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Done", done_message)
        return answer_kg

    def _answer_query_using_kp(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        # TODO: Delete this method once we're ready to let go of the multiprocessing (vs. asyncio) option
        request_body = self._get_prepped_request_body(query_graph)
        query_timeout = self._get_query_timeout_length()

        # Avoid calling the KG2 TRAPI endpoint if the 'force_local' flag is set (used only for testing/dev work)
        if self.force_local and self.kp_infores_curie == 'infores:rtx-kg2':
            json_response = self._answer_query_force_local(request_body)
        # Otherwise send the query graph to the KP's TRAPI API
        else:
            self.log.debug(f"{self.kp_infores_curie}: Sending query to {self.kp_infores_curie} API ({self.kp_endpoint})")
            try:
                with requests_cache.disabled():
                    start = time.time()
                    kp_response = requests.post(f"{self.kp_endpoint}/query",
                                                json=request_body,
                                                headers={'accept': 'application/json'},
                                                timeout=query_timeout)
                    self.log.wait_time = round(time.time() - start)
            except Exception:
                timeout_message = f"Query timed out after {query_timeout} seconds"
                self.log.warning(f"{self.kp_infores_curie}: {timeout_message}")
                self.log.timed_out = query_timeout
                return QGOrganizedKnowledgeGraph()
            if kp_response.status_code != 200:
                self.log.warning(f"{self.kp_infores_curie} API returned response of {kp_response.status_code}. "
                                 f"Response from KP was: {kp_response.text}")
                self.log.http_error = f"HTTP {kp_response.status_code}"
                return QGOrganizedKnowledgeGraph()
            else:
                json_response = kp_response.json()

        answer_kg = self._load_kp_json_response(json_response, query_graph)
        return answer_kg

    def _get_prepped_request_body(self, qg: QueryGraph) -> dict:
        # Liberally use is_set to improve performance since we don't need individual results
        for qnode_key, qnode in qg.nodes.items():
            if not qnode.ids or len(qnode.ids) > 1:
                qnode.is_set = True

        # Strip non-essential and 'empty' properties off of our qnodes and qedges
        stripped_qnodes = {qnode_key: self._strip_empty_properties(qnode)
                           for qnode_key, qnode in qg.nodes.items()}
        stripped_qedges = {qedge_key: self._strip_empty_properties(qedge)
                           for qedge_key, qedge in qg.edges.items()}

        # Load the query into a JSON Query object
        json_qg = {'nodes': stripped_qnodes, 'edges': stripped_qedges}
        body = {'message': {'query_graph': json_qg}}
        body['submitter'] = "infores:arax"
        if self.kp_infores_curie == "infores:rtx-kg2":
            body['return_minimal_metadata'] = True  # Don't want KG2 attributes because ARAX adds them later (faster)
        return body

    def _answer_query_force_local(self, request_body: dict) -> dict:
        self.log.debug(f"{self.kp_infores_curie}: Pretending to send query to KG2 API (really it will be run locally)")
        arax_query = ARAXQuery()
        kg2_araxquery_response = arax_query.query(request_body, mode='RTXKG2')
        json_response = kg2_araxquery_response.envelope.to_dict()
        return json_response

    def _load_kp_json_response(self, json_response: dict, qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        # Load the results into the object model
        answer_kg = QGOrganizedKnowledgeGraph()
        if not json_response.get("message"):
            self.log.warning(f"{self.kp_infores_curie}: No 'message' was included in the response from {self.kp_infores_curie}. "
                             f"Response was: {json.dumps(json_response, indent=4)}")
            return answer_kg
        elif not json_response["message"].get("results"):
            self.log.debug(f"{self.kp_infores_curie}: No 'results' were returned.")
            json_response["message"]["results"] = []  # Setting this to empty list helps downstream processing
            return answer_kg
        else:
            self.log.debug(f"{self.kp_infores_curie}: Got results from {self.kp_infores_curie}.")
            kp_message = ARAXMessenger().from_dict(json_response["message"])

        # Work around genetics provider's curie whitespace bug for now  TODO: remove once they've fixed it
        if self.kp_infores_curie == "infores:genetics-data-provider":
            self._remove_whitespace_from_curies(kp_message)

        # Build a map that indicates which qnodes/qedges a given node/edge fulfills
        kg_to_qg_mappings, query_curie_mappings = self._get_kg_to_qg_mappings_from_results(kp_message.results, qg)

        # Populate our final KG with the returned edges
        returned_edge_keys_missing_qg_bindings = set()
        nodes_dict = kp_message.knowledge_graph.nodes
        for returned_edge_key, returned_edge in kp_message.knowledge_graph.edges.items():
            # Catch invalid subject/object
            if not returned_edge.subject or not returned_edge.object:
                self.log.warning(f"{self.kp_infores_curie}: Edge has empty subject/object, skipping. "
                                 f"subject: '{returned_edge.subject}', object: '{returned_edge.object}'")
                continue
            if returned_edge.subject not in nodes_dict or returned_edge.object not in nodes_dict:
                self.log.warning(f"{self.kp_infores_curie}: Edge is an orphan, skipping. "
                                 f"subject: '{returned_edge.subject}', object: '{returned_edge.object}'")
                continue

            preferred_subject, preferred_object = eu.get_canonical_curies_list([returned_edge.subject, returned_edge.object], self.log)
            if not preferred_subject:
                self.log.debug(f"{self.kp_infores_curie}: Edge has no preferred subject, skipping. "
                                 f"subject: '{returned_edge.subject}'")
            else: 
                returned_edge.subject = preferred_subject
        
            if not preferred_object:
                self.log.debug(f"{self.kp_infores_curie}: Edge has no preferred object, skipping. "
                                 f"object: '{returned_edge.object}'")
            else:
                returned_edge.object = preferred_object



            arax_edge_key = self._get_arax_edge_key(returned_edge)  # Convert to an ID that's unique for us

            # Put in a placeholder for missing required attribute fields to try to keep our answer TRAPI-compliant
            if returned_edge.attributes:
                for attribute in returned_edge.attributes:
                    if not attribute.attribute_type_id:
                        attribute.attribute_type_id = f"not provided (this attribute came from {self.kp_infores_curie})"

            # Indicate that this edge passed through ARAX
            if returned_edge.sources:
                returned_edge.sources.append(self.arax_retrieval_source)
            else:
                returned_edge.sources = [self.arax_retrieval_source]

            # Delete any support graph references for now # TODO: Extract such support graphs? #2060
            if returned_edge.attributes:
                returned_edge.attributes = [attribute for attribute in returned_edge.attributes
                                            if attribute.attribute_type_id != "biolink:support_graphs"]

            if returned_edge_key in kg_to_qg_mappings['edges']:
                for qedge_key in kg_to_qg_mappings['edges'][returned_edge_key]:
                    answer_kg.add_edge(arax_edge_key, returned_edge, qedge_key)
            else:
                returned_edge_keys_missing_qg_bindings.add(returned_edge_key)
        if returned_edge_keys_missing_qg_bindings:
            self.log.warning(f"{self.kp_infores_curie}: {len(returned_edge_keys_missing_qg_bindings)} edges in the KP's answer "
                             f"KG have no bindings to the QG: {returned_edge_keys_missing_qg_bindings}")

        # Populate our final KG with the returned nodes
        returned_node_keys_missing_qg_bindings = set()
        for returned_node_key, returned_node in kp_message.knowledge_graph.nodes.items():
            if not returned_node_key:
                self.log.warning(f"{self.kp_infores_curie}: Node has empty ID, skipping. Node key is: "
                                 f"'{returned_node_key}'")
            elif returned_node_key not in kg_to_qg_mappings['nodes']:
                returned_node_keys_missing_qg_bindings.add(returned_node_key)
            else:
                for qnode_key in kg_to_qg_mappings['nodes'][returned_node_key]:
                    answer_kg.add_node(returned_node_key, returned_node, qnode_key)
            if returned_node.attributes:
                for attribute in returned_node.attributes:
                    if not attribute.attribute_type_id:
                        attribute.attribute_type_id = f"not provided (this attribute came from {self.kp_infores_curie})"
        if returned_node_keys_missing_qg_bindings:
            self.log.warning(f"{self.kp_infores_curie}: {len(returned_node_keys_missing_qg_bindings)} nodes in the KP's answer "
                             f"KG have no bindings to the QG: {returned_node_keys_missing_qg_bindings}")

        # Fill out our unofficial node.query_ids property
        for nodes in answer_kg.nodes_by_qg_id.values():
            for node_key, node in nodes.items():
                node.query_ids = eu.convert_to_list(query_curie_mappings.get(node_key))

        # Add subclass_of edges for any parent to child relationships KPs returned
        answer_kg = self._add_subclass_of_edges(answer_kg)

        return answer_kg

    @staticmethod
    def _strip_empty_properties(qnode_or_qedge: Union[QNode, QEdge]) -> Dict[str, any]:
        dict_version_of_object = qnode_or_qedge.to_dict()
        stripped_dict = {property_name: value for property_name, value in dict_version_of_object.items()
                         if dict_version_of_object.get(property_name) not in [None, []]}
        return stripped_dict

    def _get_arax_edge_key(self, edge: Edge) -> str:
        qualifiers_dict = {qualifier.qualifier_type_id: qualifier.qualifier_value for qualifier in edge.qualifiers} if edge.qualifiers else dict()
        qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate")
        qualified_object_direction = qualifiers_dict.get("biolink:object_direction_qualifier")
        qualified_object_aspect = qualifiers_dict.get("biolink:object_aspect_qualifier")
        qualified_portion = f"{qualified_predicate}--{qualified_object_direction}--{qualified_object_aspect}"
        primary_ks = eu.get_primary_knowledge_source(edge)
        edge_key = f"{self.kp_infores_curie}:{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--{primary_ks}"
        return edge_key

    def _get_query_timeout_length(self) -> int:
        # Returns the number of seconds we should wait for a response
        if self.kp_infores_curie == "infores:rtx-kg2":
            return 600
        elif self.kp_timeout:
            return self.kp_timeout
        else:
            return 120

    def _add_subclass_of_edges(self, answer_kg: QGOrganizedKnowledgeGraph) -> QGOrganizedKnowledgeGraph:
        for qnode_key in answer_kg.nodes_by_qg_id:
            nodes_with_non_empty_parent_query_ids = {node_key for node_key, node in answer_kg.nodes_by_qg_id[qnode_key].items()
                                                     if hasattr(node, "query_ids") and node.query_ids}
            initial_edge_count = sum([len(edges) for edges in answer_kg.edges_by_qg_id.values()])
            # Grab info for any parent nodes missing from the KG in bulk for easy access later
            all_parent_query_ids = {parent_id for node_key in nodes_with_non_empty_parent_query_ids
                                    for parent_id in answer_kg.nodes_by_qg_id[qnode_key][node_key].query_ids}
            parents_missing_from_kg = all_parent_query_ids.difference(set(answer_kg.nodes_by_qg_id[qnode_key]))
            parent_node_info = eu.get_canonical_curies_dict(list(parents_missing_from_kg), self.log)

            # Add subclass_of edges to the answer KG for any nodes that the KP provided query ID mappings for
            for node_key in nodes_with_non_empty_parent_query_ids:
                subclass_edges = []
                parent_query_ids = answer_kg.nodes_by_qg_id[qnode_key][node_key].query_ids
                for parent_query_id in parent_query_ids:
                    if parent_query_id is not None and parent_query_id != node_key:
                        subclass_edge = Edge(subject=node_key, object=parent_query_id, predicate="biolink:subclass_of")

                        # Add provenance info to this edge so it's clear where the assertion came from
                        kp_retrieval_source = RetrievalSource(resource_id=self.kp_infores_curie,
                                                              resource_role="primary_knowledge_source")
                        subclass_edge.sources = [kp_retrieval_source, self.arax_retrieval_source]

                        # Further describe in plain english where this edge comes from
                        edge_note = Attribute(attribute_type_id="biolink:description",
                                              value=f"ARAX created this edge to represent the fact "
                                                    f"that {self.kp_infores_curie} fulfilled {subclass_edge.object}"
                                                    f" (for {qnode_key}) with {subclass_edge.subject}.",
                                              value_type_id="metatype:String",
                                              attribute_source=self.arax_infores_curie)
                        subclass_edge.attributes = [edge_note]

                        subclass_edges.append(subclass_edge)
                if subclass_edges:
                    for edge in subclass_edges:
                        # Add the parent to the KG if it isn't in there already
                        if edge.object not in answer_kg.nodes_by_qg_id[qnode_key]:
                            parent_info_dict = parent_node_info.get(edge.object)
                            if parent_info_dict:
                                parent_node = Node(name=parent_info_dict.get("preferred_name"),
                                                   categories=[parent_info_dict.get("preferred_category")],
                                                   attributes=[])
                            else:
                                parent_node = Node()
                            parent_node.query_ids = []   # Does not need a mapping since it appears in the QG
                            answer_kg.add_node(edge.object, parent_node, qnode_key)
                        preferred_curies = eu.get_canonical_curies_list([edge.subject, edge.object], self.log)
                        if preferred_curies:
                            edge.subject, edge.object = preferred_curies
                        else:
                            self.log.debug(f"{self.kp_infores_curie}: Could not find a preferred curie for {edge.subject} or {edge.object}")
                        
                        edge_key = self._get_arax_edge_key(edge)
                        qedge_key = f"subclass:{qnode_key}--{qnode_key}"  # Technically someone could have used this key in their query, but seems highly unlikely..
                        answer_kg.add_edge(edge_key, edge, qedge_key)
            final_edge_count = sum([len(edges) for edges in answer_kg.edges_by_qg_id.values()])
            num_edges_added = final_edge_count - initial_edge_count
            if num_edges_added:
                self.log.debug(f"{self.kp_infores_curie}: Added {num_edges_added} subclass_of edges to the KG based on "
                               f"query ID mappings {self.kp_infores_curie} returned")
        return answer_kg

    @staticmethod
    def _remove_whitespace_from_curies(kp_message):
        kg = kp_message.knowledge_graph
        for node_key in set(kg.nodes):
            node = kg.nodes[node_key]
            del kg.nodes[node_key]
            kg.nodes[node_key.strip()] = node
        for edge in kg.edges.values():
            edge.subject = edge.subject.strip()
            edge.object = edge.object.strip()
        for result in kp_message.results:
            for qnode_key, node_bindings in result.node_bindings.items():
                for node_binding in node_bindings:
                    node_binding.id = node_binding.id.strip()
                    if node_binding.query_id:
                        node_binding.query_id = node_binding.query_id.strip()
