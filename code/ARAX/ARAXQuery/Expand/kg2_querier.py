#!/bin/env python3
import sys
import os
import time
from typing import Dict, Tuple, Union

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # ARAX directory
from biolink_helper import BiolinkHelper
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph


class KG2Querier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.enforce_directionality = self.response.data['parameters'].get('enforce_directionality')
        self.biolink_helper = BiolinkHelper()
        self.kg2_infores_curie = eu.get_translator_infores_curie("RTX-KG2")

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using KG2c, via PloverDB.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.response
        final_kg = QGOrganizedKnowledgeGraph()

        # Verify this is a valid one-hop query graph
        if len(query_graph.edges) != 1:
            log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg
        if len(query_graph.nodes) != 2:
            log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg

        # Get canonical versions of the input curies
        qnode_keys_with_curies = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.ids]
        for qnode_key in qnode_keys_with_curies:
            qnode = query_graph.nodes[qnode_key]
            canonical_curies = eu.get_canonical_curies_list(qnode.ids, log)
            log.debug(f"Using {len(canonical_curies)} curies as canonical curies for qnode {qnode_key}")
            qnode.ids = canonical_curies
            qnode.categories = None  # Important to clear this, otherwise results are limited (#889)

        # Send request to Plover
        plover_answer, response_status = self._answer_query_using_plover(query_graph, log)
        if response_status == 200:
            final_kg = self._load_plover_answer_into_object_model(plover_answer, log)
        else:
            log.error(f"Plover returned response of {response_status}. Answer was: {plover_answer}", error_code="RequestFailed")

        return final_kg

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        log = self.response
        qnode_key = next(qnode_key for qnode_key in single_node_qg.nodes)
        qnode = single_node_qg.nodes[qnode_key]
        final_kg = QGOrganizedKnowledgeGraph()

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        if qnode.ids:
            qnode.ids = eu.get_canonical_curies_list(qnode.ids, log)
            qnode.categories = None  # Important to clear this to avoid discrepancies in types for particular concepts

        # Send request to plover
        plover_answer, response_status = self._answer_query_using_plover(single_node_qg, log)
        if response_status == 200:
            final_kg = self._load_plover_answer_into_object_model(plover_answer, log)
        else:
            log.error(f"Plover returned response of {response_status}. Answer was: {plover_answer}", error_code="RequestFailed")

        return final_kg

    @staticmethod
    def _answer_query_using_plover(qg: QueryGraph, log: ARAXResponse) -> Tuple[Dict[str, Dict[str, Union[set, dict]]], int]:
        rtxc = RTXConfiguration()
        rtxc.live = "Production"
        log.debug(f"Sending query to Plover")
        dict_qg = qg.to_dict()
        dict_qg["include_metadata"] = True  # Ask plover to return node/edge objects (not just IDs)
        # Allow subclass_of reasoning for qnodes with a small number of curies
        for qnode in dict_qg["nodes"].values():
            if qnode.get("ids") and len(qnode["ids"]) < 5:
                if "allow_subclasses" not in qnode or qnode["allow_subclasses"] is None:
                    qnode["allow_subclasses"] = True
        response = requests.post(f"{rtxc.plover_url}/query", json=dict_qg, timeout=60,
                                 headers={'accept': 'application/json'})
        if response.status_code == 200:
            log.debug(f"Got response back from Plover")
            return response.json(), response.status_code
        else:
            log.warning(f"Plover returned a status code of {response.status_code}. Response was: {response.text}")
            return dict(), response.status_code

    def _load_plover_answer_into_object_model(self, plover_answer: Dict[str, Dict[str, Union[set, dict]]],
                                              log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        answer_kg = QGOrganizedKnowledgeGraph()
        # Load returned nodes into TRAPI object model
        for qnode_key, nodes in plover_answer["nodes"].items():
            num_nodes = len(nodes)
            log.debug(f"Loading {num_nodes} {qnode_key} nodes into TRAPI object model")
            start = time.time()
            for node_key, node_tuple in nodes.items():
                node = self._convert_kg2c_plover_node_to_trapi_node(node_tuple)
                answer_kg.add_node(node_key, node, qnode_key)
            log.debug(f"Loading {num_nodes} {qnode_key} nodes into TRAPI object model took "
                      f"{round(time.time() - start, 2)} seconds")
        # Load returned edges into TRAPI object model
        for qedge_key, edges in plover_answer["edges"].items():
            num_edges = len(edges)
            log.debug(f"Loading {num_edges} edges into TRAPI object model")
            start = time.time()
            for edge_key, edge_tuple in edges.items():
                edge = self._convert_kg2c_plover_edge_to_trapi_edge(edge_tuple)
                answer_kg.add_edge(edge_key, edge, qedge_key)
            log.debug(f"Loading {num_edges} {qedge_key} edges into TRAPI object model took "
                      f"{round(time.time() - start, 2)} seconds")
        return answer_kg

    @staticmethod
    def _convert_kg2c_plover_node_to_trapi_node(node_tuple: list) -> Node:
        node = Node(name=node_tuple[0], categories=eu.convert_to_list(node_tuple[1]))
        return node

    def _convert_kg2c_plover_edge_to_trapi_edge(self, edge_tuple: list) -> Edge:
        edge = Edge(subject=edge_tuple[0], object=edge_tuple[1], predicate=edge_tuple[2], attributes=[])
        knowledge_sources = edge_tuple[3]
        # Indicate that this edge came from the KG2 KP

        edge.attributes.append(Attribute(attribute_type_id="biolink:aggregator_knowledge_source",
                                         value=self.kg2_infores_curie,
                                         value_type_id="biolink:InformationResource",
                                         attribute_source=self.kg2_infores_curie))
        # Create knowledge source attributes for each of the knowledge sources
        knowledge_source_attributes = [Attribute(attribute_type_id="knowledge_source",
                                                 value=infores_curie,
                                                 value_type_id="biolink:InformationResource",
                                                 attribute_source=self.kg2_infores_curie)
                                       for infores_curie in knowledge_sources]
        edge.attributes += knowledge_source_attributes

        return edge
