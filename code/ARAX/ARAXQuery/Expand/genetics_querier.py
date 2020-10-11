#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple, Set

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import DictKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from response import Response
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.query_graph import QueryGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class GeneticsQuerier:

    def __init__(self, response_object: Response):
        self.response = response_object
        self.genetics_kp_api_url = "https://translator.broadinstitute.org/genetics_data_provider/query"
        self.magma_score_name = "MAGMA-pvalue"
        self.quantile_score_name = "Genetics-quantile"
        self.score_type_lookup = {self.magma_score_name: "EDAM:data_1669",
                                  self.quantile_score_name: "?"}  # TODO
        self.accepted_node_types = {"gene", "pathway", "phenotypic_feature", "disease"}
        self.node_type_remappings = {"protein": "gene"}
        self.prefix_mappings = {"gene": "NCBIGene", "pathway": "GO", "phenotypic_feature": "EFO", "disease": "EFO"}

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using the Genetics Provider.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_ids for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.response
        continue_if_no_results = self.response.data['parameters']['continue_if_no_results']
        include_integrated_score = self.response.data['parameters']['include_integrated_score']
        final_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Verify this is a valid one-hop query graph and tweak its contents as needed for this KP
        self._verify_one_hop_query_graph_is_valid(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        modified_query_graph = self._pre_process_query_graph(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        qedge = modified_query_graph.edges[0]
        source_qnode_id = qedge.source_id
        target_qnode_id = qedge.target_id

        # Answer the query using the KP and load its answers into our Swagger model
        json_response = self._send_query_to_genetics_kp(modified_query_graph, log)
        returned_kg = json_response.get('knowledge_graph')
        if not returned_kg:
            log.warning(f"Genetics KP didn't error out, but no KG is in the response")
        else:
            # Build a map of node/edge IDs to qnode/qedge IDs
            qg_id_mappings = self._get_qg_id_mappings_from_results(json_response['results'])
            # Populate our final KG with nodes and edges
            for returned_edge in returned_kg['edges']:
                if include_integrated_score or returned_edge['score_name'] == self.magma_score_name:
                    swagger_edge = self._create_swagger_edge_from_kp_edge(returned_edge)
                    for qedge_id in qg_id_mappings['edges'][swagger_edge.id]:
                        final_kg.add_edge(swagger_edge, qedge_id)
                    edge_to_nodes_map[swagger_edge.id] = {source_qnode_id: swagger_edge.source_id,
                                                          target_qnode_id: swagger_edge.target_id}
            for returned_node in returned_kg['nodes']:
                swagger_node = self._create_swagger_node_from_kp_node(returned_node)
                for qnode_id in qg_id_mappings['nodes'][swagger_node.id]:
                    final_kg.add_node(swagger_node, qnode_id)

        if not eu.qg_is_fulfilled(query_graph, final_kg):
            if continue_if_no_results:
                log.warning(f"No paths were found satisfying this query graph in Genetics KP")
            else:
                log.error(f"No paths were found satisfying this query graph in Genetics KP", error_code="NoResults")

        return final_kg, edge_to_nodes_map

    @staticmethod
    def _verify_one_hop_query_graph_is_valid(query_graph: QueryGraph, log: Response):
        if len(query_graph.edges) != 1:
            log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) > 2:
            log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) < 2:
            log.error(f"answer_one_hop_query() was passed a query graph with less than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _pre_process_query_graph(self, query_graph: QueryGraph, log: Response) -> QueryGraph:
        for qnode in query_graph.nodes:
            # Convert node types to preferred format and verify we can do this query
            formatted_qnode_types = {self.node_type_remappings.get(qnode_type, qnode_type) for qnode_type in eu.convert_string_or_list_to_list(qnode.type)}
            accepted_qnode_types = formatted_qnode_types.intersection(self.accepted_node_types)
            if not accepted_qnode_types:
                log.error(f"Can't answer this query using the Genetics Provider; unaccepted type for QNode {qnode.id}", error_code="UnsupportedQueryForKP")
                return query_graph
            else:
                qnode.type = list(accepted_qnode_types)[0]
            # Convert curies to equivalent curies accepted by the KP (depending on qnode type)
            if qnode.curie:
                synonymizer = NodeSynonymizer()
                converted_curies = synonymizer.convert_curie(qnode.curie, self.prefix_mappings[qnode.type])
                if converted_curies:
                    qnode.curie = converted_curies[0]
                    log.debug(f"Converted qnode {qnode.id} curie to {qnode.curie}")
                else:
                    log.warning(f"Could not convert qnode {qnode.id} curie to preferred prefix ({self.prefix_mappings[qnode.type]})")
        return query_graph

    @staticmethod
    def _get_qg_id_mappings_from_results(results: [any]) -> Dict[str, Dict[str, Set[str]]]:
        qnode_id_mappings = dict()
        qedge_id_mappings = dict()
        for result in results:
            for node_binding in result['node_bindings']:
                qg_id = node_binding['qg_id']
                kg_id = node_binding['kg_id']
                if kg_id in qnode_id_mappings:
                    qnode_id_mappings[kg_id].add(qg_id)
                else:
                    qnode_id_mappings[kg_id] = {qg_id}
            for edge_binding in result['edge_bindings']:
                qg_id = edge_binding['qg_id']
                kg_id = edge_binding['kg_id']
                if kg_id in qedge_id_mappings:
                    qedge_id_mappings[kg_id].add(qg_id)
                else:
                    qedge_id_mappings[kg_id] = {qg_id}
        return {"nodes": qnode_id_mappings, "edges": qedge_id_mappings}

    def _send_query_to_genetics_kp(self, query_graph: QueryGraph, log: Response) -> Dict[str, any]:
        # Send query to their API (stripping down qnode/qedges to only the properties they like)
        stripped_qnodes = []
        for qnode in query_graph.nodes:
            stripped_qnode = {'id': qnode.id, 'type': qnode.type}
            if qnode.curie:
                stripped_qnode['curie'] = qnode.curie
            stripped_qnodes.append(stripped_qnode)
        stripped_qedges = [{'id': qedge.id, 'source_id': qedge.source_id, 'target_id': qedge.target_id, 'type': 'associated'}
                           for qedge in query_graph.edges]
        kp_response = requests.post(self.genetics_kp_api_url,
                                    json={'message': {'query_graph': {'nodes': stripped_qnodes, 'edges': stripped_qedges}}},
                                    headers={'accept': 'application/json'})
        if kp_response.status_code != 200:
            log.warning(f"Genetics KP API returned response of {kp_response.status_code}")
            return dict()
        else:
            return kp_response.json()

    def _create_swagger_edge_from_kp_edge(self, kp_edge: Dict[str, any]) -> Edge:
        score_name = kp_edge['score_name']
        swagger_edge = Edge(id=kp_edge['id'],
                            source_id=kp_edge['source_id'],
                            target_id=kp_edge['target_id'],
                            type=kp_edge['type'],
                            provided_by='Genetics KP',
                            is_defined_by='ARAX',
                            edge_attributes=[EdgeAttribute(name=score_name,
                                                           type=self.score_type_lookup[score_name],
                                                           value=kp_edge['score'])])
        return swagger_edge

    @staticmethod
    def _create_swagger_node_from_kp_node(kp_node: Dict[str, any]) -> Node:
        return Node(id=kp_node['id'],
                    type=kp_node['type'])
