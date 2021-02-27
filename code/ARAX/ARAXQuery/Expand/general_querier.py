#!/bin/env python3
import sys
import os
from typing import List, Dict, Tuple, Set, Union

import Expand.expand_utilities as eu
import requests
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.message import Message
from openapi_server.models.result import Result


class GeneralQuerier:

    def __init__(self, response_object: ARAXResponse, kp_name: str):
        self.log = response_object
        self.kp_name = kp_name
        self.kp_endpoint = f"{eu.get_kp_endpoint_url(kp_name)}"
        self.node_category_overrides_for_kp = eu.get_node_category_overrides_for_kp(kp_name)
        self.kp_preferred_prefixes = eu.get_kp_preferred_prefixes(kp_name)

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

        # Verify this query graph is valid and will work for this KP
        self._verify_is_one_hop_query_graph(query_graph)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        if self.node_category_overrides_for_kp:
            query_graph = self._override_qnode_types_as_needed(query_graph)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        # Convert curies to the prefixes that this KP prefers (if we know that info)
        if self.kp_preferred_prefixes:
            query_graph = self._convert_to_accepted_curies(query_graph)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        qedge = next(qedge for qedge in query_graph.edges.values())

        # Answer the query using the KP and load its answers into our Swagger model
        json_response = self._send_query_to_kp(query_graph)
        if json_response['message'].get('knowledge_graph') is None:
            log.warning(f"'knowledge_graph' is missing in the message returned from {self.kp_name}")
        else:
            returned_message = Message().from_dict(json_response['message'])
            print(returned_message.results)  # TODO: Why does this print but then is empty in next line??
            # Build a map that indicates which qnodes/qedges a given node/edge fulfills
            qg_id_mappings = self._get_qg_id_mappings_from_results(returned_message.results)

            # Populate our final KG with the returned nodes and edges
            for returned_edge_key, returned_edge in returned_message.knowledge_graph.edges.items():
                arax_edge_key = self._get_arax_edge_key(returned_edge)  # Convert to an ID that's unique for us
                for qedge_key in qg_id_mappings['edges'][returned_edge_key]:
                    final_kg.add_edge(arax_edge_key, returned_edge, qedge_key)
            for returned_node_key, returned_node in returned_message.knowledge_graph.nodes.items():
                for qnode_key in qg_id_mappings['nodes'][returned_node_key]:
                    final_kg.add_node(returned_node_key, returned_node, qnode_key)
            # Build a map that indicates which of an edge's nodes fulfill which qnode
            edge_to_nodes_map = self._create_edge_to_nodes_map(qg_id_mappings, returned_message.knowledge_graph, qedge)

        return final_kg, edge_to_nodes_map

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

    def _override_qnode_types_as_needed(self, query_graph: QueryGraph) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            overriden_categories = {self.node_category_overrides_for_kp.get(qnode_category, qnode_category)
                                    for qnode_category in eu.convert_string_or_list_to_list(qnode.category)}
            qnode.category = list(overriden_categories)[0] if len(overriden_categories) == 1 else list(overriden_categories)
        return query_graph

    def _verify_qg_is_accepted_by_kp(self, query_graph: QueryGraph):
        # TODO: Make this work for "None" categories, move to somewhere else? (where Expand decides what KP to use?)
        kp_predicates_response = requests.get(f"{self.kp_endpoint}/predicates", headers={'accept': 'application/json'})
        if kp_predicates_response.status_code != 200:
            self.log.warning(f"Unable to access {self.kp_name}'s predicates endpoint "
                             f"(returned status of {kp_predicates_response.status_code})")
        else:
            predicates_dict = kp_predicates_response.json()
            qnodes = query_graph.nodes
            triples = [[qnodes[qedge.subject].category, qedge.predicate, qnodes[qedge.object].category]
                       for qedge in query_graph.edges.values()]
            for triple in triples:
                subject_category = triple[0]
                object_category = triple[1]
                predicate = triple[2]
                if subject_category not in predicates_dict:
                    self.log.error(f"{self.kp_name} cannot answer queries with {subject_category} as subject. Supported"
                                   f" subject categories are: {list(predicates_dict)}", error_code="UnsupportedQueryForKP")
                elif object_category not in predicates_dict[subject_category]:
                    self.log.error(f"{self.kp_name} cannot answer queries from {subject_category} to {object_category}."
                                   f"Supported object categories for a subject of {subject_category} are "
                                   f"{list(predicates_dict[subject_category])}", error_code="UnsupportedQueryForKP")
                elif predicate not in predicates_dict[subject_category][object_category]:
                    self.log.error(f"For {subject_category}--{object_category} qedges, {self.kp_name} doesn't support "
                                   f"a predicate of '{predicate}'. Supported predicates are: {predicates_dict[subject_category][object_category]}",
                                   error_code="UnsupportedQueryForKP")

    def _convert_to_accepted_curies(self, query_graph: QueryGraph) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            if qnode.id:
                equivalent_curies = eu.get_curie_synonyms(qnode.id, self.log)
                preferred_prefix = self.kp_preferred_prefixes[qnode.category]
                desired_curies = [curie for curie in equivalent_curies if curie.startswith(f"{preferred_prefix}:")]
                if desired_curies:
                    qnode.id = desired_curies if len(desired_curies) > 1 else desired_curies[0]
                    self.log.debug(f"Converted qnode {qnode_key} curie to {qnode.id}")
                else:
                    self.log.warning(f"Could not convert qnode {qnode_key} curie(s) to preferred prefix "
                                     f"({self.kp_preferred_prefixes[qnode.category]})")
        return query_graph

    @staticmethod
    def _get_qg_id_mappings_from_results(results: List[Result]) -> Dict[str, Dict[str, Set[str]]]:
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

    def _create_edge_to_nodes_map(self, qg_id_mappings: Dict[str, Dict[str, Set[str]]], kg: KnowledgeGraph, qedge: QEdge) -> Dict[str, Dict[str, str]]:
        """
        This function creates an 'edge_to_nodes_map' that indicates which of an edge's nodes (subject or object) is
        fulfilling which qnode ID (since edge.subject does not necessarily fulfill qedge.subject).
        Example: {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        edge_to_nodes_map = dict()
        kg_node_to_qnode_mappings = qg_id_mappings["nodes"]
        for edge_key, edge in kg.edges.items():
            arax_edge_key = self._get_arax_edge_key(edge)  # We use edge keys guaranteed to be unique across KPs
            if qedge.subject in kg_node_to_qnode_mappings[edge.subject] and qedge.object in kg_node_to_qnode_mappings[edge.object]:
                edge_to_nodes_map[arax_edge_key] = {qedge.subject: edge.subject, qedge.object: edge.object}
            else:
                edge_to_nodes_map[arax_edge_key] = {qedge.subject: edge.object, qedge.object: edge.subject}
        return edge_to_nodes_map

    def _send_query_to_kp(self, query_graph: QueryGraph) -> Union[Dict[str, any], None]:
        # Strip non-essential and 'empty' properties off of our qnodes and qedges
        stripped_qnodes = {qnode_key: self._strip_empty_properties(qnode)
                           for qnode_key, qnode in query_graph.nodes.items()}
        stripped_qedges = {qedge_key: self._strip_empty_properties(qedge)
                           for qedge_key, qedge in query_graph.edges.items()}

        # Send the query to the KP's API
        kp_response = requests.post(f"{self.kp_endpoint}/query",
                                    json={'message': {'query_graph': {'nodes': stripped_qnodes, 'edges': stripped_qedges}}},
                                    headers={'accept': 'application/json'})
        if kp_response.status_code == 200:
            return kp_response.json()
        else:
            self.log.warning(f"{self.kp_name} KP API returned response of {kp_response.status_code}: {kp_response.text}")
            return None

    @staticmethod
    def _strip_empty_properties(qnode_or_qedge: Union[QNode, QEdge]) -> Dict[str, any]:
        dict_version_of_object = qnode_or_qedge.to_dict()
        stripped_dict = {property_name: value for property_name, value in dict_version_of_object.items()
                         if dict_version_of_object.get(property_name) is not None}
        return stripped_dict

    @staticmethod
    def _create_swagger_node_from_kp_node(kp_node_key: str, kp_node: Dict[str, any]) -> Tuple[str, Node]:
        return kp_node_key, Node(category=kp_node['category'],
                                 name=kp_node.get('name'))

    def _get_arax_edge_key(self, edge: Edge) -> str:
        return f"{self.kp_name}:{edge.subject}-{edge.predicate}-{edge.object}"
