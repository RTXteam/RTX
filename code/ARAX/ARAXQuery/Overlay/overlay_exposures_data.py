#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It currently adds the data in
EdgeAttributes tacked onto existing edges.
"""
import itertools
import json
import sys
import os

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class OverlayExposuresData:

    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def decorate(self):
        knowledge_graph = self.message.knowledge_graph
        nodes_map = {node.id: node for node in self.message.knowledge_graph.nodes}
        log = self.response

        # Figure out all the different edges we should query ICEES for
        relevant_edges = [edge for edge in knowledge_graph.edges if self._is_relevant_edge(edge, nodes_map)]
        if relevant_edges:
            log.debug(f"Found {len(relevant_edges)} edges to attempt to get exposures data for")
        else:
            log.warning(f"Could not find any edges appropriate to query ICEES+ for")
            return self.response
        # TODO: Adjust to query node pairs... (otherwise duplicating effort for parallel edges..)

        # Grab our synonyms in one up front batch
        node_ids_used_by_edges = {edge.source_id for edge in relevant_edges}.union(edge.target_id for edge in relevant_edges)
        synonymizer = NodeSynonymizer()
        synonyms_dict = synonymizer.get_equivalent_nodes(list(node_ids_used_by_edges), kg_name='KG2')

        # Query ICEES for each edge in the knowledge graph that might have exposures data
        num_edges_obtained_icees_data_for = 0
        for edge in relevant_edges:
            # Try to find a curie of the type (prefix) ICEES likes
            source_synonyms = synonyms_dict.get(edge.source_id, [edge.source_id])
            target_synonyms = synonyms_dict.get(edge.target_id, [edge.target_id])
            formatted_source_synonyms = [self._convert_curie_to_icees_preferred_format(curie) for curie in source_synonyms]
            formatted_target_synonyms = [self._convert_curie_to_icees_preferred_format(curie) for curie in target_synonyms]
            accepted_source_synonyms = [curie for curie in formatted_source_synonyms if self._has_accepted_prefix(curie)]
            accepted_target_synonyms = [curie for curie in formatted_target_synonyms if self._has_accepted_prefix(curie)]
            if not accepted_source_synonyms or not accepted_target_synonyms:
                log.debug(f"Could not find curies that ICEES accepts for edge {edge.id} ({edge.source_id}--{edge.target_id})")
                continue

            # Query ICEES for each possible combination of synonyms for source and target nodes
            for source_curie_to_try, target_curie_to_try in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                qedge = QEdge(id=f"icees_{edge.id}", source_id=source_curie_to_try, target_id=target_curie_to_try)
                log.debug(f"Sending query to ICEES+ for {source_curie_to_try}--{target_curie_to_try}")
                returned_edge_attributes = self._get_exposures_data_for_edge(qedge)
                if returned_edge_attributes:
                    num_edges_obtained_icees_data_for += 1
                    log.debug(f"Got data back from ICEES+ for this edge")
                    # Add the data as new EdgeAttributes on the current edge
                    if not edge.edge_attributes:
                        edge.edge_attributes = []
                    edge.edge_attributes += returned_edge_attributes
                    # Don't worry about checking remaining synonym combos if we got results
                    break

        if num_edges_obtained_icees_data_for:
            log.info(f"Overlayed {num_edges_obtained_icees_data_for} edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any edges in the KG")

        return self.response

    @staticmethod
    def _get_exposures_data_for_edge(qedge):
        # Note: ICEES doesn't quite accept ReasonerStdAPI, so we transform to what works
        qedges = [qedge.to_dict()]
        qnodes = [{"node_id": curie, "curie": curie} for curie in [qedge.source_id, qedge.target_id]]
        icees_compatible_query = {"message": {"knowledge_graph": {"edges": qedges,
                                                                  "nodes": qnodes}}}
        icees_response = requests.post("https://icees.renci.org:16340/knowledge_graph_overlay",
                                       json=icees_compatible_query,
                                       headers={'accept': 'application/json'},
                                       verify=False)
        all_edge_attributes = []
        if icees_response and icees_response.status_code == 200 and "return value" in icees_response.json():
            # TODO: better error handling
            returned_knowledge_graph = icees_response.json()["return value"].get("knowledge_graph")
            if returned_knowledge_graph:
                for edge in returned_knowledge_graph.get("edges", []):
                    source_id = edge.get("source_id")
                    target_id = edge.get("target_id")
                    if source_id and target_id:
                        # Skip any self-edges and reverse edges in ICEES response
                        if source_id == qedge.source_id and target_id == qedge.target_id:
                            for edge_attribute in edge.get("edge_attributes", []):
                                all_edge_attributes.append(EdgeAttribute(name="icees_p-value",  # TODO: better naming?
                                                                         value=edge_attribute["p_value"],
                                                                         type="EDAM:data_1669"))
        return all_edge_attributes

    @staticmethod
    def _has_accepted_prefix(curie):
        # Note: These are extracted from ICEES' identifiers.yaml file; may change when they start using node normalizer
        icees_prefixes = {"CHEBI", "PUBCHEM", "MESH", "NCIT", "umlscui", "CAS", "CHEMBL", "rxcui", "SCTID", "MONDO",
                          "HP", "ENVO", "SMILES", "LOINC"}
        prefix = curie.split(':')[0]
        return prefix in icees_prefixes

    @staticmethod
    def _convert_curie_to_icees_preferred_format(curie):
        prefix = curie.split(':')[0]
        local_id = curie.split(':')[-1]
        if prefix == "CUI" or prefix == "UMLS":
            return f"umlscui:{local_id}"
        elif prefix == "CHEMBL.COMPOUND":
            return f"CHEMBL:{local_id}"
        else:
            return curie

    @staticmethod
    def _is_relevant_edge(edge, nodes_by_qg_id):
        # TODO: Does every edge need to involve a drug/chemical_substance?
        exposures_node_types = {'chemical_substance', 'drug', 'disease', 'phenotypic_feature'}
        source_node = nodes_by_qg_id.get(edge.source_id)
        target_node = nodes_by_qg_id.get(edge.target_id)
        if set(source_node.type).intersection(exposures_node_types) and set(target_node.type).intersection(exposures_node_types):
            return True
        else:
            return False
