#!/bin/env python3
# This file contains utilities/helper functions for general use within the Overlay module
import itertools
import os
import sys
from typing import Dict, Set, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.message import Message
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_resultify import ARAXResultify
from response import Response


def get_node_pairs_to_overlay(source_qnode_id: str, target_qnode_id: str, query_graph: QueryGraph,
                              knowledge_graph: KnowledgeGraph, log: Response) -> Set[Tuple[str, str]]:
    """
    This function determines which combinations of source/target nodes in the KG need to be overlayed (e.g., have a
    virtual edge added between). It makes use of Resultify to determine what combinations of source and target nodes
    may actually appear together in the same Results. (See issue #1069.) If it fails to narrow the node pairs for
    whatever reason, it defaults to returning all possible combinations of source/target nodes.
    """
    log.debug(f"Narrowing down {source_qnode_id}--{target_qnode_id} node pairs to overlay")
    kg_nodes_by_qg_id = get_node_ids_by_qg_id(knowledge_graph)
    kg_edges_by_qg_id = get_edge_ids_by_qg_id(knowledge_graph)
    # Grab the portion of the QG already 'expanded' (aka, present in the KG)
    sub_query_graph = QueryGraph(nodes=[qnode for qnode in query_graph.nodes if qnode.id in set(kg_nodes_by_qg_id)],
                                 edges=[qedge for qedge in query_graph.edges if qedge.id in set(kg_edges_by_qg_id)])

    # Compute results using Resultify so we can see which nodes appear in the same results
    sub_message = Message()
    sub_message.query_graph = sub_query_graph
    sub_message.knowledge_graph = KnowledgeGraph(nodes=knowledge_graph.nodes.copy(),
                                                 edges=knowledge_graph.edges.copy())
    resultifier = ARAXResultify()
    resultify_response = resultifier.apply(sub_message, {})

    # Figure out which node pairs appear together in one or more results
    if resultify_response.status == 'OK':
        node_pairs = set()
        for result in sub_message.results:
            source_curies_in_this_result = {node_binding.kg_id for node_binding in result.node_bindings if
                                            node_binding.qg_id == source_qnode_id}
            target_curies_in_this_result = {node_binding.kg_id for node_binding in result.node_bindings if
                                            node_binding.qg_id == target_qnode_id}
            pairs_in_this_result = set(itertools.product(source_curies_in_this_result, target_curies_in_this_result))
            node_pairs = node_pairs.union(pairs_in_this_result)
        log.debug(f"Identified {len(node_pairs)} node pairs to overlay (with help of resultify)")
        if node_pairs:
            return node_pairs
    # Back up to using the old (O(n^2)) method of all combinations of source/target nodes in the KG
    log.warning(f"Failed to narrow down node pairs to overlay; defaulting to all possible combinations")
    return set(itertools.product(kg_nodes_by_qg_id[source_qnode_id], kg_nodes_by_qg_id[target_qnode_id]))


def get_node_ids_by_qg_id(knowledge_graph: KnowledgeGraph) -> Dict[str, Set[str]]:
    # Returns all node IDs in the KG organized like so: {"n00": {"DOID:12"}, "n01": {"UniProtKB:1", "UniProtKB:2", ...}}
    node_ids_by_qg_id = dict()
    if knowledge_graph.nodes:
        for node in knowledge_graph.nodes:
            for qnode_id in node.qnode_ids:
                if qnode_id not in node_ids_by_qg_id:
                    node_ids_by_qg_id[qnode_id] = set()
                node_ids_by_qg_id[qnode_id].add(node.id)
    return node_ids_by_qg_id


def get_edge_ids_by_qg_id(knowledge_graph: KnowledgeGraph) -> Dict[str, Set[str]]:
    # Returns all edge IDs in the KG organized like so: {"e00": {"KG2:123", ...}, "e01": {"KG2:224", "KG2:225", ...}}
    edge_ids_by_qg_id = dict()
    if knowledge_graph.edges:
        for edge in knowledge_graph.edges:
            for qedge_id in edge.qedge_ids:
                if qedge_id not in edge_ids_by_qg_id:
                    edge_ids_by_qg_id[qedge_id] = set()
                edge_ids_by_qg_id[qedge_id].add(edge.id)
    return edge_ids_by_qg_id
