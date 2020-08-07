#!/bin/env python3
"""
This class overlays the knowledge graph with clinical exposures data from ICEES+. It currently adds the data in
EdgeAttributes tacked onto existing edges.
"""
import itertools
import sys
import os

import requests
import yaml

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.q_edge import QEdge
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class OverlayExposuresData:

    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.icees_curies = self._load_icees_known_curies(self.response)

    def overlay_exposures_data(self):
        self._decorate_edges()

    def _decorate_edges(self):
        knowledge_graph = self.message.knowledge_graph
        log = self.response

        # Grab our synonyms in one up front batch
        synonymizer = NodeSynonymizer()
        node_ids = {node.id for node in knowledge_graph.nodes}
        synonyms_dict = synonymizer.get_equivalent_nodes(node_ids, kg_name='KG2')

        # TODO: Adjust to query node pairs... (otherwise duplicating effort for parallel edges..)
        # Query ICEES for each edge in the knowledge graph that ICEES can provide data on (use known curies)
        num_edges_obtained_icees_data_for = 0
        for edge in knowledge_graph.edges:
            source_synonyms = synonyms_dict.get(edge.source_id, [edge.source_id])
            target_synonyms = synonyms_dict.get(edge.target_id, [edge.target_id])
            formatted_source_synonyms = [self._convert_curie_to_icees_preferred_format(curie) for curie in source_synonyms]
            formatted_target_synonyms = [self._convert_curie_to_icees_preferred_format(curie) for curie in target_synonyms]
            accepted_source_synonyms = self.icees_curies.intersection(set(formatted_source_synonyms))
            accepted_target_synonyms = self.icees_curies.intersection(set(formatted_target_synonyms))
            if not accepted_source_synonyms or not accepted_target_synonyms:
                log.debug(f"Could not find curies that ICEES accepts for edge {edge.id} ({edge.source_id}--{edge.target_id})")
            else:
                # Query ICEES for each possible combination of accepted source/target synonyms
                for source_curie_to_try, target_curie_to_try in itertools.product(accepted_source_synonyms, accepted_target_synonyms):
                    qedge = QEdge(id=f"icees_{edge.id}", source_id=source_curie_to_try, target_id=target_curie_to_try)
                    log.debug(f"Sending query to ICEES+ for {source_curie_to_try}--{target_curie_to_try}")
                    returned_edge_attributes = self._get_exposures_data_for_edge(qedge, log)
                    if returned_edge_attributes:
                        num_edges_obtained_icees_data_for += 1
                        log.debug(f"Got data back from ICEES+")
                        # Add the data as new EdgeAttributes on the current edge
                        if not edge.edge_attributes:
                            edge.edge_attributes = []
                        edge.edge_attributes += returned_edge_attributes
                        # Don't worry about checking remaining combos if we got results TODO: use lowest p-value?
                        break

        if num_edges_obtained_icees_data_for:
            log.info(f"Overlayed {num_edges_obtained_icees_data_for} edges with exposures data from ICEES+")
        else:
            log.warning(f"Could not find ICEES+ exposures data for any edges in the KG")

        return self.response

    def _add_virtual_edges(self):
        # Figure out 'relevant' node pairs

        # Grab synonyms for those node pairs and convert to preferred format, filter down to those accepted by ICEES

        # Query all possible combinations of accepted node pairs, until we get an answer (?) (or take lowest p-value?)

        # Add a virtual edge between each node pair (not synonym - but actual, in the KG)
        pass

    @staticmethod
    def _get_exposures_data_for_edge(qedge, log):
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
                            for edge_attribute in edge.get("edge_attributes", []):
                                all_edge_attributes.append(EdgeAttribute(name="icees_p-value",  # TODO: better naming?
                                                                         value=edge_attribute["p_value"],
                                                                         type="EDAM:data_1669"))
        return all_edge_attributes

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
