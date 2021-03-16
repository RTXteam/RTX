#!/bin/env python3
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
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../Overlay/")
from Overlay.compute_ngd import ComputeNGD
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.message import Message


class NGDQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.ngd_edge_type = "biolink:has_normalized_google_distance_with"
        self.ngd_edge_attribute_name = "normalized_google_distance"
        self.ngd_edge_attribute_type = "EDAM:data_2526"
        self.ngd_edge_attribute_url = "https://arax.ncats.io/api/rtx/v1/ui/#/PubmedMeshNgd"

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using NGD (with the assistance of KG2).
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

        # Verify this is a valid one-hop query graph
        self._verify_one_hop_query_graph_is_valid(query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        # Find potential answers using KG2
        log.debug(f"Finding potential answers using KG2")
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]
        qedge_params_str = ", ".join(list(filter(None, [f"key={qedge_key}",
                                                        f"subject={source_qnode_key}",
                                                        f"object={target_qnode_key}",
                                                        self._get_dsl_qedge_type_str(qedge)])))
        source_params_str = ", ".join(list(filter(None, [f"key={source_qnode_key}",
                                                         self._get_dsl_qnode_curie_str(source_qnode),
                                                         self._get_dsl_qnode_category_str(source_qnode)])))
        target_params_str = ", ".join(list(filter(None, [f"key={target_qnode_key}",
                                                         self._get_dsl_qnode_curie_str(target_qnode),
                                                         self._get_dsl_qnode_category_str(target_qnode)])))
        actions_list = [
            f"add_qnode({source_params_str})",
            f"add_qnode({target_params_str})",
            f"add_qedge({qedge_params_str})",
            f"expand(kp=ARAX/KG2)",
            f"return(message=true, store=false)",
        ]
        kg2_response, kg2_message = self._run_arax_query(actions_list, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

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
                edge_to_nodes_map[ngd_edge_key] = {source_qnode_key: ngd_source_node_key,
                                                   target_qnode_key: ngd_target_node_key}

        return final_kg, edge_to_nodes_map

    def _create_ngd_edge(self, ngd_value: float, subject: str, object: str, pmid_list: list) -> Tuple[str, Edge]:
        ngd_edge = Edge()
        ngd_edge.predicate = self.ngd_edge_type
        ngd_edge.subject = subject
        ngd_edge.object = object
        ngd_edge_key = f"NGD:{subject}--{ngd_edge.predicate}--{object}"
        ngd_edge.attributes = [Attribute(name=self.ngd_edge_attribute_name,
                                         type=self.ngd_edge_attribute_type,
                                         value=ngd_value,
                                         url=self.ngd_edge_attribute_url)]
        ngd_edge.attributes += [Attribute(name="provided_by", value="ARAX", type=eu.get_attribute_type("provided_by")),
                                Attribute(name="is_defined_by", value="ARAX", type=eu.get_attribute_type("is_defined_by")),
                                Attribute(name="publications", value=pmid_list, type=eu.get_attribute_type("publications"))]
        return ngd_edge_key, ngd_edge

    @staticmethod
    def _create_ngd_node(kg2_node_key: str, kg2_node: Node) -> Tuple[str, Node]:
        ngd_node = Node()
        ngd_node_key = kg2_node_key
        ngd_node.name = kg2_node.name
        ngd_node.category = kg2_node.category
        return ngd_node_key, ngd_node

    @staticmethod
    def _run_arax_query(actions_list: List[str], log: ARAXResponse) -> Tuple[ARAXResponse, Message]:
        araxq = ARAXQuery()
        sub_query_response = araxq.query({"operations": {"actions": actions_list}})
        if sub_query_response.status != 'OK':
            log.error(f"Encountered an error running ARAXQuery within Expand: {sub_query_response.show(level=sub_query_response.DEBUG)}")
        return sub_query_response, araxq.message

    @staticmethod
    def _get_dsl_qnode_curie_str(qnode: QNode) -> str:
        curie_str = f"[{', '.join(qnode.id)}]" if isinstance(qnode.id, list) else qnode.id
        return f"id={curie_str}" if qnode.id else ""

    @staticmethod
    def _get_dsl_qnode_category_str(qnode: QNode) -> str:
        if len(qnode.category) == 0:
            return ""
        elif len(qnode.category) == 1:
            return f"category={qnode.category[0]}"
        else:
            return f"category=[{', '.join(qnode.category)}]"

    @staticmethod
    def _get_dsl_qedge_type_str(qedge: QEdge) -> str:
        if len(qedge.predicate) == 0:
            return ""
        elif len(qedge.predicate) == 1:
            return f"predicate={qedge.predicate[0]}"
        else:
            return f"predicate=[{', '.join(qedge.predicate)}]"

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
