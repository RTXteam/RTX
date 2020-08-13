#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple

import Expand.expand_utilities as eu
from Expand.expand_utilities import DictKnowledgeGraph
from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_query import ARAXQuery
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../Overlay/")
from Overlay.compute_ngd import ComputeNGD
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge


class NGDQuerier:

    def __init__(self, response_object: Response):
        self.response = response_object
        self.cngd = ComputeNGD(self.response, None, None)
        self.ngd_edge_type = "has_normalized_google_distance_with"
        self.ngd_edge_attribute_name = "normalized_google_distance"
        self.ngd_edge_attribute_type = "EDAM:data_2526"
        self.ngd_edge_attribute_url = "https://arax.rtx.ai/api/rtx/v1/ui/#/PubmedMeshNgd"

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using NGD (with the assistance of KG2).
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_ids for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.response
        continue_if_no_results = self.response.data['parameters']['continue_if_no_results']
        final_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Verify this is a valid one-hop query graph
        self._verify_one_hop_query_graph_is_valid(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        # Find potential answers using KG2
        qedge = query_graph.edges[0]
        source_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.source_id)
        target_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.target_id)
        qedge_params_str = ", ".join(list(filter(None, [f"id={qedge.id}",
                                                        f"source_id={source_qnode.id}",
                                                        f"target_id={target_qnode.id}",
                                                        self._get_dsl_qedge_type_str(qedge)])))
        source_params_str = ", ".join(list(filter(None, [f"id={source_qnode.id}",
                                                         self._get_dsl_qnode_curie_str(source_qnode),
                                                         self._get_dsl_qnode_type_str(source_qnode)])))
        target_params_str = ", ".join(list(filter(None, [f"id={target_qnode.id}",
                                                         self._get_dsl_qnode_curie_str(target_qnode),
                                                         self._get_dsl_qnode_type_str(target_qnode)])))
        actions_list = [
            f"add_qnode({source_params_str})",
            f"add_qnode({target_params_str})",
            f"add_qedge({qedge_params_str})",
            f"expand(kp=ARAX/KG2)",
            f"return(message=true, store=false)",
        ]
        kg2_answer_kg = self._run_arax_query(actions_list, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        # Go through those answers from KG2 and calculate ngd for each edge
        kg2_edges_map = {edge.id: edge for edge in kg2_answer_kg.edges}
        kg2_nodes_map = {node.id: node for node in kg2_answer_kg.nodes}
        kg2_edge_ngd_map = dict()
        for kg2_edge in kg2_edges_map.values():
            kg2_node_1 = kg2_nodes_map.get(kg2_edge.source_id)  # These are already canonicalized (default behavior)
            kg2_node_2 = kg2_nodes_map.get(kg2_edge.target_id)
            # Figure out which node corresponds to source qnode (don't necessarily match b/c query was bidirectional)
            if source_qnode.id in kg2_node_1.qnode_ids and target_qnode.id in kg2_node_2.qnode_ids:
                ngd_source_id = kg2_node_1.id
                ngd_target_id = kg2_node_2.id
            else:
                ngd_source_id = kg2_node_2.id
                ngd_target_id = kg2_node_1.id
            ngd_value = self.cngd.calculate_ngd_fast(ngd_source_id, ngd_target_id)
            kg2_edge_ngd_map[kg2_edge.id] = {"ngd_value": ngd_value, "source_id": ngd_source_id, "target_id": ngd_target_id}

        # Create edges for those from KG2 found to have a low enough ngd value
        for kg2_edge_id, ngd_info_dict in kg2_edge_ngd_map.items():
            ngd_value = ngd_info_dict['ngd_value']
            if ngd_value is not None and ngd_value < 0.5:  # TODO: Make determination of the threshold much more sophisticated
                source_id = ngd_info_dict["source_id"]
                target_id = ngd_info_dict["target_id"]
                ngd_edge = self._create_ngd_edge(ngd_value, source_id, target_id)
                ngd_source_node = self._create_ngd_node(kg2_nodes_map.get(ngd_edge.source_id))
                ngd_target_node = self._create_ngd_node(kg2_nodes_map.get(ngd_edge.target_id))
                final_kg.add_edge(ngd_edge, qedge.id)
                final_kg.add_node(ngd_source_node, source_qnode.id)
                final_kg.add_node(ngd_target_node, target_qnode.id)
                edge_to_nodes_map[ngd_edge.id] = {source_qnode.id: ngd_source_node.id,
                                                  target_qnode.id: ngd_target_node.id}

        if not eu.qg_is_fulfilled(query_graph, final_kg):
            if continue_if_no_results:
                log.warning(f"No paths were found satisfying this query graph using NGD")
            else:
                log.error(f"No paths were found satisfying this query graph using NGD", error_code="NoResults")

        return final_kg, edge_to_nodes_map

    def _create_ngd_edge(self, ngd_value: float, source_id: str, target_id: str) -> Edge:
        ngd_edge = Edge()
        ngd_edge.type = self.ngd_edge_type
        ngd_edge.source_id = source_id
        ngd_edge.target_id = target_id
        ngd_edge.id = f"NGD:{source_id}--{ngd_edge.type}--{target_id}"
        ngd_edge.provided_by = "ARAX"
        ngd_edge.is_defined_by = "ARAX"
        ngd_edge.edge_attributes = [EdgeAttribute(name=self.ngd_edge_attribute_name,
                                                  type=self.ngd_edge_attribute_type,
                                                  value=ngd_value,
                                                  url=self.ngd_edge_attribute_url)]
        return ngd_edge

    @staticmethod
    def _create_ngd_node(kg2_node: Node) -> Node:
        ngd_node = Node()
        ngd_node.id = kg2_node.id
        ngd_node.name = kg2_node.name
        ngd_node.type = kg2_node.type
        return ngd_node

    @staticmethod
    def _run_arax_query(actions_list: List[str], log: Response) -> DictKnowledgeGraph:
        araxq = ARAXQuery()
        sub_query_response = araxq.query({"previous_message_processing_plan": {"processing_actions": actions_list}})
        if sub_query_response.status != 'OK':
            log.error(f"Encountered an error running ARAXQuery within Expand: {sub_query_response.show(level=sub_query_response.DEBUG)}")
            return dict()
        sub_query_message = araxq.message
        return sub_query_message.knowledge_graph

    @staticmethod
    def _get_dsl_qnode_curie_str(qnode: QNode) -> str:
        curie_str = f"[{', '.join(qnode.curie)}]" if isinstance(qnode.curie, list) else qnode.curie
        return f"curie={curie_str}" if qnode.curie else ""

    @staticmethod
    def _get_dsl_qnode_type_str(qnode: QNode) -> str:
        # Use only the first type if there are multiple (which ARAXExpander adds for cases like "gene"/"protein")
        type_str = qnode.type[0] if isinstance(qnode.type, list) else qnode.type
        return f"type={type_str}" if qnode.type else ""

    @staticmethod
    def _get_dsl_qedge_type_str(qedge: QEdge) -> str:
        return f"type={qedge.type}" if qedge.type else ""

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
