#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It adds the data (p-values) either in
virtual edges (if the virtual_relation_label, source_qnode_id, and target_qnode_id are provided) or as EdgeAttributes
tacked onto existing edges in the knowledge graph (applied to all edges).
"""
import itertools
import sys
import os

import requests
import yaml


import random
import time
random.seed(time.time())

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou


class OverlayExposuresData:

    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.icees_known_curies = self._load_icees_known_curies(self.response)
        self.synonyms_dict = self._get_node_synonyms(self.message.knowledge_graph)
        self.icees_attribute_name = "icees_p-value"
        self.icees_attribute_type = "EDAM:data_1669"
        self.icees_edge_type = "has_icees_p-value_with"
        self.icees_knowledge_graph_overlay_url = "https://icees.renci.org:16340/knowledge_graph_overlay"
        self.virtual_relation_label = self.parameters.get('virtual_relation_label')

    def overlay_exposures_data(self):
        source_qnode_id = self.parameters.get('source_qnode_id')
        target_qnode_id = self.parameters.get('target_qnode_id')
        if self.virtual_relation_label and source_qnode_id and target_qnode_id:
            self.response.debug(f"Overlaying exposures data using virtual edge method "
                                f"({source_qnode_id}--{self.virtual_relation_label}--{target_qnode_id})")
            self._add_virtual_edges(source_qnode_id, target_qnode_id)
        else:
            self.response.debug(f"Overlaying exposures data using attribute method")
            self._decorate_existing_edges()

    def _add_virtual_edges(self, source_qnode_id, target_qnode_id):
        # This function adds ICEES exposures data as virtual edges between nodes with the specified qnode IDs
        knowledge_graph = self.message.knowledge_graph
        query_graph = self.message.query_graph
        log = self.response
        nodes_by_qg_id = self._get_nodes_by_qg_id(knowledge_graph)
        source_curies = set(nodes_by_qg_id.get(source_qnode_id))
        target_curies = set(nodes_by_qg_id.get(target_qnode_id))
        # Determine which curies ICEES 'knows' about
        known_source_curies = {curie for curie in source_curies if self._get_accepted_synonyms(curie)}
        known_target_curies = {curie for curie in target_curies if self._get_accepted_synonyms(curie)}

        num_node_pairs_recognized = 0
        for source_curie, target_curie in ou.get_node_pairs_to_overlay(source_qnode_id, target_qnode_id, query_graph, knowledge_graph, log):
            # Query ICEES only for synonyms it 'knows' about
            if source_curie in known_source_curies and target_curie in known_target_curies:
                accepted_source_synonyms = self._get_accepted_synonyms(source_curie)
                accepted_target_synonyms = self._get_accepted_synonyms(target_curie)
                for source_synonym, target_synonym in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                    # qedge = QEdge(id=f"icees_{source_synonym}--{target_synonym}",
                    #               source_id=source_synonym,
                    #               target_id=target_synonym)
                    qedge = QEdge(id=f"icees_{source_synonym}--{target_synonym}",
                                  source_id=source_synonym,
                                  target_id=target_synonym)
                    log.debug(f"Sending query to ICEES+ for {source_synonym}--{target_synonym}")
                    p_value = self._get_icees_p_value_for_edge(qedge, log)
                    if p_value is not None:
                        num_node_pairs_recognized += 1
                        # Add a new virtual edge with this data
                        id, virtual_edge = self._create_icees_virtual_edge(source_curie, target_curie, p_value)
                        old_id = id
                        while id in knowledge_graph.edges:
                            id = old_id+f".{random.randint(10**(9-1), (10**9)-1)}"
                        knowledge_graph.edges[id] = virtual_edge
                        break  # Don't worry about checking remaining synonym combos if we got results
            # Add an 'empty' virtual edge (p-value of None) if we couldn't find any results for this node pair #1009
            id, empty_virtual_edge = self._create_icees_virtual_edge(source_curie, target_curie, None)
            while id in knowledge_graph.edges:
                id = old_id+f".{random.randint(10**(9-1), (10**9)-1)}"
            knowledge_graph.edges[id] = empty_virtual_edge

        # Add a qedge to the query graph that corresponds to our new virtual edges
        # new_qedge = QEdge(id=self.virtual_relation_label,
        #                   source_id=source_qnode_id,
        #                   target_id=target_qnode_id,
        #                   type=self.icees_edge_type,
        #                   option_group_id=ou.determine_virtual_qedge_option_group(source_qnode_id, target_qnode_id,
        #                                                                           query_graph, log))
        # Likely need to change this for TRAPI 1.0
        new_qedge = QEdge(subject=source_qnode_id,
                          object=target_qnode_id,
                          predicate=self.icees_edge_type,
                          option_group_id=ou.determine_virtual_qedge_option_group(source_qnode_id, target_qnode_id,
                                                                                  query_graph, log))
        query_graph.edges[self.virtual_relation_label] = new_qedge

        if num_node_pairs_recognized:
            log.info(f"ICEES+ returned data for {num_node_pairs_recognized} node pairs")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any {source_qnode_id}--{target_qnode_id} node pairs")

    def _decorate_existing_edges(self):
        # This function decorates all existing edges in the knowledge graph with ICEES data, stored in EdgeAttributes
        knowledge_graph = self.message.knowledge_graph
        log = self.response

        # Query ICEES for each edge in the knowledge graph that ICEES can provide data on (use known curies)
        num_edges_obtained_icees_data_for = 0
        edges_by_node_pair = self._get_edges_by_node_pair(knowledge_graph)  # Don't duplicate effort for parallel edges
        for node_pair_key, node_pair_edges in edges_by_node_pair.items():
            source_id = node_pair_edges[0].source_id
            target_id = node_pair_edges[0].target_id
            accepted_source_synonyms = self._get_accepted_synonyms(source_id)
            accepted_target_synonyms = self._get_accepted_synonyms(target_id)
            if accepted_source_synonyms and accepted_target_synonyms:
                # Query ICEES for each possible combination of accepted source/target synonyms
                for source_curie_to_try, target_curie_to_try in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                    qedge = QEdge(id=f"icees_e00", source_id=source_curie_to_try, target_id=target_curie_to_try)
                    log.debug(f"Sending query to ICEES+ for {source_curie_to_try}--{target_curie_to_try}")
                    p_value = self._get_icees_p_value_for_edge(qedge, log)
                    if p_value is not None:
                        num_edges_obtained_icees_data_for += len(node_pair_edges)
                        new_edge_attribute = self._create_icees_edge_attribute(p_value)
                        # Add the data as new EdgeAttributes on the existing edges with this source/target ID
                        for edge in node_pair_edges:
                            if not edge.edge_attributes:
                                edge.edge_attributes = []
                            edge.edge_attributes.append(new_edge_attribute)
                        # Don't worry about checking remaining synonym combos if we got results
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
        if self.icees_known_curies:
            return self.icees_known_curies.intersection(formatted_synonyms)
        else:
            return formatted_synonyms

    def _get_icees_p_value_for_edge(self, qedge, log):
        # Note: ICEES doesn't quite accept ReasonerStdAPI, so we transform to what works
        qedges = [qedge.to_dict()]
        qnodes = [{"node_id": curie, "curie": curie} for curie in [qedge.subject, qedge.object]]
        icees_compatible_query = {"message": {"knowledge_graph": {"edges": qedges,
                                                                  "nodes": qnodes}}}
        icees_response = requests.post(self.icees_knowledge_graph_overlay_url,
                                       json=icees_compatible_query,
                                       headers={'accept': 'application/json'},
                                       verify=False)
        if icees_response.status_code != 200:
            log.warning(f"ICEES+ API returned response of {icees_response.status_code}")
        elif "return value" in icees_response.json():
            returned_knowledge_graph = icees_response.json()["return value"].get("knowledge_graph")
            if returned_knowledge_graph:
                p_values = []
                for edge in returned_knowledge_graph.get("edges", dict()).values():
                    source_id = edge.get("subject")
                    target_id = edge.get("object")
                    # Skip any self-edges and reverse edges in ICEES response
                    if source_id == qedge.source_id and target_id == qedge.target_id:
                        p_values += [attribute["p_value"] for attribute in edge.get("edge_attributes", []) if attribute.get("p_value") is not None]
                if p_values:
                    average_p_value = sum(p_values) / len(p_values)
                    log.debug(f"Average returned p-value is {average_p_value}")
                    return average_p_value
        return None

    def _create_icees_edge_attribute(self, p_value):
        return EdgeAttribute(name=self.icees_attribute_name,
                             value=p_value,
                             type=self.icees_attribute_type)

    def _create_icees_virtual_edge(self, source_curie, target_curie, p_value):
        id = f"ICEES:{source_curie}--{target_curie}"
        # edge = Edge(id=f"ICEES:{source_curie}--{target_curie}",
        #             type=self.icees_edge_type,
        #             source_id=source_curie,
        #             target_id=target_curie,
        #             is_defined_by="ARAX",
        #             provided_by="ICEES+",
        #             relation=self.virtual_relation_label,
        #             qedge_ids=[self.virtual_relation_label],
        #             edge_attributes=[self._create_icees_edge_attribute(p_value)])
        edge_attribute_list = [
            self._create_icees_edge_attribute(p_value),
            EdgeAttribute(name="is_defined_by", value="ARAX"),
            EdgeAttribute(name="provided_by", value="ICEES+"),
            EdgeAttribute(name="qedge_ids", value=[self.virtual_relation_label])
        ]
        edge = Edge(predicate=self.icees_edge_type, subject=source_curie, object=target_curie,
                        relation=self.virtual_relation_label, attributes=edge_attribute_list)
        return id, edge

    @staticmethod
    def _get_nodes_by_qg_id(knowledge_graph):
        nodes_by_qg_id = dict()
        for key, node in knowledge_graph.nodes.items():
            for qnode_id in node.qnode_ids:
                if qnode_id not in nodes_by_qg_id:
                    nodes_by_qg_id[qnode_id] = dict()
                nodes_by_qg_id[qnode_id][node.id] = node
        return nodes_by_qg_id

    @staticmethod
    def _get_node_synonyms(knowledge_graph):
        synonymizer = NodeSynonymizer()
        node_ids = {key for key in knowledge_graph.nodes.keys()}
        equivalent_curie_info = synonymizer.get_equivalent_nodes(node_ids, kg_name='KG2')
        return {node_id: set(equivalent_curies_dict) for node_id, equivalent_curies_dict in equivalent_curie_info.items()}

    @staticmethod
    def _get_edges_by_node_pair(knowledge_graph):
        edges_by_node_pair = dict()
        for edge in knowledge_graph.edges.values():
            node_pair_key = f"{edge.subject}--{edge.object}"
            if node_pair_key not in edges_by_node_pair:
                edges_by_node_pair[node_pair_key] = []
            edges_by_node_pair[node_pair_key].append(edge)
        return edges_by_node_pair

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
