#!/bin/env python3
import json
import sys
import os
import requests
from typing import List, Dict, Tuple, Set, Union

import Expand.expand_utilities as eu
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.result import Result


class TRAPIQuerier:

    def __init__(self, response_object: ARAXResponse, kp_name: str):
        self.log = response_object
        self.kp_name = kp_name
        self.kp_endpoint = f"{eu.get_kp_endpoint_url(kp_name)}"
        self.node_category_overrides_for_kp = eu.get_node_category_overrides_for_kp(kp_name)
        self.kp_preferred_prefixes = eu.get_kp_preferred_prefixes(kp_name)
        self.kp_supports_category_lists = eu.kp_supports_category_lists(kp_name)
        self.kp_supports_predicate_lists = eu.kp_supports_predicate_lists(kp_name)
        self.kp_supports_none_for_category = eu.kp_supports_none_for_category(kp_name)
        self.kp_supports_none_for_predicate = eu.kp_supports_none_for_predicate(kp_name)

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :return: A tuple containing:
            1. An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
           results for the query. (Organized by QG IDs.)
            2. A map of which nodes fulfilled which qnode_keys for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        qg_copy = eu.copy_qg(query_graph)  # Create a copy so we don't modify the original

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        qg_copy = self._preprocess_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        if not self.kp_name.endswith("KG2"):  # Skip for KG2 for now since predicates/ isn't symmetric yet
            self._verify_qg_is_accepted_by_kp(qg_copy)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        # Answer the query using the KP and load its answers into our object model
        if self.kp_name.endswith("KG2"):
            # Our KPs can handle batch queries (where qnode.id is a list of curies)
            final_kg, edge_to_nodes_map = self._answer_query_using_kp(qg_copy)
        else:
            # Otherwise we need to search for curies one-by-one (until TRAPI includes a batch querying method)
            qedge = next(qedge for qedge in qg_copy.edges.values())
            subject_qnode_curies = eu.convert_to_list(qg_copy.nodes[qedge.subject].id)
            subject_qnode_curies = subject_qnode_curies if subject_qnode_curies else [None]
            object_qnode_curies = eu.convert_to_list(qg_copy.nodes[qedge.object].id)
            object_qnode_curies = object_qnode_curies if object_qnode_curies else [None]
            curie_combinations = [(curie_subj, curie_obj) for curie_subj in subject_qnode_curies for curie_obj in object_qnode_curies]
            # Query KP for all pairs of subject/object curies (pairs look like ("curie1", None) if one has no curies)
            for curie_combination in curie_combinations:
                subject_curie = curie_combination[0]
                object_curie = curie_combination[1]
                qg_copy.nodes[qedge.subject].id = subject_curie
                qg_copy.nodes[qedge.object].id = object_curie
                self.log.debug(f"Current curie pair is: subject: {subject_curie}, object: {object_curie}")
                if self.kp_supports_category_lists and self.kp_supports_predicate_lists:
                    sub_kg, sub_edge_to_nodes_map = self._answer_query_using_kp(qg_copy)
                else:
                    sub_kg, sub_edge_to_nodes_map = self._answer_query_for_kps_who_dont_like_lists(qg_copy)
                edge_to_nodes_map.update(sub_edge_to_nodes_map)
                final_kg = eu.merge_two_kgs(sub_kg, final_kg)

        return final_kg, edge_to_nodes_map

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a single-node (edge-less) query using the specified KP.
        :param single_node_qg: A TRAPI query graph containing a single node (no edges).
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
           results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = eu.copy_qg(single_node_qg)

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_single_node_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg
        qg_copy = self._preprocess_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Answer the query using the KP and load its answers into our object model
        final_kg, _ = self._answer_query_using_kp(qg_copy)
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

    def _preprocess_query_graph(self, query_graph: QueryGraph):
        # Make sure category and predicate are always lists
        for qnode_key, qnode in query_graph.nodes.items():
            qnode.category = eu.convert_to_list(qnode.category)
        for qedge_key, qedge in query_graph.edges.items():
            qedge.predicate = eu.convert_to_list(qedge.predicate)
        # Make any overrides of categories that are needed (e.g., consider 'proteins' to be 'genes', etc.)
        if self.node_category_overrides_for_kp:
            query_graph = self._override_qnode_types_as_needed(query_graph)
        # Convert curies to the prefixes that this KP prefers (if we know that info)
        if self.kp_preferred_prefixes:
            query_graph = self._convert_to_accepted_curie_prefixes(query_graph)
        return query_graph

    def _override_qnode_types_as_needed(self, query_graph: QueryGraph) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            overriden_categories = {self.node_category_overrides_for_kp.get(qnode_category, qnode_category)
                                    for qnode_category in qnode.category}
            qnode.category = list(overriden_categories)
        return query_graph

    def _verify_qg_is_accepted_by_kp(self, query_graph: QueryGraph):
        kp_predicates_response = requests.get(f"{self.kp_endpoint}/predicates", headers={'accept': 'application/json'})
        if kp_predicates_response.status_code != 200:
            self.log.warning(f"Unable to access {self.kp_name}'s predicates endpoint "
                             f"(returned status of {kp_predicates_response.status_code})")
        else:
            predicates_dict = kp_predicates_response.json()
            qnodes = query_graph.nodes
            qedge_key = next(qedge_key for qedge_key in query_graph.edges)
            qedge = query_graph.edges[qedge_key]
            qg_triples = [[qnodes[qedge.subject].category, qedge.predicate, qnodes[qedge.object].category]
                          for qedge in query_graph.edges.values()]
            for triple in qg_triples:
                query_subject_categories = set(triple[0])
                query_predicates = set(triple[1])
                query_object_categories = set(triple[2])

                # Make sure the subject qnode's category(s) are accepted by the KP
                allowed_subj_categories = set(predicates_dict)
                accepted_query_subj_categories = query_subject_categories.intersection(allowed_subj_categories)
                if not query_subject_categories and self.kp_supports_none_for_category:
                    # If this KP supports None for category, we'll pretend we have all supported categories
                    accepted_query_subj_categories = allowed_subj_categories
                if not accepted_query_subj_categories:
                    self.log.error(f"{self.kp_name} doesn't support {qedge.subject}'s category. Supported categories "
                                   f"for subject qnodes are: {allowed_subj_categories}",
                                   error_code="UnsupportedQueryForKP")
                    return

                # Make sure that, given the subject qnode's category(s), >=1 of the object's categories are accepted
                allowed_object_categories = {category for subj_category in accepted_query_subj_categories
                                             for category in predicates_dict[subj_category]}
                accepted_query_obj_categories = query_object_categories.intersection(allowed_object_categories)
                if not query_object_categories and self.kp_supports_none_for_category:
                    # If this KP supports None for category, we'll pretend we have all nested categories on this qnode
                    accepted_query_obj_categories = allowed_object_categories
                if not accepted_query_obj_categories:
                    self.log.error(f"{self.kp_name} doesn't support {qedge.object}'s category. When subject "
                                   f"category is {query_subject_categories}, supported object categories are: "
                                   f"{allowed_object_categories}", error_code="UnsupportedQueryForKP")
                    return

                # Make sure that, given the subject/object categories, at least one of the predicates is accepted
                allowed_predicates = set()
                for subj_category in accepted_query_subj_categories:
                    for obj_category in accepted_query_obj_categories:
                        if obj_category in predicates_dict[subj_category]:
                            allowed_predicates.update(set(predicates_dict[subj_category][obj_category]))
                accepted_query_predicates = query_predicates.intersection(allowed_predicates)
                if not query_predicates and self.kp_supports_none_for_predicate:
                    # If this KP supports None for predicate, we'll pretend we have all nested predicates
                    accepted_query_predicates = allowed_predicates
                if not accepted_query_predicates:
                    self.log.error(f"{self.kp_name} doesn't support {qedge_key}'s predicate. For "
                                   f"{query_subject_categories}-->{query_object_categories} qedges, supported "
                                   f"predicates are: {allowed_predicates}")
                    return

    def _convert_to_accepted_curie_prefixes(self, query_graph: QueryGraph) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.id:
                equivalent_curies = eu.get_curie_synonyms(qnode.id, self.log)
                # TODO: Right to take first category here?
                preferred_prefix = self.kp_preferred_prefixes.get(qnode.category[0]) if qnode.category else None
                if preferred_prefix:
                    desired_curies = [curie for curie in equivalent_curies if curie.startswith(f"{preferred_prefix}:")]
                    if desired_curies:
                        qnode.id = desired_curies if len(desired_curies) > 1 else desired_curies[0]
                        self.log.debug(f"Converted qnode {qnode_key} curie to {qnode.id}")
                    else:
                        self.log.warning(f"Could not convert qnode {qnode_key} curie(s) to preferred prefix "
                                         f"({self.kp_preferred_prefixes[qnode.category[0]]})")
        return query_graph

    @staticmethod
    def _get_kg_to_qg_mappings_from_results(results: List[Result]) -> Dict[str, Dict[str, Set[str]]]:
        """
        This function returns a dictionary in which one can lookup which qnode_keys/qedge_keys a given node/edge
        fulfills. Like: {"nodes": {"PR:11": {"n00"}, "MESH:22": {"n00", "n01"} ... }, "edges": { ... }}
        """
        qnode_key_mappings = dict()
        qedge_key_mappings = dict()
        for result in results:
            for qnode_key, node_bindings in result.node_bindings.items():
                kg_ids = {node_binding.id for node_binding in node_bindings}
                for kg_id in kg_ids:
                    if kg_id not in qnode_key_mappings:
                        qnode_key_mappings[kg_id] = set()
                    qnode_key_mappings[kg_id].add(qnode_key)
            for qedge_key, edge_bindings in result.edge_bindings.items():
                kg_ids = {edge_binding.id for edge_binding in edge_bindings}
                for kg_id in kg_ids:
                    if kg_id not in qedge_key_mappings:
                        qedge_key_mappings[kg_id] = set()
                    qedge_key_mappings[kg_id].add(qedge_key)
        return {"nodes": qnode_key_mappings, "edges": qedge_key_mappings}

    def _create_edge_to_nodes_map(self, kg_to_qg_mappings: Dict[str, Dict[str, Set[str]]], kg: KnowledgeGraph, qedge: QEdge) -> Dict[str, Dict[str, str]]:
        """
        This function creates an 'edge_to_nodes_map' that indicates which of an edge's nodes (subject or object) is
        fulfilling which qnode ID (since edge.subject does not necessarily fulfill qedge.subject).
        Example: {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:12'}}
        """
        edge_to_nodes_map = dict()
        node_to_qnode_map = kg_to_qg_mappings["nodes"]
        for edge_key, edge in kg.edges.items():
            arax_edge_key = self._get_arax_edge_key(edge)  # We use edge keys guaranteed to be unique across KPs
            if qedge.subject in node_to_qnode_map[edge.subject] and qedge.object in node_to_qnode_map[edge.object]:
                edge_to_nodes_map[arax_edge_key] = {qedge.subject: edge.subject, qedge.object: edge.object}
            else:
                edge_to_nodes_map[arax_edge_key] = {qedge.subject: edge.object, qedge.object: edge.subject}
        return edge_to_nodes_map

    def _answer_query_using_kp(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        answer_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        # Strip non-essential and 'empty' properties off of our qnodes and qedges
        stripped_qnodes = {qnode_key: self._strip_empty_properties(qnode)
                           for qnode_key, qnode in query_graph.nodes.items()}
        stripped_qedges = {qedge_key: self._strip_empty_properties(qedge)
                           for qedge_key, qedge in query_graph.edges.items()}

        # Send the query to the KP's API
        body = {'message': {'query_graph': {'nodes': stripped_qnodes, 'edges': stripped_qedges}}}
        self.log.debug(f"Sending query to {self.kp_name} API")
        kp_response = requests.post(f"{self.kp_endpoint}/query", json=body, headers={'accept': 'application/json'})
        json_response = kp_response.json()
        if kp_response.status_code == 200:
            if not json_response.get("message"):
                self.log.warning(
                    f"No 'message' was included in the response from {self.kp_name}. Response from KP was: "
                    f"{json.dumps(json_response, indent=4)}")
            elif not json_response["message"].get("results"):
                self.log.warning(f"No 'results' were returned from {self.kp_name}. Response from KP was: "
                                 f"{json.dumps(json_response, indent=4)}")
                json_response["message"]["results"] = []  # Setting this to empty list helps downstream processing
            else:
                kp_message = ARAXMessenger().from_dict(json_response["message"])
                # Build a map that indicates which qnodes/qedges a given node/edge fulfills
                kg_to_qg_mappings = self._get_kg_to_qg_mappings_from_results(kp_message.results)

                # Populate our final KG with the returned nodes and edges
                for returned_edge_key, returned_edge in kp_message.knowledge_graph.edges.items():
                    arax_edge_key = self._get_arax_edge_key(returned_edge)  # Convert to an ID that's unique for us
                    for qedge_key in kg_to_qg_mappings['edges'][returned_edge_key]:
                        answer_kg.add_edge(arax_edge_key, returned_edge, qedge_key)
                for returned_node_key, returned_node in kp_message.knowledge_graph.nodes.items():
                    for qnode_key in kg_to_qg_mappings['nodes'][returned_node_key]:
                        answer_kg.add_node(returned_node_key, returned_node, qnode_key)
                # Build a map that indicates which of an edge's nodes fulfill which qnode
                if query_graph.edges:
                    qedge = next(qedge for qedge in query_graph.edges.values())
                    edge_to_nodes_map = self._create_edge_to_nodes_map(kg_to_qg_mappings, kp_message.knowledge_graph, qedge)
        else:
            self.log.warning(f"{self.kp_name} API returned response of {kp_response.status_code}. Response from KP was:"
                             f" {json.dumps(json_response, indent=4)}")

        return answer_kg, edge_to_nodes_map

    def _answer_query_for_kps_who_dont_like_lists(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        TRAPI 1.0 says qnode.category and qedge.predicate can both be strings OR lists, but many KPs don't support
        them being lists. So this function pings such KPs one by one for each possible
        subj_category--predicate--obj_category combination.
        """
        qg_copy = eu.copy_qg(query_graph)  # Use a copy of the QG so we don't modify the original
        qnodes = qg_copy.nodes
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)
        qedge = qg_copy.edges[qedge_key]
        subject_categories = qnodes[qedge.subject].category if qnodes[qedge.subject].category else [None]
        object_categories = qnodes[qedge.object].category if qnodes[qedge.object].category else [None]
        predicates = qedge.predicate if qedge.predicate else [None]
        possible_triples = [(subject_category, predicate, object_category) for subject_category in subject_categories
                            for predicate in predicates for object_category in object_categories]
        answer_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        for possible_triple in possible_triples:
            current_subject_category = possible_triple[0]
            current_predicate = possible_triple[1]
            current_object_category = possible_triple[2]
            # Modify the QG so it's asking only for the current category--predicate--category triple
            qg_copy.nodes[qedge.subject].category = current_subject_category
            qg_copy.nodes[qedge.object].category = current_object_category
            qg_copy.edges[qedge_key].predicate = current_predicate
            self.log.debug(f"Current triple is: {current_subject_category}--{current_predicate}--{current_object_category}")
            sub_kg, sub_edge_to_nodes_map = self._answer_query_using_kp(qg_copy)
            # Merge the answers for this triple into our answers received thus far
            edge_to_nodes_map.update(sub_edge_to_nodes_map)
            answer_kg = eu.merge_two_kgs(sub_kg, answer_kg)

        return answer_kg, edge_to_nodes_map

    @staticmethod
    def _strip_empty_properties(qnode_or_qedge: Union[QNode, QEdge]) -> Dict[str, any]:
        dict_version_of_object = qnode_or_qedge.to_dict()
        stripped_dict = {property_name: value for property_name, value in dict_version_of_object.items()
                         if dict_version_of_object.get(property_name) is not None}
        return stripped_dict

    def _get_arax_edge_key(self, edge: Edge) -> str:
        return f"{self.kp_name}:{edge.subject}-{edge.predicate}-{edge.object}"
