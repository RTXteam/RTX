#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple, Set

import Expand.expand_utilities as eu
import requests
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.attribute import Attribute


class MoleProQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.kp_api_url = "https://translator.broadinstitute.org/molepro/trapi/v1.0/query"
        self.kp_name = "MolePro"
        # TODO: Eventually validate queries better based on info in future TRAPI knowledge_map endpoint
        self.accepted_node_categories = {"biolink:ChemicalSubstance", "biolink:Gene", "biolink:Disease"}
        self.accepted_edge_types = {"biolink:correlated_with"}
        self.node_category_overrides_for_kp = {"biolink:Protein": "biolink:Gene"}  # We'll call our proteins genes for MolePro queries
        self.kp_preferred_prefixes = {"biolink:ChemicalSubstance": "CHEMBL.COMPOUND", "biolink:Gene": "HGNC", "biolink:Disease": "MONDO"}

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using the Molecular Provider.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_keys for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.response
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Verify this is a valid one-hop query graph and tweak its contents as needed for this KP
        self._verify_one_hop_query_graph_is_valid(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        modified_query_graph = self._pre_process_query_graph(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        qedge = next(qedge for qedge in modified_query_graph.edges.values())
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object

        # Answer the query using the KP and load its answers into our Swagger model
        json_response = self._send_query_to_kp(modified_query_graph, log)
        returned_kg = json_response.get('knowledge_graph')
        if not returned_kg:
            log.warning(f"No KG is present in the response from {self.kp_name}")
        else:
            # Build a map of node/edge IDs to qnode/qedge IDs
            qg_id_mappings = self._get_qg_id_mappings_from_results(json_response['results'])
            # Populate our final KG with nodes and edges
            for returned_edge_key, returned_edge in returned_kg['edges'].items():
                kp_edge_key, swagger_edge = self._create_swagger_edge_from_kp_edge(returned_edge_key, returned_edge)
                swagger_edge_key = self._create_unique_edge_key(swagger_edge)  # Convert to an ID that's unique for us
                for qedge_key in qg_id_mappings['edges'][kp_edge_key]:
                    final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                edge_to_nodes_map[swagger_edge_key] = {source_qnode_key: swagger_edge.subject,
                                                       target_qnode_key: swagger_edge.object}
            for returned_node_key, returned_node in returned_kg['nodes'].items():
                swagger_node_key, swagger_node = self._create_swagger_node_from_kp_node(returned_node_key, returned_node)
                for qnode_key in qg_id_mappings['nodes'][swagger_node_key]:
                    final_kg.add_node(swagger_node_key, swagger_node, qnode_key)

        return final_kg, edge_to_nodes_map

    @staticmethod
    def _verify_one_hop_query_graph_is_valid(query_graph: QueryGraph, log: ARAXResponse):
        if len(query_graph.edges) != 1:
            log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) > 2:
            log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) < 2:
            log.error(f"answer_one_hop_query() was passed a query graph with less than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _pre_process_query_graph(self, query_graph: QueryGraph, log: ARAXResponse) -> QueryGraph:
        for qnode_key, qnode in query_graph.nodes.items():
            # Convert node types to preferred format and verify we can do this query
            formatted_qnode_categories = {self.node_category_overrides_for_kp.get(qnode_category, qnode_category) for qnode_category in eu.convert_string_or_list_to_list(qnode.category)}
            accepted_qnode_categories = formatted_qnode_categories.intersection(self.accepted_node_categories)
            if not accepted_qnode_categories:
                log.error(f"{self.kp_name} can only be used for queries involving {self.accepted_node_categories} "
                          f"and QNode {qnode_key} has type '{qnode.category}'", error_code="UnsupportedQueryForKP")
                return query_graph
            else:
                qnode.category = list(accepted_qnode_categories)[0]
            # Convert curies to equivalent curies accepted by the KP (depending on qnode type)
            if qnode.id:
                equivalent_curies = eu.get_curie_synonyms(qnode.id, log)
                desired_curies = [curie for curie in equivalent_curies if curie.startswith(f"{self.kp_preferred_prefixes[qnode.category]}:")]
                if desired_curies:
                    qnode.id = desired_curies if len(desired_curies) > 1 else desired_curies[0]
                    log.debug(f"Converted qnode {qnode_key} curie to {qnode.id}")
                else:
                    log.warning(f"Could not convert qnode {qnode_key} curie(s) to preferred prefix ({self.kp_preferred_prefixes[qnode.category]})")
        return query_graph

    @staticmethod
    def _get_qg_id_mappings_from_results(results: [any]) -> Dict[str, Dict[str, Set[str]]]:
        # Builds a dictionary of node_keys/edge_keys to their lists of qnode_keys/qedge_keys
        qnode_key_mappings = dict()
        qedge_key_mappings = dict()
        for result in results:
            for qnode_key, node_bindings in result['node_bindings'].items():
                kg_ids = {node_binding['id'] for node_binding in node_bindings}
                for kg_id in kg_ids:
                    if kg_id not in qnode_key_mappings:
                        qnode_key_mappings[kg_id] = set()
                    qnode_key_mappings[kg_id].add(qnode_key)
            for qedge_key, edge_bindings in result['edge_bindings'].items():
                kg_ids = {edge_binding['id'] for edge_binding in edge_bindings}
                for kg_id in kg_ids:
                    if kg_id not in qedge_key_mappings:
                        qedge_key_mappings[kg_id] = set()
                    qedge_key_mappings[kg_id].add(qedge_key)
        return {"nodes": qnode_key_mappings, "edges": qedge_key_mappings}

    def _send_query_to_kp(self, query_graph: QueryGraph, log: ARAXResponse) -> Dict[str, any]:
        # Send query to their API (stripping down qnode/qedges to only the properties they like)
        stripped_qnodes = dict()
        for qnode_key, qnode in query_graph.nodes.items():
            stripped_qnode = {'category': qnode.category}
            if qnode.id:
                stripped_qnode['id'] = qnode.id
            stripped_qnodes[qnode_key] = stripped_qnode
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)  # Our query graph is single-edge
        qedge = query_graph.edges[qedge_key]
        stripped_qedge = {'subject': qedge.subject,
                          'object': qedge.object,
                          'predicate': qedge.predicate if qedge.predicate else list(self.accepted_edge_types)[0]}
        if stripped_qedge['predicate'] not in self.accepted_edge_types:
            log.warning(f"{self.kp_name} only accepts the following edge types: {self.accepted_edge_types}")
        source_stripped_qnode = stripped_qnodes[qedge.subject]
        input_curies = eu.convert_string_or_list_to_list(source_stripped_qnode['id'])
        combined_message = dict()
        for input_curie in input_curies:  # Until we have batch querying, ping them one-by-one for each input curie
            log.debug(f"Sending {qedge_key} query to {self.kp_name} for {input_curie}")
            source_stripped_qnode['id'] = input_curie
            kp_response = requests.post(self.kp_api_url,
                                        json={'message': {'query_graph': {'nodes': stripped_qnodes, 'edges': {qedge_key: stripped_qedge}}}},
                                        headers={'accept': 'application/json'})
            if kp_response.status_code != 200:
                log.warning(f"{self.kp_name} KP API returned response of {kp_response.status_code}: {kp_response.text}")
            else:
                kp_response_json = kp_response.json()
                kp_message = kp_response_json["message"]
                if kp_message.get('results'):
                    if not combined_message:
                        combined_message = kp_message
                    else:
                        combined_message['knowledge_graph']['nodes'].update(kp_message['knowledge_graph']['nodes'])
                        combined_message['knowledge_graph']['edges'].update(kp_message['knowledge_graph']['edges'])
                        combined_message['results'] += kp_message['results']
        return combined_message

    def _create_swagger_edge_from_kp_edge(self, kp_edge_key: str, kp_edge: Dict[str, any]) -> Edge:
        swagger_edge = Edge(subject=kp_edge['subject'],
                            object=kp_edge['object'],
                            predicate=kp_edge['predicate'])
        swagger_edge.attributes = [Attribute(name="provided_by", value=self.kp_name, type=eu.get_attribute_type("provided_by")),
                                   Attribute(name="is_defined_by", value="ARAX", type=eu.get_attribute_type("is_defined_by"))]
        return kp_edge_key, swagger_edge

    @staticmethod
    def _create_swagger_node_from_kp_node(kp_node_key: str, kp_node: Dict[str, any]) -> Tuple[str, Node]:
        return kp_node_key, Node(category=kp_node['category'],
                                 name=kp_node.get('name'))

    def _create_unique_edge_key(self, swagger_edge: Edge) -> str:
        return f"{self.kp_name}:{swagger_edge.subject}-{swagger_edge.predicate}-{swagger_edge.object}"
