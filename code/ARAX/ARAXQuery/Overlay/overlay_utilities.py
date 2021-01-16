#!/bin/env python3
# This file contains utilities/helper functions for general use within the Overlay module
import itertools
import os
import sys
from typing import Dict, Optional, Set, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.message import Message
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_resultify import ARAXResultify
from ARAX_response import ARAXResponse


def get_node_pairs_to_overlay(subject_qnode_key: str, object_qnode_key: str, query_graph: QueryGraph,
                              knowledge_graph: KnowledgeGraph, log: ARAXResponse) -> Set[Tuple[str, str]]:
    """
    This function determines which combinations of subject/object nodes in the KG need to be overlayed (e.g., have a
    virtual edge added between). It makes use of Resultify to determine what combinations of subject and object nodes
    may actually appear together in the same Results. (See issue #1069.) If it fails to narrow the node pairs for
    whatever reason, it defaults to returning all possible combinations of subject/object nodes.
    """
    log.debug(f"Narrowing down {subject_qnode_key}--{object_qnode_key} node pairs to overlay")
    kg_nodes_by_qg_id = get_node_ids_by_qg_id(knowledge_graph)
    kg_edges_by_qg_id = get_edge_ids_by_qg_id(knowledge_graph)
    # Grab the portion of the QG already 'expanded' (aka, present in the KG)
    sub_query_graph = QueryGraph(nodes={key:qnode for key, qnode in query_graph.nodes.items() if key in set(kg_nodes_by_qg_id)},
                                 edges={key:qedge for key, qedge in query_graph.edges.items() if key in set(kg_edges_by_qg_id)})

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
            subject_curies_in_this_result = {node_binding.kg_id for node_binding in result.node_bindings if
                                            node_binding.qg_id == subject_qnode_key}
            object_curies_in_this_result = {node_binding.kg_id for node_binding in result.node_bindings if
                                            node_binding.qg_id == object_qnode_key}
            pairs_in_this_result = set(itertools.product(subject_curies_in_this_result, object_curies_in_this_result))
            node_pairs = node_pairs.union(pairs_in_this_result)
        log.debug(f"Identified {len(node_pairs)} node pairs to overlay (with help of resultify)")
        if node_pairs:
            return node_pairs
    # Back up to using the old (O(n^2)) method of all combinations of subject/object nodes in the KG
    log.warning(f"Failed to narrow down node pairs to overlay; defaulting to all possible combinations")
    return set(itertools.product(kg_nodes_by_qg_id[subject_qnode_key], kg_nodes_by_qg_id[object_qnode_key]))


def get_node_ids_by_qg_id(knowledge_graph: KnowledgeGraph) -> Dict[str, Set[str]]:
    # Returns all node IDs in the KG organized like so: {"n00": {"DOID:12"}, "n01": {"UniProtKB:1", "UniProtKB:2", ...}}
    node_keys_by_qg_key = dict()
    if knowledge_graph.nodes:
        for key, node in knowledge_graph.nodes.items():
            for qnode_key in node.qnode_keys:
                if qnode_key not in node_keys_by_qg_key:
                    node_keys_by_qg_key[qnode_key] = set()
                node_keys_by_qg_key[qnode_key].add(key)
    return node_keys_by_qg_key


def get_edge_ids_by_qg_id(knowledge_graph: KnowledgeGraph) -> Dict[str, Set[str]]:
    # Returns all edge IDs in the KG organized like so: {"e00": {"KG2:123", ...}, "e01": {"KG2:224", "KG2:225", ...}}
    edge_keys_by_qg_key = dict()
    if knowledge_graph.edges:
        for key, edge in knowledge_graph.edges.items():
            for qedge_key in edge.qedge_keys:
                if qedge_key not in edge_keys_by_qg_key:
                    edge_keys_by_qg_key[qedge_key] = set()
                edge_keys_by_qg_key[qedge_key].add(key)
    return edge_keys_by_qg_key


def determine_virtual_qedge_option_group(subject_qnode_key: str, object_qnode_key: str, query_graph: QueryGraph, log: Response) -> Optional[str]:
    # Determines what option group ID a virtual qedge between the two input qnodes should have
    qnodes = [qnode for key, qnode in query_graph.nodes.items() if key in {subject_qnode_key, object_qnode_key}]
    qnode_option_group_ids = {qnode.option_group_id for qnode in qnodes if qnode.option_group_id}
    if len(qnode_option_group_ids) == 1:
        return list(qnode_option_group_ids)[0]
    elif len(qnode_option_group_ids) > 1:
        log.error(f"Cannot add a virtual qedge between two qnodes that belong to different option groups {qnode_option_group_ids}",
                  error_code="InvalidQEdge")
        return None
    else:
        return None
