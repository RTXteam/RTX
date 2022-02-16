#!/bin/env python3
import random
import sys
import os
import time
from collections import defaultdict
from typing import Dict, Tuple, Union, Set

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
        self.biolink_helper = BiolinkHelper()
        self.kg2_infores_curie = "infores:rtx-kg2"
        self.max_allowed_edges = 1000000
        self.max_edges_per_input_curie = 1000
        self.curie_batch_size = 100

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

        # Send the query to plover in batches of input curies
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        input_qnode_key = self._get_input_qnode_key(query_graph)
        input_curies = query_graph.nodes[input_qnode_key].ids
        input_curie_set = set(input_curies)
        curie_batches = [input_curies[i:i+self.curie_batch_size] for i in range(0, len(input_curies), self.curie_batch_size)]
        log.debug(f"Split {len(input_curies)} input curies into {len(curie_batches)} batches to send to Plover")
        log.info(f"Max edges allowed per input curie for this query is: {self.max_edges_per_input_curie}")
        batch_num = 1
        for curie_batch in curie_batches:
            log.debug(f"Sending batch {batch_num} to Plover (has {len(curie_batch)} input curies)")
            query_graph.nodes[input_qnode_key].ids = curie_batch
            plover_answer, response_status = self._answer_query_using_plover(query_graph, log)
            if response_status == 200:
                batch_kg = self._load_plover_answer_into_object_model(plover_answer, log)
                final_kg = eu.merge_two_kgs(batch_kg, final_kg)
                # Prune down highly-connected input curies if we're over the max number of allowed edges
                if final_kg.edges_by_qg_id.get(qedge_key):
                    if len(final_kg.edges_by_qg_id[qedge_key]) > self.max_allowed_edges:
                        log.debug(f"Have exceeded max num allowed edges ({self.max_allowed_edges}); will attempt to "
                                  f"reduce the number of edges by pruning down highly connected nodes")
                        final_kg = self._prune_highly_connected_nodes(final_kg, qedge_key, input_curie_set,
                                                                      input_qnode_key, self.max_edges_per_input_curie,
                                                                      log)
                    # Error out if this pruning wasn't sufficient to bring down the edge count
                    if len(final_kg.edges_by_qg_id[qedge_key]) > self.max_allowed_edges:
                        log.error(f"Query for qedge {qedge_key} produced more than {self.max_allowed_edges} edges, "
                                  f"which is too much for the system to handle. You must somehow make your query "
                                  f"smaller (specify fewer input curies or use more specific predicates/categories).",
                                  error_code="QueryTooLarge")
                        return final_kg
            else:
                log.error(f"Plover returned response of {response_status}. Answer was: {plover_answer}", error_code="RequestFailed")
                return final_kg
            batch_num += 1

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
    def _prune_highly_connected_nodes(kg: QGOrganizedKnowledgeGraph, qedge_key: str, input_curies: Set[str],
                                      input_qnode_key: str, max_edges_per_input_curie: int, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        # First create a lookup of which edges belong to which input curies
        input_nodes_to_edges_dict = defaultdict(set)
        for edge_key, edge in kg.edges_by_qg_id[qedge_key].items():
            if edge.subject in input_curies:
                input_nodes_to_edges_dict[edge.subject].add(edge_key)
            if edge.object in input_curies:
                input_nodes_to_edges_dict[edge.object].add(edge_key)
        # Then prune down highly-connected nodes (delete edges per input curie in excess of some set limit)
        for node_key, connected_edge_keys in input_nodes_to_edges_dict.items():
            connected_edge_keys_list = list(connected_edge_keys)
            if len(connected_edge_keys_list) > max_edges_per_input_curie:
                random.shuffle(connected_edge_keys_list)  # Make it random which edges we keep for this input curie
                edge_keys_to_remove = connected_edge_keys_list[max_edges_per_input_curie:]
                log.debug(f"Randomly removing {len(edge_keys_to_remove)} edges from answer for input curie {node_key}")
                for edge_key in edge_keys_to_remove:
                    kg.edges_by_qg_id[qedge_key].pop(edge_key, None)
                # Document that not all answers for this input curie are included
                node = kg.nodes_by_qg_id[input_qnode_key].get(node_key)
                if node:
                    if not node.attributes:
                        node.attributes = []
                    if not any(attribute.attribute_type_id == "biolink:incomplete_result_set"
                               for attribute in node.attributes):
                        node.attributes.append(Attribute(attribute_type_id="biolink:incomplete_result_set",  # TODO: request this as actual biolink item?
                                                         value_type_id="metatype:Boolean",
                                                         value=True,
                                                         attribute_source="infores:rtx-kg2",
                                                         description=f"This attribute indicates that not all "
                                                                     f"nodes/edges returned as answers for this input "
                                                                     f"curie were included in the final answer due to "
                                                                     f"size limitations. {max_edges_per_input_curie} "
                                                                     f"edges for this input curie were kept."))
        # Then delete any nodes orphaned by removal of edges
        node_keys_used_by_edges = kg.get_all_node_keys_used_by_edges()
        for qnode_key, nodes in kg.nodes_by_qg_id.items():
            orphan_node_keys = set(nodes).difference(node_keys_used_by_edges)
            if orphan_node_keys:
                log.debug(f"Removing {len(orphan_node_keys)} {qnode_key} nodes orphaned by the above step")
                for orphan_node_key in orphan_node_keys:
                    del kg.nodes_by_qg_id[qnode_key][orphan_node_key]
        return kg

    @staticmethod
    def _answer_query_using_plover(qg: QueryGraph, log: ARAXResponse) -> Tuple[Dict[str, Dict[str, Union[set, dict]]], int]:
        rtxc = RTXConfiguration()
        rtxc.live = "Production"
        # First prep the query graph (requires some minor additions for Plover)
        dict_qg = qg.to_dict()
        dict_qg["include_metadata"] = True  # Ask plover to return node/edge objects (not just IDs)
        dict_qg["respect_predicate_symmetry"] = True  # Ignore direction for symmetric predicate, enforce for asymmetric
        # Allow subclass_of reasoning for qnodes with a small number of curies
        for qnode in dict_qg["nodes"].values():
            if qnode.get("ids") and len(qnode["ids"]) < 5:
                if "allow_subclasses" not in qnode or qnode["allow_subclasses"] is None:
                    qnode["allow_subclasses"] = True
        # Then send the actual query
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
        # Create knowledge source attributes for each of this edge's knowledge sources
        knowledge_source_attributes = [Attribute(attribute_type_id="biolink:knowledge_source",
                                                 value=infores_curie,
                                                 value_type_id="biolink:InformationResource",
                                                 attribute_source=self.kg2_infores_curie)
                                       for infores_curie in knowledge_sources]
        edge.attributes += knowledge_source_attributes
        return edge

    @staticmethod
    def _get_input_qnode_key(one_hop_qg: QueryGraph) -> str:
        qedge = next(qedge for qedge in one_hop_qg.edges.values())
        qnode_a_key = qedge.subject
        qnode_b_key = qedge.object
        qnode_a = one_hop_qg.nodes[qnode_a_key]
        qnode_b = one_hop_qg.nodes[qnode_b_key]
        if qnode_a.ids and qnode_b.ids:
            # Considering the qnode with fewer curies the 'input' is more efficient for querying Plover
            return qnode_a_key if len(qnode_a.ids) < len(qnode_b.ids) else qnode_b_key
        elif qnode_a.ids:
            return qnode_a_key
        else:
            return qnode_b_key
