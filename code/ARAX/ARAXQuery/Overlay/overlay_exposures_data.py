#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It adds the data (p-values) either in
virtual edges (if the virtual_relation_label, subject_qnode_key, and object_qnode_key are provided) or as EdgeAttributes
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
        self.icees_edge_type = "biolink:has_icees_p-value_with"
        self.icees_knowledge_graph_overlay_url = "https://icees.renci.org:16340/knowledge_graph_overlay"
        self.virtual_relation_label = self.parameters.get('virtual_relation_label')

    def overlay_exposures_data(self):
        subject_qnode_key = self.parameters.get('subject_qnode_key')
        object_qnode_key = self.parameters.get('object_qnode_key')
        if self.virtual_relation_label and subject_qnode_key and object_qnode_key:
            self.response.debug(f"Overlaying exposures data using virtual edge method "
                                f"({subject_qnode_key}--{self.virtual_relation_label}--{object_qnode_key})")
            self._add_virtual_edges(subject_qnode_key, object_qnode_key)
        else:
            self.response.debug(f"Overlaying exposures data using attribute method")
            self._decorate_existing_edges()

    def _add_virtual_edges(self, subject_qnode_key, object_qnode_key):
        # This function adds ICEES exposures data as virtual edges between nodes with the specified qnode IDs
        knowledge_graph = self.message.knowledge_graph
        query_graph = self.message.query_graph
        log = self.response
        nodes_by_qg_id = self._get_nodes_by_qg_id(knowledge_graph)
        subject_curies = set(nodes_by_qg_id.get(subject_qnode_key))
        object_curies = set(nodes_by_qg_id.get(object_qnode_key))
        # Determine which curies ICEES 'knows' about
        known_subject_curies = {curie for curie in subject_curies if self._get_accepted_synonyms(curie)}
        known_object_curies = {curie for curie in object_curies if self._get_accepted_synonyms(curie)}

        num_node_pairs_recognized = 0
        for subject_curie, object_curie in ou.get_node_pairs_to_overlay(subject_qnode_key, object_qnode_key, query_graph, knowledge_graph, log):
            # Query ICEES only for synonyms it 'knows' about
            if subject_curie in known_subject_curies and object_curie in known_object_curies:
                accepted_subject_synonyms = self._get_accepted_synonyms(subject_curie)
                accepted_object_synonyms = self._get_accepted_synonyms(object_curie)
                for subject_synonym, object_synonym in itertools.product(accepted_subject_synonyms, accepted_object_synonyms):
                    # qedge = QEdge(id=f"icees_{subject_synonym}--{object_synonym}",
                    #               subject_key=subject_synonym,
                    #               object_key=object_synonym)
                    qedge = QEdge(subject=subject_synonym,
                                  object=object_synonym)
                    qedge.id = f"icees_{subject_synonym}--{object_synonym}"
                    log.debug(f"Sending query to ICEES+ for {subject_synonym}--{object_synonym}")
                    p_value = self._get_icees_p_value_for_edge(qedge, log)
                    if p_value is not None:
                        num_node_pairs_recognized += 1
                        # Add a new virtual edge with this data
                        id, virtual_edge = self._create_icees_virtual_edge(subject_curie, object_curie, p_value)
                        old_id = id
                        while id in knowledge_graph.edges:
                            id = old_id+f".{random.randint(10**(9-1), (10**9)-1)}"
                        knowledge_graph.edges[id] = virtual_edge
                        if self.message.results is not None and len(self.message.results) > 0:
                            ou.update_results_with_overlay_edge(subject_knode_key=subject_curie, object_knode_key=object_curie, kedge_key=id, message=self.message, log=log)
                        break  # Don't worry about checking remaining synonym combos if we got results
            # Add an 'empty' virtual edge (p-value of None) if we couldn't find any results for this node pair #1009
            id, empty_virtual_edge = self._create_icees_virtual_edge(subject_curie, object_curie, None)
            while id in knowledge_graph.edges:
                id = old_id+f".{random.randint(10**(9-1), (10**9)-1)}"
            knowledge_graph.edges[id] = empty_virtual_edge

        # Add a qedge to the query graph that corresponds to our new virtual edges
        # new_qedge = QEdge(id=self.virtual_relation_label,
        #                   subject_key=subject_qnode_key,
        #                   object_key=object_qnode_key,
        #                   type=self.icees_edge_type,
        #                   option_group_id=ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
        #                                                                           query_graph, log))
        # Likely need to change this for TRAPI 1.0
        new_qedge = QEdge(subject=subject_qnode_key,
                          object=object_qnode_key,
                          predicate=self.icees_edge_type,
                          option_group_id=ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
                                                                                  query_graph, log))
        query_graph.edges[self.virtual_relation_label] = new_qedge

        if num_node_pairs_recognized:
            log.info(f"ICEES+ returned data for {num_node_pairs_recognized} node pairs")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any {subject_qnode_key}--{object_qnode_key} node pairs")

    def _decorate_existing_edges(self):
        # This function decorates all existing edges in the knowledge graph with ICEES data, stored in EdgeAttributes
        knowledge_graph = self.message.knowledge_graph
        log = self.response

        # Query ICEES for each edge in the knowledge graph that ICEES can provide data on (use known curies)
        num_edges_obtained_icees_data_for = 0
        edges_by_node_pair = self._get_edges_by_node_pair(knowledge_graph)  # Don't duplicate effort for parallel edges
        for node_pair_key, node_pair_edges in edges_by_node_pair.items():
            subject_key = node_pair_edges[0].subject
            object_key = node_pair_edges[0].object
            accepted_subject_synonyms = self._get_accepted_synonyms(subject_key)
            accepted_object_synonyms = self._get_accepted_synonyms(object_key)
            if accepted_subject_synonyms and accepted_object_synonyms:
                # Query ICEES for each possible combination of accepted subject/object synonyms
                for subject_curie_to_try, object_curie_to_try in itertools.product(accepted_subject_synonyms, accepted_object_synonyms):
                    qedge = QEdge(subject=subject_curie_to_try, object=object_curie_to_try)
                    qedge.id=f"icees_e00"
                    log.debug(f"Sending query to ICEES+ for {subject_curie_to_try}--{object_curie_to_try}")
                    p_value = self._get_icees_p_value_for_edge(qedge, log)
                    if p_value is not None:
                        num_edges_obtained_icees_data_for += len(node_pair_edges)
                        new_edge_attribute = self._create_icees_edge_attribute(p_value)
                        # Add the data as new EdgeAttributes on the existing edges with this subject/object ID
                        for edge in node_pair_edges:
                            if not edge.attributes:
                                edge.attributes = []
                            edge.attributes.append(new_edge_attribute)
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
            return set(list(formatted_synonyms)[:5])  # Only use first few equivalent curies if we don't know which they like

    def _get_icees_p_value_for_edge(self, qedge, log):
        # Note: ICEES doesn't quite accept ReasonerStdAPI, so we transform to what works
        qedges = [qedge.to_dict()]
        qnodes = [{"node_key": curie, "curie": curie} for curie in [qedge.subject, qedge.object]]
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
                    subject_key = edge.get("subject")
                    object_key = edge.get("object")
                    # Skip any self-edges and reverse edges in ICEES response
                    if subject_key == qedge.subject and object_key == qedge.object:
                        p_values += [attribute["p_value"] for attribute in edge.get("attributes", []) if attribute.get("p_value") is not None]
                if p_values:
                    average_p_value = sum(p_values) / len(p_values)
                    log.debug(f"Average returned p-value is {average_p_value}")
                    return average_p_value
        return None

    def _create_icees_edge_attribute(self, p_value):
        return EdgeAttribute(original_attribute_name=self.icees_attribute_name,
                             value=p_value,
                             attribute_type_id=self.icees_attribute_type)

    def _create_icees_virtual_edge(self, subject_curie, object_curie, p_value):
        id = f"ICEES:{subject_curie}--{object_curie}"
        # edge = Edge(id=f"ICEES:{subject_curie}--{object_curie}",
        #             type=self.icees_edge_type,
        #             subject_key=subject_curie,
        #             object_key=object_curie,
        #             is_defined_by="ARAX",
        #             provided_by="ICEES+",
        #             relation=self.virtual_relation_label,
        #             qedge_ids=[self.virtual_relation_label],
        #             attributes=[self._create_icees_edge_attribute(p_value)])
        provided_by = "infores:icees"
        edge_attribute_list = [
            self._create_icees_edge_attribute(p_value),
            EdgeAttribute(original_attribute_name="virtual_relation_label", value=self.virtual_relation_label, attribute_type_id="biolink:Unknown"),
            #EdgeAttribute(original_attribute_name="is_defined_by", value="ARAX", attribute_type_id="biolink:Unknown"),
            EdgeAttribute(original_attribute_name="provided_by", value=provided_by, attribute_type_id="biolink:aggregator_knowledge_source", attribute_source=provided_by, value_type_id="biolink:InformationResource"),
            EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="biolink:computed_value", attribute_source="infores:arax-reasoner-ara", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
            #EdgeAttribute(name="qedge_ids", value=[self.virtual_relation_label])
        ]
        edge = Edge(predicate=self.icees_edge_type, subject=subject_curie, object=object_curie,
                        attributes=edge_attribute_list)
        edge.qedge_keys=[self.virtual_relation_label]
        return id, edge

    @staticmethod
    def _get_nodes_by_qg_id(knowledge_graph):
        nodes_by_qg_key = dict()
        for key, node in knowledge_graph.nodes.items():
            for qnode_key in node.qnode_keys:
                if qnode_key not in nodes_by_qg_key:
                    nodes_by_qg_key[qnode_key] = dict()
                nodes_by_qg_key[qnode_key][key] = node
        return nodes_by_qg_key

    @staticmethod
    def _get_node_synonyms(knowledge_graph):
        synonymizer = NodeSynonymizer()
        node_keys = {key for key in knowledge_graph.nodes.keys()}
        equivalent_curie_info = synonymizer.get_equivalent_nodes(node_keys)
        return {node_key: set(equivalent_curies_dict) for node_key, equivalent_curies_dict in equivalent_curie_info.items()}

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
