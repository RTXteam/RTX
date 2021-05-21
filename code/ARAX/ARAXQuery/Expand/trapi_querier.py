#!/bin/env python3
import json
import sys
import os
import requests
from typing import List, Dict, Set, Union

import Expand.expand_utilities as eu
import requests_cache
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_query import ARAXQuery
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.result import Result
from openapi_server.models.attribute import Attribute


class TRAPIQuerier:

    def __init__(self, response_object: ARAXResponse, kp_name: str, user_specified_kp: bool, force_local: bool = False):
        self.log = response_object
        self.kp_name = kp_name
        self.user_specified_kp = user_specified_kp
        self.force_local = force_local
        self.kp_endpoint = f"{eu.get_kp_endpoint_url(kp_name)}"
        self.node_category_overrides_for_kp = eu.get_node_category_overrides_for_kp(kp_name)
        self.kp_preferred_prefixes = eu.get_kp_preferred_prefixes(kp_name)
        self.kp_supports_category_lists = eu.kp_supports_category_lists(kp_name)
        self.kp_supports_predicate_lists = eu.kp_supports_predicate_lists(kp_name)
        self.kp_supports_none_for_category = eu.kp_supports_none_for_category(kp_name)
        self.kp_supports_none_for_predicate = eu.kp_supports_none_for_predicate(kp_name)
        self.predicates_timeout = 5

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = eu.copy_qg(query_graph)  # Create a copy so we don't modify the original

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg
        qg_copy = self._preprocess_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg
        if self.user_specified_kp and not self.kp_name.endswith("KG2"):  # Skip for KG2 for now since predicates/ isn't symmetric yet
            self._verify_qg_is_accepted_by_kp(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Answer the query using the KP and load its answers into our object model
        if self.kp_name in eu.get_kps_that_support_curie_lists():
            # Only certain KPs can handle batch queries currently (where qnode.id is a list of curies)
            final_kg = self._answer_query_using_kp(qg_copy)
        else:
            # Otherwise we need to search for curies one-by-one (until TRAPI includes a batch querying method)
            qedge = next(qedge for qedge in qg_copy.edges.values())
            subject_qnode_curies = eu.convert_to_list(qg_copy.nodes[qedge.subject].ids)
            subject_qnode_curies = subject_qnode_curies if subject_qnode_curies else [None]
            object_qnode_curies = eu.convert_to_list(qg_copy.nodes[qedge.object].ids)
            object_qnode_curies = object_qnode_curies if object_qnode_curies else [None]
            curie_combinations = [(curie_subj, curie_obj) for curie_subj in subject_qnode_curies for curie_obj in object_qnode_curies]
            # Query KP for all pairs of subject/object curies (pairs look like ("curie1", None) if one has no curies)
            for curie_combination in curie_combinations:
                subject_curie = curie_combination[0]
                object_curie = curie_combination[1]
                qg_copy.nodes[qedge.subject].ids = subject_curie
                qg_copy.nodes[qedge.object].ids = object_curie
                self.log.debug(f"{self.kp_name}: Current curie pair is: subject: {subject_curie}, object: {object_curie}")
                if self.kp_supports_category_lists and self.kp_supports_predicate_lists:
                    sub_kg = self._answer_query_using_kp(qg_copy)
                else:
                    sub_kg = self._answer_query_for_kps_who_dont_like_lists(qg_copy)
                final_kg = eu.merge_two_kgs(sub_kg, final_kg)

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
        qg_copy = eu.copy_qg(single_node_qg)

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_single_node_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg
        qg_copy = self._preprocess_query_graph(qg_copy)
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

    def _preprocess_query_graph(self, query_graph: QueryGraph):
        # Make any overrides of categories that are needed (e.g., consider 'proteins' to be 'genes', etc.)
        if self.node_category_overrides_for_kp:
            query_graph = self._override_qnode_types_as_needed(query_graph)
        # Convert curies to the prefixes that this KP prefers (if we know that info)
        if self.kp_preferred_prefixes:
            query_graph = self._convert_to_accepted_curie_prefixes(query_graph)
        return query_graph

    def _override_qnode_types_as_needed(self, query_graph: QueryGraph) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.categories:
                overriden_categories = {self.node_category_overrides_for_kp.get(qnode_category, qnode_category)
                                        for qnode_category in qnode.categories}
                qnode.categories = list(overriden_categories)
        return query_graph

    def _verify_qg_is_accepted_by_kp(self, query_graph: QueryGraph):
        try:
            with requests_cache.disabled():
                kp_predicates_response = requests.get(f"{self.kp_endpoint}/predicates", timeout=self.predicates_timeout)
        except Exception:
            self.log.warning(f"{self.kp_name}: Timed out trying to hit {self.kp_name}'s /predicates endpoint "
                             f"(waited {self.predicates_timeout} seconds)")
        else:
            if kp_predicates_response.status_code != 200:
                self.log.warning(f"{self.kp_name}: Unable to access {self.kp_name}'s predicates endpoint "
                                 f"(returned status of {kp_predicates_response.status_code})")
                return

            predicates_dict = kp_predicates_response.json()
            qnodes = query_graph.nodes
            qedge_key = next(qedge_key for qedge_key in query_graph.edges)
            qedge = query_graph.edges[qedge_key]
            qg_triples = [[qnodes[qedge.subject].categories, qedge.predicates, qnodes[qedge.object].categories]
                          for qedge in query_graph.edges.values()]
            for triple in qg_triples:
                query_subject_categories = set(triple[0]) if triple[0] else set()
                query_predicates = set(triple[1]) if triple[1] else set()
                query_object_categories = set(triple[2]) if triple[2] else set()

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
            if qnode.ids:
                equivalent_curies = eu.get_curie_synonyms(qnode.ids, self.log)
                # TODO: Right to take first category here?
                preferred_prefix = self.kp_preferred_prefixes.get(qnode.categories[0]) if qnode.categories else None
                if preferred_prefix:
                    desired_curies = [curie for curie in equivalent_curies if curie.startswith(f"{preferred_prefix}:")]
                    if desired_curies:
                        qnode.ids = desired_curies
                        self.log.debug(f"{self.kp_name}: Converted qnode {qnode_key} curie to {qnode.ids}")
                    else:
                        self.log.warning(f"{self.kp_name}: Could not convert qnode {qnode_key} curie(s) to preferred prefix "
                                         f"({self.kp_preferred_prefixes[qnode.categories[0]]})")
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

    def _answer_query_using_kp(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        answer_kg = QGOrganizedKnowledgeGraph()
        # Liberally use is_set to improve performance since we don't need individual results
        for qnode_key, qnode in query_graph.nodes.items():
            if not qnode.ids or len(qnode.ids) > 1:
                qnode.is_set = True

        # Strip non-essential and 'empty' properties off of our qnodes and qedges
        stripped_qnodes = {qnode_key: self._strip_empty_properties(qnode)
                           for qnode_key, qnode in query_graph.nodes.items()}
        stripped_qedges = {qedge_key: self._strip_empty_properties(qedge)
                           for qedge_key, qedge in query_graph.edges.items()}

        # Figure out what an appropriate timeout point is given how many curies are in this query
        query_timeout = self._get_query_timeout_length(query_graph)

        # Send the query to the KP
        query_graph = {'nodes': stripped_qnodes, 'edges': stripped_qedges}
        if not self.kp_name == "RTX-KG2":  # We're using 1.1 for KG2 API, but not other KPs yet (until deadline)
            query_graph = self._switch_qg_to_trapi_1_0(query_graph)
        body = {'message': {'query_graph': query_graph}}
        # Avoid calling the KG2 TRAPI endpoint if the 'force_local' flag is set (used only for testing/dev work)
        if self.force_local and self.kp_name == 'RTX-KG2':
            self.log.debug(f"{self.kp_name}: Pretending to send query to KG2 API (really it will be run locally)")
            arax_query = ARAXQuery()
            kg2_araxquery_response = arax_query.query(body, mode='RTXKG2')
            json_response = kg2_araxquery_response.envelope.to_dict()
        # Otherwise send the query graph to the KP's TRAPI API
        else:
            self.log.debug(f"{self.kp_name}: Sending query to {self.kp_name} API")
            try:
                with requests_cache.disabled():
                    kp_response = requests.post(f"{self.kp_endpoint}/query", json=body, headers={'accept': 'application/json'},
                                                timeout=query_timeout)
            except Exception:
                self.log.warning(f"{self.kp_name}: Query timed out (waited {query_timeout} seconds)")
                return answer_kg
            if kp_response.status_code != 200:
                self.log.warning(f"{self.kp_name} API returned response of {kp_response.status_code}. "
                                 f"Response from KP was: {kp_response.text}")
                return answer_kg
            else:
                json_response = kp_response.json()

        # Load the results into the object model
        if not json_response.get("message"):
            self.log.warning(f"{self.kp_name}: No 'message' was included in the response from {self.kp_name}. "
                             f"Response was: {json.dumps(json_response, indent=4)}")
            return answer_kg
        elif not json_response["message"].get("results"):
            self.log.debug(f"{self.kp_name}: No 'results' were returned.")
            json_response["message"]["results"] = []  # Setting this to empty list helps downstream processing
            return answer_kg
        else:
            self.log.debug(f"{self.kp_name}: Got results from {self.kp_name}.")
            # Temporarily convert any old attributes from KPs to new form (patch during 1.0 -> 1.1 transition)
            self._convert_trapi_1_0_kg_to_1_1(json_response["message"]["knowledge_graph"])
            kp_message = ARAXMessenger().from_dict(json_response["message"])

        # Build a map that indicates which qnodes/qedges a given node/edge fulfills
        kg_to_qg_mappings = self._get_kg_to_qg_mappings_from_results(kp_message.results)

        # Populate our final KG with the returned nodes and edges
        for returned_edge_key, returned_edge in kp_message.knowledge_graph.edges.items():
            arax_edge_key = self._get_arax_edge_key(returned_edge)  # Convert to an ID that's unique for us
            if not returned_edge.attributes:
                returned_edge.attributes = []
            returned_edge.attributes.append(Attribute(attribute_type_id="biolink:knowledge_provider_source",
                                                      value=eu.get_kp_infores_curie(self.kp_name),
                                                      value_type_id="biolink:InformationResource",
                                                      attribute_source="infores:arax_ara"))
            for qedge_key in kg_to_qg_mappings['edges'][returned_edge_key]:
                answer_kg.add_edge(arax_edge_key, returned_edge, qedge_key)
        for returned_node_key, returned_node in kp_message.knowledge_graph.nodes.items():
            for qnode_key in kg_to_qg_mappings['nodes'][returned_node_key]:
                answer_kg.add_node(returned_node_key, returned_node, qnode_key)

        return answer_kg

    def _answer_query_for_kps_who_dont_like_lists(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        TRAPI 1.0 says qnode.category and qedge.predicate can both be strings OR lists, but many KPs don't support
        them being lists. So this function pings such KPs one by one for each possible
        subj_category--predicate--obj_category combination.
        """
        qg_copy = eu.copy_qg(query_graph)  # Use a copy of the QG so we don't modify the original
        qnodes = qg_copy.nodes
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)
        qedge = qg_copy.edges[qedge_key]
        subject_categories = qnodes[qedge.subject].categories if qnodes[qedge.subject].categories else [None]
        object_categories = qnodes[qedge.object].categories if qnodes[qedge.object].categories else [None]
        predicates = qedge.predicates if qedge.predicates else [None]
        possible_triples = [(subject_category, predicate, object_category) for subject_category in subject_categories
                            for predicate in predicates for object_category in object_categories]
        answer_kg = QGOrganizedKnowledgeGraph()
        for possible_triple in possible_triples:
            current_subject_category = possible_triple[0]
            current_predicate = possible_triple[1]
            current_object_category = possible_triple[2]
            # Modify the QG so it's asking only for the current category--predicate--category triple
            qg_copy.nodes[qedge.subject].categories = current_subject_category
            qg_copy.nodes[qedge.object].categories = current_object_category
            qg_copy.edges[qedge_key].predicates = current_predicate
            self.log.debug(f"{self.kp_name}: Current triple is: {current_subject_category}--{current_predicate}--{current_object_category}")
            sub_kg = self._answer_query_using_kp(qg_copy)
            # Merge the answers for this triple into our answers received thus far
            answer_kg = eu.merge_two_kgs(sub_kg, answer_kg)

        return answer_kg

    @staticmethod
    def _strip_empty_properties(qnode_or_qedge: Union[QNode, QEdge]) -> Dict[str, any]:
        dict_version_of_object = qnode_or_qedge.to_dict()
        stripped_dict = {property_name: value for property_name, value in dict_version_of_object.items()
                         if dict_version_of_object.get(property_name) not in [None, []]}
        return stripped_dict

    def _get_arax_edge_key(self, edge: Edge) -> str:
        return f"{self.kp_name}:{edge.subject}-{edge.predicate}-{edge.object}"

    def _get_query_timeout_length(self, qg: QueryGraph) -> int:
        # Returns the number of seconds we should wait for a response based on the number of curies in the QG
        num_total_curies = sum([len(qnode.ids) for qnode in qg.nodes.values() if qnode.ids])
        if self.kp_name == "RTX-KG2":
            return 600
        elif self.user_specified_kp:  # This can be smaller since we don't send multi-curie queries to other KPs yet
            return 60
        elif num_total_curies < 10:
            return 15
        else:
            return 120

    @staticmethod
    def _switch_qg_to_trapi_1_0(dict_qg: Dict[str, Dict[str, any]]) -> Dict[str, Dict[str, any]]:
        # This is a temporary patch for use until we start using KPs' TRAPI 1.1 endpoints
        qnode_keys = set(dict_qg["nodes"])
        for qnode_key in qnode_keys:
            qnode = dict_qg["nodes"][qnode_key]
            if "ids" in qnode:
                qnode["id"] = qnode["ids"]
                del qnode["ids"]
            if "categories" in qnode:
                qnode["category"] = qnode["categories"]
                del qnode["categories"]
        qedge_keys = set(dict_qg["edges"])
        for qedge_key in qedge_keys:
            qedge = dict_qg["edges"][qedge_key]
            if "predicates" in qedge:
                qedge["predicate"] = qedge["predicates"]
                del qedge["predicates"]
        return dict_qg

    @staticmethod
    def _convert_old_attributes_to_new(attributes: List[Dict[str, any]]) -> List[Dict[str, any]]:
        # This is a temporary patch until we're using KPs' TRAPI 1.1 endpoints
        if attributes:
            for attribute in attributes:
                if not attribute.get("original_attribute_name"):
                    attribute["original_attribute_name"] = attribute.get("name")
                if not attribute.get("attribute_type_id"):
                    attribute["attribute_type_id"] = attribute.get("type")
        return attributes

    def _convert_trapi_1_0_kg_to_1_1(self, kg: Dict[str, Dict[str, any]]):
        # This is a temporary patch until we're using KPs' TRAPI 1.1 endpoints
        for node in kg["nodes"].values():
            if node.get("category"):
                node["categories"] = eu.convert_to_list(node["category"])
            if node.get("attributes"):
                node["attributes"] = self._convert_old_attributes_to_new(node["attributes"])
        for edge in kg["edges"].values():
            if edge.get("attributes"):
                edge["attributes"] = self._convert_old_attributes_to_new(edge["attributes"])
