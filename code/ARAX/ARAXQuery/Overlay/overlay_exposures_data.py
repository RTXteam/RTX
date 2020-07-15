#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It currently adds the data in
EdgeAttributes tacked onto existing edges.
"""
import itertools
import json
import sys
import os

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
                log.warning(f"Could not find curies that ICEES accepts for edge {edge.source_id}--{edge.target_id}")
                return self.response

            for source_curie_to_try, target_curie_to_try in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                # Create a query graph to send to ICEES (note: they currently accept a sort of hybrid of a QG and a KG)
                edge_query_graph = QueryGraph(nodes=[QNode(id=source_curie_to_try, curie=source_curie_to_try),
                                                     QNode(id=target_curie_to_try, curie=target_curie_to_try)],
                                              edges=[QEdge(id=f"icees_{edge.id}", source_id=source_curie_to_try, target_id=target_curie_to_try)])

                # Send the query to ICEES and process results
                log.debug(f"Sending query to ICEES+ for {source_curie_to_try}--{target_curie_to_try}")
                returned_kg = self._get_exposures_data_for_edge(edge_query_graph)
                if returned_kg:
                    num_edges_obtained_icees_data_for += 1
                    log.debug(f"Got data back from ICEES+ for this edge")
                    for returned_edge in returned_kg.edges:
                        # TODO: They provide edges in both directions (seem to have identical p-values)... should we only keep one direction?
                        if not returned_edge.source_id == returned_edge.target_id:  # Exclude self-edges
                            # Add the data as a new EdgeAttribute on the current edge
                            if not edge.edge_attributes:
                                edge.edge_attributes = []
                            edge.edge_attributes += returned_edge.edge_attributes
                    # Don't worry about checking remaining synonym combos if we got results
                    break

        if num_edges_obtained_icees_data_for:
            log.info(f"Overlayed {num_edges_obtained_icees_data_for} edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any edges in the KG")

        return self.response

    @staticmethod
    def _get_exposures_data_for_edge(query_graph):
        # Note: ICEES doesn't quite accept ReasonerStdAPI, so we transform to what works
        edges = [edge.to_dict() for edge in query_graph.edges]
        nodes = [{"node_id": node.id, "curie": node.curie, "type": node.type} for node in query_graph.nodes]
        icees_compatible_query = {"message": {"knowledge_graph": {"edges": edges,
                                                                  "nodes": nodes}}}
        # TODO: Actually run the query using Query_ICEES.py, and load results into API model
        # icees_querier = Query_ICEES()
        # response = icees_querier.post_knowledge_graph_overlay(icees_compatible_query)
        # TODO: Figure out how to represent their EdgeAttributes... they look like: "edge_attributes": [
        #             {
        #               "src_feature": "AlopeciaDx",
        #               "tgt_feature": "AvgDailyAcetaldehydeExposure_2",
        #               "p_value": 0.000003790881671012495
        #             }

        # Using this just for testing purposes! (until we have a working Query_ICEES.py plugged in)
        return KnowledgeGraph(nodes=[Node(id="SCTID:72164009", type=["disease"]),
                                     Node(id="CHEBI:15343", type=["chemical_substance"])],
                              edges=[Edge(id="icees_n00_n01",
                                          source_id="SCTID:72164009",
                                          target_id="CHEBI:15343",
                                          type="association",
                                          edge_attributes=[EdgeAttribute(name="AvgDailyAcetaldehydeExposure_2",
                                                                         value=0.000003790881671012495)]),
                                     Edge(id="icees_n00_n00",
                                          source_id="SCTID:72164009",
                                          target_id="SCTID:72164009",
                                          type="association",
                                          edge_attributes=[EdgeAttribute(name="AvgDailyAcetaldehydeExposure_2",
                                                                         value=0)])])

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
