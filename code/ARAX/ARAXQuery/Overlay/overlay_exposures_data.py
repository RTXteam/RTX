#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It either adds the data as virtual
edges (if the virtual_relation_label, source_qnode_id, and target_qnode_id are provided) or as EdgeAttributes tacked
onto existing edges in the knowledge graph (applied to all edges).
"""
import itertools
import sys
import os

import requests
import yaml

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.q_edge import QEdge
from swagger_server.models.edge import Edge
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class OverlayExposuresData:

    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.icees_curies = self._load_icees_known_curies(self.response)
        self.synonyms_dict = self._get_node_synonyms(self.message.knowledge_graph)
        self.icees_attribute_name = "icees_p-value"
        self.icees_edge_type = "has_icees_p-value_with"

    def overlay_exposures_data(self):
        virtual_relation_label = self.parameters.get('virtual_relation_label')
        source_qnode_id = self.parameters.get('source_qnode_id')
        target_qnode_id = self.parameters.get('target_qnode_id')
        if virtual_relation_label and source_qnode_id and target_qnode_id:
            self.response.debug(f"Overlaying exposures data using virtual edge method "
                                f"({source_qnode_id}--{virtual_relation_label}--{target_qnode_id})")
            self._add_virtual_edges(virtual_relation_label, source_qnode_id, target_qnode_id)
        else:
            self.response.debug(f"Overlaying exposures data using attribute method")
            self._decorate_existing_edges()

    def _add_virtual_edges(self, virtual_relation_label, source_qnode_id, target_qnode_id):
        # This function adds ICEES exposures data as virtual edges between nodes with the specified qnode IDs
        knowledge_graph = self.message.knowledge_graph
        log = self.response
        nodes_by_qg_id = self._get_nodes_by_qg_id(knowledge_graph)

        # Narrow down our curies to only those ICEES 'knows' about
        source_curie_set = {curie for curie in nodes_by_qg_id.get(source_qnode_id) if self._get_accepted_synonyms(curie)}
        target_curie_set = {curie for curie in nodes_by_qg_id.get(target_qnode_id) if self._get_accepted_synonyms(curie)}
        if not source_curie_set or not target_curie_set:
            log.warning(f"Could not find curies that ICEES accepts for any {source_qnode_id}--{target_qnode_id} node pairs")
            return

        # Query ICEES for each possible combination of accepted source/target synonyms
        num_virtual_eges_added = 0
        for source_curie, target_curie in itertools.product(source_curie_set, target_curie_set):
            accepted_source_synonyms = self._get_accepted_synonyms(source_curie)
            accepted_target_synonyms = self._get_accepted_synonyms(target_curie)
            for source_synonym, target_synonym in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                qedge = QEdge(id=f"icees_{source_synonym}--{target_synonym}",
                              source_id=source_synonym,
                              target_id=target_synonym)
                log.debug(f"Sending query to ICEES+ for {source_synonym}--{target_synonym}")
                returned_edge_attributes = self._get_exposures_data(qedge, log)
                if returned_edge_attributes:
                    log.debug(f"Got data back from ICEES+")
                    # Add a new virtual edge with this data
                    num_virtual_eges_added += 1
                    new_edge = Edge(id=f"ICEES:{source_curie}--{target_curie}",
                                    type=self.icees_edge_type,
                                    source_id=source_curie,
                                    target_id=target_curie,
                                    is_defined_by="ARAX",
                                    provided_by="ICEES+",
                                    relation=virtual_relation_label,
                                    qedge_ids=[virtual_relation_label],
                                    edge_attributes=returned_edge_attributes)
                    knowledge_graph.edges.append(new_edge)
                    # Don't worry about checking remaining synonym combos if we got results (TODO: change this?)
                    break

        # Add a qedge to the query graph if we added any virtual edges
        if num_virtual_eges_added:
            new_qedge = QEdge(id=virtual_relation_label,
                              source_id=source_qnode_id,
                              target_id=target_qnode_id,
                              type=self.icees_edge_type)
            self.message.query_graph.edges.append(new_qedge)

        if num_virtual_eges_added:
            log.info(f"Added {num_virtual_eges_added} virtual edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any {source_qnode_id}--{target_qnode_id} node pairs")

    def _decorate_existing_edges(self):
        # This function decorates all existing edges in the knowledge graph with ICEES data, stored in EdgeAttributes
        knowledge_graph = self.message.knowledge_graph
        log = self.response

        # TODO: Adjust to query node pairs... (otherwise duplicating effort for parallel edges..)
        # Query ICEES for each edge in the knowledge graph that ICEES can provide data on (use known curies)
        num_edges_obtained_icees_data_for = 0
        for edge in knowledge_graph.edges:
            accepted_source_synonyms = self._get_accepted_synonyms(edge.source_id)
            accepted_target_synonyms = self._get_accepted_synonyms(edge.target_id)
            if not accepted_source_synonyms or not accepted_target_synonyms:
                log.debug(f"Could not find curies that ICEES accepts for edge {edge.id} ({edge.source_id}--{edge.target_id})")
            else:
                # Query ICEES for each possible combination of accepted source/target synonyms
                for source_curie_to_try, target_curie_to_try in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                    qedge = QEdge(id=f"icees_{edge.id}", source_id=source_curie_to_try, target_id=target_curie_to_try)
                    log.debug(f"Sending query to ICEES+ for {source_curie_to_try}--{target_curie_to_try}")
                    returned_edge_attributes = self._get_exposures_data(qedge, log)
                    if returned_edge_attributes:
                        num_edges_obtained_icees_data_for += 1
                        log.debug(f"Got data back from ICEES+")
                        # Add the data as new EdgeAttributes on the current edge
                        if not edge.edge_attributes:
                            edge.edge_attributes = []
                        edge.edge_attributes += returned_edge_attributes
                        # Don't worry about checking remaining synonym combos if we got results (TODO: change this?)
                        break

        if num_edges_obtained_icees_data_for:
            log.info(f"Overlayed {num_edges_obtained_icees_data_for} edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any edges in the KG")

        return self.response

    # Helper functions

    def _get_accepted_synonyms(self, curie):
        synonyms = self.synonyms_dict.get(curie, curie)
        formatted_synonyms = {self._convert_curie_to_icees_preferred_format(curie) for curie in synonyms}
        accepted_synonyms = self.icees_curies.intersection(formatted_synonyms)
        return accepted_synonyms

    def _get_exposures_data(self, qedge, log):
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
        if icees_response.status_code != 200:
            log.warning(f"ICEES+ API returned response of {icees_response.status_code}.")
        elif "return value" in icees_response.json():
            returned_knowledge_graph = icees_response.json()["return value"].get("knowledge_graph")
            if returned_knowledge_graph:
                for edge in returned_knowledge_graph.get("edges", []):
                    source_id = edge.get("source_id")
                    target_id = edge.get("target_id")
                    if source_id and target_id:
                        # Skip any self-edges and reverse edges in ICEES response
                        if source_id == qedge.source_id and target_id == qedge.target_id:
                            for returned_edge_attribute in edge.get("edge_attributes", []):
                                all_edge_attributes.append(EdgeAttribute(name=self.icees_attribute_name,
                                                                         value=returned_edge_attribute["p_value"],
                                                                         type="EDAM:data_1669"))
        return all_edge_attributes

    @staticmethod
    def _get_nodes_by_qg_id(knowledge_graph):
        nodes_by_qg_id = dict()
        for node in knowledge_graph.nodes:
            for qnode_id in node.qnode_ids:
                if qnode_id not in nodes_by_qg_id:
                    nodes_by_qg_id[qnode_id] = dict()
                nodes_by_qg_id[qnode_id][node.id] = node
        return nodes_by_qg_id

    @staticmethod
    def _get_node_synonyms(knowledge_graph):
        synonymizer = NodeSynonymizer()
        node_ids = {node.id for node in knowledge_graph.nodes}
        equivalent_curie_info = synonymizer.get_equivalent_nodes(node_ids, kg_name='KG2')
        return {node_id: set(equivalent_curies_dict) for node_id, equivalent_curies_dict in equivalent_curie_info.items()}

    @staticmethod
    def _load_icees_known_curies(log):
        response = requests.get("https://raw.githubusercontent.com/NCATS-Tangerine/icees-api/api/config/identifiers.yml")
        known_curies = []
        if response.status_code == 200:
            icees_curie_dict = yaml.safe_load(response.text)
            for category, sub_dict in icees_curie_dict.items():
                for sub_category, curie_list in sub_dict.items():
                    known_curies += curie_list
        else:
            log.warning(f"Failed to load ICEES yaml file of known curies. (Page gave status {response.status_code}.)")
        return set(known_curies)

    @staticmethod
    def _convert_curie_to_icees_preferred_format(curie):
        prefix = curie.split(':')[0]
        local_id = curie.split(':')[-1]
        if prefix.upper() == "CUI" or prefix.upper() == "UMLS":
            return f"umlscui:{local_id}"
        elif prefix.upper() == "CHEMBL.COMPOUND":
            return f"CHEMBL:{local_id}"
        elif prefix.upper() == "RXNORM":
            return f"rxcui:{local_id}"
        else:
            return curie
