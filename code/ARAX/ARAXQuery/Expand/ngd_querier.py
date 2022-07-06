#!/bin/env python3
import copy
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse
from ARAX_decorator import ARAXDecorator
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../Overlay/")
from Overlay.compute_ngd import ComputeNGD
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.message import Message


class NGDQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.ngd_edge_predicate = "biolink:has_normalized_google_distance_with"
        self.accepted_qedge_predicates = {"biolink:has_normalized_google_distance_with", "biolink:related_to"}
        self.ngd_edge_attribute_name = "normalized_google_distance"
        self.ngd_edge_attribute_type = "EDAM:data_2526"
        self.decorator = ARAXDecorator()

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using NGD (with the assistance of KG2).
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.response
        final_kg = QGOrganizedKnowledgeGraph()

        # Verify this is a valid one-hop query graph
        self._verify_one_hop_query_graph_is_valid(query_graph, log)
        if log.status != 'OK':
            return final_kg
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        qedge = query_graph.edges[qedge_key]
        if qedge.predicates and not set(qedge.predicates).intersection(self.accepted_qedge_predicates):
            log.error(f"NGD can only expand qedges with these predicates: {self.accepted_qedge_predicates}. QEdge"
                      f" {qedge_key}'s predicate is: {qedge.predicates}", error_code="UnsupportedQG")
            return final_kg
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object

        # Find potential answers using KG2
        log.debug(f"Finding potential answers using KG2")
        modified_qg = copy.deepcopy(query_graph)
        for qedge in modified_qg.edges.values():
            qedge.predicates = None

        request_body = {"message": {"query_graph": modified_qg.to_dict()}}
        kg2_response, kg2_message = self._run_arax_query(request_body, log)
        if log.status != 'OK':
            return final_kg

        # Go through those answers from KG2 and calculate ngd for each edge
        log.debug(f"Calculating NGD between each potential node pair")
        kg2_answer_kg = kg2_message.knowledge_graph
        cngd = ComputeNGD(log, kg2_message, None)
        cngd.load_curie_to_pmids_data(kg2_answer_kg.nodes)
        kg2_edge_ngd_map = dict()
        for kg2_edge_key, kg2_edge in kg2_answer_kg.edges.items():
            kg2_node_1_key = kg2_edge.subject
            kg2_node_2_key = kg2_edge.object
            kg2_node_1 = kg2_answer_kg.nodes.get(kg2_node_1_key)  # These are already canonicalized (default behavior)
            kg2_node_2 = kg2_answer_kg.nodes.get(kg2_node_2_key)
            # Figure out which node corresponds to source qnode (don't necessarily match b/c query was bidirectional)
            if source_qnode_key in kg2_node_1.qnode_keys and target_qnode_key in kg2_node_2.qnode_keys:
                ngd_subject = kg2_node_1_key
                ngd_object = kg2_node_2_key
            else:
                ngd_subject = kg2_node_2_key
                ngd_object = kg2_node_1_key
            ngd_value, pmid_set = cngd.calculate_ngd_fast(ngd_subject, ngd_object)
            kg2_edge_ngd_map[kg2_edge_key] = {"ngd_value": ngd_value, "subject": ngd_subject, "object": ngd_object, "pmids": [f"PMID:{pmid}" for pmid in pmid_set]}

        # Create edges for those from KG2 found to have a low enough ngd value
        threshold = 0.5
        log.debug(f"Creating edges between node pairs with NGD below the threshold ({threshold})")
        for kg2_edge_key, ngd_info_dict in kg2_edge_ngd_map.items():
            ngd_value = ngd_info_dict['ngd_value']
            if ngd_value is not None and ngd_value < threshold:  # TODO: Make determination of the threshold much more sophisticated
                subject = ngd_info_dict["subject"]
                object = ngd_info_dict["object"]
                pmid_list = ngd_info_dict["pmids"]
                ngd_edge_key, ngd_edge = self._create_ngd_edge(ngd_value, subject, object, pmid_list)
                ngd_source_node_key, ngd_source_node = self._create_ngd_node(ngd_edge.subject, kg2_answer_kg.nodes.get(ngd_edge.subject))
                ngd_target_node_key, ngd_target_node = self._create_ngd_node(ngd_edge.object, kg2_answer_kg.nodes.get(ngd_edge.object))
                final_kg.add_edge(ngd_edge_key, ngd_edge, qedge_key)
                final_kg.add_node(ngd_source_node_key, ngd_source_node, source_qnode_key)
                final_kg.add_node(ngd_target_node_key, ngd_target_node, target_qnode_key)

        return final_kg

    def _create_ngd_edge(self, ngd_value: float, subject: str, object: str, pmid_list: list) -> Tuple[str, Edge]:
        ngd_edge = Edge()
        ngd_edge.predicate = self.ngd_edge_predicate
        ngd_edge.subject = subject
        ngd_edge.object = object
        ngd_edge_key = f"NGD:{subject}--{ngd_edge.predicate}--{object}"
        ngd_edge.attributes = [Attribute(original_attribute_name=self.ngd_edge_attribute_name,
                                         attribute_type_id=self.ngd_edge_attribute_type,
                                         value=ngd_value)]
        kp_description = "ARAX's in-house normalized google distance database."
        ngd_edge.attributes += [self.decorator.create_attribute("publications", pmid_list),
                                eu.get_kp_source_attribute("infores:arax-normalized-google-distance", arax_kp=True, description=kp_description),
                                eu.get_arax_source_attribute(),
                                eu.get_computed_value_attribute()]
        return ngd_edge_key, ngd_edge

    @staticmethod
    def _create_ngd_node(kg2_node_key: str, kg2_node: Node) -> Tuple[str, Node]:
        ngd_node = Node()
        ngd_node_key = kg2_node_key
        ngd_node.name = kg2_node.name
        ngd_node.categories = kg2_node.categories
        return ngd_node_key, ngd_node

    @staticmethod
    def _run_arax_query(request_body: dict, log: ARAXResponse) -> Tuple[ARAXResponse, Message]:
        araxq = ARAXQuery()
        sub_query_response = araxq.query(request_body, mode="RTXKG2")
        if sub_query_response.status != 'OK':
            log.error(f"Encountered an error running ARAXQuery within Expand: {sub_query_response.show(level=sub_query_response.DEBUG)}")
        return sub_query_response, araxq.message

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
