#!/bin/env python3
"""
Ranks ARAX results. Reads these parts of the TRAPI message:

  message
  ├── query_graph.nodes[qnode_key]        (which query node is the answer)
  ├── knowledge_graph.nodes[node_id]      (the actual node objects)
  ├── knowledge_graph.edges[edge_id]      (the actual edge objects, with attributes)
  ├── auxiliary_graphs[aux_id].edges      (edge ids behind inferred edges)
  └── results[i]
      ├── node_bindings[qnode_key] -> [NodeBinding(id=node_id)]
      └── analyses[0]
          ├── edge_bindings[qedge_key] -> [EdgeBinding(id=edge_id)]
          └── support_graphs -> [aux_id]
"""
import math
import os
import sys
from collections.abc import Callable

import networkx as nx
import numpy as np
import numpy.typing as npt
import scipy.stats

from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server")
from openapi_server.models.edge import Edge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.result import Result

from util import connect_to_sqlite_read_only

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from RTXConfiguration import RTXConfiguration
from ARAX_resultify import _get_essence_node_for_qg

EDGE_BIOLINK_ATTRIBUTES = ('biolink:knowledge_level', 'biolink:agent_type', 'biolink:publications')
EDGE_ARAX_SCORE_ATTRIBUTES = ('normalized_google_distance', 'jaccard_index', 'probability_treats')
SPS_QUERY_CHUNK_SIZE = 1000


def _get_answer_node_ids(result: Result, answer_qnode_key: str) -> list[str]:
    return [node_binding.id for node_binding in result.node_bindings.get(answer_qnode_key, [])]


def _get_supporting_edge_ids(result: Result) -> dict[str, list[str]]:
    """Map each qedge key to the KG edge ids bound to it in this result, skipping creative_ qedges."""
    return {qedge_key: [edge_binding.id for edge_binding in edge_bindings]
            for qedge_key, edge_bindings in result.analyses[0].edge_bindings.items()
            if 'creative_' not in qedge_key}


def _get_edge_attributes(edge: Edge) -> dict[str, str | float | list[str] | None]:
    """
    pulls the attributes the ranker scores out of an edge
    """
    edge_attributes = {'primary_source': next((source.resource_id for source in edge.sources or []
                                                if source.resource_role == 'primary_knowledge_source'), None)}
    for attribute in edge.attributes or []:
        if attribute.attribute_type_id in EDGE_BIOLINK_ATTRIBUTES:
            edge_attributes[attribute.attribute_type_id.removeprefix('biolink:')] = attribute.value
        elif attribute.original_attribute_name in EDGE_ARAX_SCORE_ATTRIBUTES:
            edge_attributes[attribute.original_attribute_name] = float(attribute.value)
    return edge_attributes


def _get_overlay_sqlite_path() -> str:
    sqlite_name = os.path.basename(RTXConfiguration().info_for_overlay_sqlite_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "KnowledgeSources", "Tier0", sqlite_name)


def _get_sps_by_node_id(node_ids: set[str]) -> dict[str, float]:
    sqlite_path = _get_overlay_sqlite_path()
    if not node_ids or not os.path.isfile(sqlite_path):
        return {}
    connection = connect_to_sqlite_read_only(sqlite_path)
    try:
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'node_sps'").fetchone() is None:
            return {}
        node_ids = list(node_ids)
        sps_by_node_id = {}
        for start in range(0, len(node_ids), SPS_QUERY_CHUNK_SIZE):
            chunk = node_ids[start:start + SPS_QUERY_CHUNK_SIZE]
            placeholders = ",".join("?" * len(chunk))
            sps_by_node_id.update(connection.execute(f"SELECT id, sps FROM node_sps WHERE id IN ({placeholders})", chunk))
        return sps_by_node_id
    finally:
        connection.close()


class ARAXRanker:

    def aggregate_scores_dmk(self, response: ARAXResponse) -> None:
        message = response.envelope.message
        if not message.results:
            return

        answer_qnode_key = _get_essence_node_for_qg(message.query_graph)
        kg_edges = message.knowledge_graph.edges

        # gather what every result needs, in one pass
        answer_node_ids_by_result = [_get_answer_node_ids(result, answer_qnode_key) if answer_qnode_key else []
                                     for result in message.results]
        supporting_edge_ids_by_result = [_get_supporting_edge_ids(result) for result in message.results]

        # look up each answer node's SPS and each bound edge's attributes once, shared across results
        sps_by_node_id = _get_sps_by_node_id({node_id for node_ids in answer_node_ids_by_result
                                              for node_id in node_ids})
        bound_edge_ids = {edge_id for edge_ids_by_qedge in supporting_edge_ids_by_result
                          for edge_ids in edge_ids_by_qedge.values() for edge_id in edge_ids}
        edge_attributes_by_id = {edge_id: _get_edge_attributes(kg_edges[edge_id]) for edge_id in bound_edge_ids}

        for result, answer_node_ids, edge_ids_by_qedge in zip(message.results, answer_node_ids_by_result,
                                                              supporting_edge_ids_by_result):
            known_sps = [sps_by_node_id[node_id] for node_id in answer_node_ids if node_id in sps_by_node_id]
            result_sps = min(known_sps) if known_sps else None
            result_edge_attributes = {qedge_key: [edge_attributes_by_id[edge_id] for edge_id in edge_ids]
                                      for qedge_key, edge_ids in edge_ids_by_qedge.items()}
            # next: score result_edge_attributes, then multiply by the SPS factor of result_sps
