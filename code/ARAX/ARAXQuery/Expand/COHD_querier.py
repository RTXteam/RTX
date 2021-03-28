#!/bin/env python3
import sys
import os
import traceback
import ast
import itertools
import numpy as np
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/KnowledgeSources/COHD_local/scripts/")
from COHDIndex import COHDIndex
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

class COHDQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.cohdindex = COHDIndex()
        self.synonymizer = NodeSynonymizer()

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using COHD database.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        # Set up the required parameters
        log = self.response
        self.count = 0
        COHD_method = self.response.data['parameters']['COHD_method']
        COHD_method_percentile = self.response.data['parameters']['COHD_method_percentile']
        final_kg = QGOrganizedKnowledgeGraph()
        # Switch QG back to old style where category/predicate can be strings OR lists
        query_graph = eu.switch_back_to_str_or_list_types(query_graph)

        if COHD_method_percentile == 99:
            pass
        elif type(COHD_method_percentile) is str:
            try:
                COHD_method_percentile = float(COHD_method_percentile)
                if (COHD_method_percentile < 0) or (COHD_method_percentile > 100):
                    log.error("The 'COHD_method_percentile' in Expander should be between 0 and 100", error_code="ParameterError")
                    return final_kg
            except ValueError:
                log.error("The 'COHD_method_percentile' in Expander should be numeric", error_code="ParameterError")
                return final_kg
        else:
            log.error("The 'COHD_method_percentile' in Expander should be an float", error_code="ParameterError")
            return final_kg

        # Verify this is a valid one-hop query graph
        if len(query_graph.edges) != 1:
            log.error(f"COHDQuerier.answer_one_hop_query() was passed a query graph that is not one-hop: {query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg

        # Run the actual query and process results
        if COHD_method.lower() == 'paired_concept_freq':
            final_kg = self._answer_query_using_COHD_paired_concept_freq(query_graph, COHD_method_percentile, log)
        elif COHD_method.lower() == 'observed_expected_ratio':
            final_kg = self._answer_query_using_COHD_observed_expected_ratio(query_graph, COHD_method_percentile, log)
        elif COHD_method.lower() == 'chi_square':
            final_kg = self._answer_query_using_COHD_chi_square(query_graph, COHD_method_percentile, log)
        else:
            log.error(f"The parameter 'COHD_method' was passed an invalid option. The current allowed options are `paired_concept_freq`, `observed_expected_ratio`, `chi_square`.", error_code="InvalidParameterOption")

        return final_kg

    def _answer_query_using_COHD_paired_concept_freq(self, query_graph: QueryGraph, COHD_method_percentile: float, log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using paired concept frequency")
        final_kg = QGOrganizedKnowledgeGraph()
        # if COHD_method_threshold == float("inf"):
        #     threshold = pow(10, -3.365)  # default threshold based on the distribution of 0.99 quantile
        # else:
        #     threshold = COHD_method_threshold
        # log.info(f"The threshod used to filter paired concept frequency is {threshold}")

        # extract information from the QueryGraph
        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]

        # check if both ends of edge have no curie
        if (source_qnode.id is None) and (target_qnode.id is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # Convert curie ids to OMOP ids
        if source_qnode.id is not None:
            source_qnode_omop_ids = self._get_omop_id_from_curies(source_qnode_key, query_graph, log)
        else:
            source_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg
        if target_qnode.id is not None:
            target_qnode_omop_ids = self._get_omop_id_from_curies(target_qnode_key, query_graph, log)
        else:
            target_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg

        # expand edges according to the OMOP id pairs
        if (source_qnode_omop_ids is None) and (target_qnode_omop_ids is None):
            return final_kg

        elif (source_qnode_omop_ids is not None) and (target_qnode_omop_ids is not None):
            source_dict = dict()
            target_dict = dict()
            average_threshold = 0
            count = 0
            for (source_preferred_key, target_preferred_key) in itertools.product(list(source_qnode_omop_ids.keys()), list(target_qnode_omop_ids.keys())):

                if source_qnode.category is None and target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        continue
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                frequency = 0
                threshold1 = np.percentile([row['concept_frequency'] for row in self.cohdindex.get_paired_concept_freq(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3) if row['concept_frequency'] != 0], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. 0
                threshold2 = np.percentile([row['concept_frequency'] for row in self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3) if row['concept_frequency'] != 0], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. 0
                threshold = min(threshold1, threshold2)  # pick the minimum one for threshold
                average_threshold = average_threshold + threshold
                count = count + 1
                omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(source_qnode_omop_ids[source_preferred_key], target_qnode_omop_ids[target_preferred_key])]
                if len(omop_pairs) != 0:
                    res = self.cohdindex.get_paired_concept_freq(concept_id_pair=omop_pairs, dataset_id=3)  # use the hierarchical dataset
                    if len(res) != 0:
                        maximum_concept_frequency = res[0]['concept_frequency']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                        frequency = maximum_concept_frequency
                value = frequency
                if value >= threshold:
                    swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "paired_concept_frequency", value)
                else:
                    continue

                source_dict[source_preferred_key] = source_qnode_key
                target_dict[target_preferred_key] = target_qnode_key

                # Finally add the current edge to our answer knowledge graph
                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of paired concept frequency is {threshold/count}")

            return final_kg

        elif source_qnode_omop_ids is not None:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for source_preferred_key in source_qnode_omop_ids:

                if source_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        log.warning(f"The preferred type of source preferred id '{source_preferred_key}' can't match to the given source type '{source_qnode.category}''")
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                new_edge[source_preferred_key] = dict()
                threshold = np.percentile([row['concept_frequency'] for row in self.cohdindex.get_paired_concept_freq(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3) if row['concept_frequency'] != 0], COHD_method_percentile)
                average_threshold = average_threshold + threshold
                count = count + 1
                freq_data_list = [row for row in self.cohdindex.get_paired_concept_freq(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3) if row['concept_frequency'] >= threshold]
                for freq_data in freq_data_list:
                    if target_qnode.category is None:
                        preferred_target_list = self.cohdindex.get_curies_from_concept_id(freq_data['concept_id_2'])
                    else:
                        preferred_target_list = [preferred_target_curie for preferred_target_curie in self.cohdindex.get_curies_from_concept_id(freq_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_target_curie)[preferred_target_curie]['preferred_category'] == target_qnode.category]

                    for target_preferred_key in preferred_target_list:
                        if target_preferred_key not in new_edge[source_preferred_key]:
                            new_edge[source_preferred_key][target_preferred_key] = freq_data['concept_frequency']
                        else:
                            if freq_data['concept_frequency'] > new_edge[source_preferred_key][target_preferred_key]:
                                new_edge[source_preferred_key][target_preferred_key] = freq_data['concept_frequency']

                if len(new_edge[source_preferred_key]) != 0:
                    for target_preferred_key in new_edge[source_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "paired_concept_frequency", new_edge[source_preferred_key][target_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of paired concept frequency is {threshold/count}")

            return final_kg

        else:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for target_preferred_key in target_qnode_omop_ids:

                if target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                new_edge[target_preferred_key] = dict()
                threshold = np.percentile([row['concept_frequency'] for row in self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3) if row['concept_frequency'] != 0], COHD_method_percentile)
                average_threshold = average_threshold + threshold
                count = count + 1
                freq_data_list = [row for row in self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3) if row['concept_frequency'] >= threshold]
                for freq_data in freq_data_list:
                    if source_qnode.category is None:
                        preferred_source_list = self.cohdindex.get_curies_from_concept_id(freq_data['concept_id_2'])
                    else:
                        preferred_source_list = [preferred_source_curie for preferred_source_curie in self.cohdindex.get_curies_from_concept_id(freq_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_source_curie)[preferred_source_curie]['preferred_category'] == source_qnode.category]

                    for source_preferred_key in preferred_source_list:
                        if source_preferred_key not in new_edge[target_preferred_key]:
                            new_edge[target_preferred_key][source_preferred_key] = freq_data['concept_frequency']
                        else:
                            if freq_data['concept_frequency'] > new_edge[target_preferred_key][source_preferred_key]:
                                new_edge[target_preferred_key][source_preferred_key] = freq_data['concept_frequency']

                if len(new_edge[target_preferred_key]) != 0:
                    for source_preferred_key in new_edge[target_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "paired_concept_frequency", new_edge[target_preferred_key][source_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of paired concept frequency is {threshold/count}")

            return final_kg

    def _answer_query_using_COHD_observed_expected_ratio(self, query_graph: QueryGraph, COHD_method_percentile: float, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using natural logarithm of observed expected ratio")
        final_kg = QGOrganizedKnowledgeGraph()
        # if COHD_method_threshold == float("inf"):
        #     threshold = 4.44  # default threshold based on the distribution of 0.99 quantile
        # else:
        #     threshold = COHD_method_threshold
        # log.info(f"The threshod used to filter natural logarithm of observed expected ratio is {threshold}")

        # extract information from the QueryGraph
        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]

        # check if both ends of edge have no curie
        if (source_qnode.id is None) and (target_qnode.id is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # Convert curie ids to OMOP ids
        if source_qnode.id is not None:
            source_qnode_omop_ids = self._get_omop_id_from_curies(source_qnode_key, query_graph, log)
        else:
            source_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg
        if target_qnode.id is not None:
            target_qnode_omop_ids = self._get_omop_id_from_curies(target_qnode_key, query_graph, log)
        else:
            target_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg

        # expand edges according to the OMOP id pairs
        if (source_qnode_omop_ids is None) and (target_qnode_omop_ids is None):
            return final_kg

        elif (source_qnode_omop_ids is not None) and (target_qnode_omop_ids is not None):
            source_dict = dict()
            target_dict = dict()
            average_threshold = 0
            count = 0
            for (source_preferred_key, target_preferred_key) in itertools.product(list(source_qnode_omop_ids.keys()), list(target_qnode_omop_ids.keys())):

                if source_qnode.category is None and target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        continue
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                value = float("-inf")
                threshold1 = np.percentile([row['ln_ratio'] for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] != float("-inf")], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. -inf
                threshold2 = np.percentile([row['ln_ratio'] for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] != float("-inf")], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. -inf
                threshold = min(threshold1, threshold2)  # pick the minimum one for threshold
                average_threshold = average_threshold + threshold
                count = count + 1
                omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(source_qnode_omop_ids[source_preferred_key], target_qnode_omop_ids[target_preferred_key])]
                if len(omop_pairs) != 0:
                    res = self.cohdindex.get_obs_exp_ratio(concept_id_pair=omop_pairs, domain="", dataset_id=3)  # use the hierarchical dataset
                    if len(res) != 0:
                        maximum_ln_ratio = res[0]['ln_ratio']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                        value = maximum_ln_ratio
                if value >= threshold:
                    swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "ln_observed_expected_ratio", value)
                else:
                    continue

                source_dict[source_preferred_key] = source_qnode_key
                target_dict[target_preferred_key] = target_qnode_key

                # Finally add the current edge to our answer knowledge graph
                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of natural logarithm of observed expected ratio is {threshold/count}")

            return final_kg

        elif source_qnode_omop_ids is not None:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for source_preferred_key in source_qnode_omop_ids:

                if source_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                new_edge[source_preferred_key] = dict()
                threshold = np.percentile([row['ln_ratio'] for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] != float("-inf")], COHD_method_percentile)
                average_threshold = average_threshold + threshold
                count = count + 1
                ln_ratio_data_list = [row for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] >= threshold]
                for ln_ratio_data in ln_ratio_data_list:
                    if target_qnode.category is None:
                        preferred_target_list = self.cohdindex.get_curies_from_concept_id(ln_ratio_data['concept_id_2'])
                    else:
                        preferred_target_list = [preferred_target_curie for preferred_target_curie in self.cohdindex.get_curies_from_concept_id(ln_ratio_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_target_curie)[preferred_target_curie]['preferred_category'] == target_qnode.category]

                    for target_preferred_key in preferred_target_list:
                        if target_preferred_key not in new_edge[source_preferred_key]:
                            new_edge[source_preferred_key][target_preferred_key] = ln_ratio_data['ln_ratio']
                        else:
                            if ln_ratio_data['ln_ratio'] > new_edge[source_preferred_key][target_preferred_key]:
                                new_edge[source_preferred_key][target_preferred_key] = ln_ratio_data['ln_ratio']

                if len(new_edge[source_preferred_key]) != 0:
                    for target_preferred_key in new_edge[source_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "ln_observed_expected_ratio", new_edge[source_preferred_key][target_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of natural logarithm of observed expected ratio is {threshold/count}")
            return final_kg

        else:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for target_preferred_key in target_qnode_omop_ids:

                if target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                new_edge[target_preferred_key] = dict()
                threshold = np.percentile([row['ln_ratio'] for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] != float("-inf")], COHD_method_percentile)
                average_threshold = average_threshold + threshold
                count = count + 1
                ln_ratio_data_list = [row for row in self.cohdindex.get_obs_exp_ratio(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['ln_ratio'] >= threshold]
                for ln_ratio_data in ln_ratio_data_list:
                    if source_qnode.category is None:
                        preferred_source_list = self.cohdindex.get_curies_from_concept_id(ln_ratio_data['concept_id_2'])
                    else:
                        preferred_source_list = [preferred_source_curie for preferred_source_curie in self.cohdindex.get_curies_from_concept_id(ln_ratio_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_source_curie)[preferred_source_curie]['preferred_category'] == source_qnode.category]

                    for source_preferred_key in preferred_source_list:
                        if source_preferred_key not in new_edge[target_preferred_key]:
                            new_edge[target_preferred_key][source_preferred_key] = ln_ratio_data['ln_ratio']
                        else:
                            if ln_ratio_data['ln_ratio'] > new_edge[target_preferred_key][source_preferred_key]:
                                new_edge[target_preferred_key][source_preferred_key] = ln_ratio_data['ln_ratio']

                if len(new_edge[target_preferred_key]) != 0:
                    for source_preferred_key in new_edge[target_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "ln_observed_expected_ratio", new_edge[target_preferred_key][source_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of natural logarithm of observed expected ratio is {threshold/count}")
            return final_kg

    def _answer_query_using_COHD_chi_square(self, query_graph: QueryGraph, COHD_method_percentile: float, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using chi square pvalue")
        final_kg = QGOrganizedKnowledgeGraph()
        # if COHD_method_threshold == float("inf"):
        #     threshold = pow(10, -270.7875)  # default threshold based on the distribution of 0.99 quantile
        # else:
        #     threshold = COHD_method_threshold
        # log.info(f"The threshod used to filter chi square pvalue is {threshold}")

        # extract information from the QueryGraph
        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]

        # check if both ends of edge have no curie
        if (source_qnode.id is None) and (target_qnode.id is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # Convert curie ids to OMOP ids
        if source_qnode.id is not None:
            source_qnode_omop_ids = self._get_omop_id_from_curies(source_qnode_key, query_graph, log)
        else:
            source_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg
        if target_qnode.id is not None:
            target_qnode_omop_ids = self._get_omop_id_from_curies(target_qnode_key, query_graph, log)
        else:
            target_qnode_omop_ids = None
        if log.status != 'OK':
            return final_kg

        # expand edges according to the OMOP id pairs
        if (source_qnode_omop_ids is None) and (target_qnode_omop_ids is None):
            return final_kg

        elif (source_qnode_omop_ids is not None) and (target_qnode_omop_ids is not None):
            source_dict = dict()
            target_dict = dict()
            average_threshold = 0
            count = 0
            for (source_preferred_key, target_preferred_key) in itertools.product(list(source_qnode_omop_ids.keys()), list(target_qnode_omop_ids.keys())):

                if source_qnode.category is None and target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        continue
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept ids was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                value = float("inf")
                threshold1 = np.percentile([row['p-value'] for row in self.cohdindex.get_chi_square(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['p-value'] != 0], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. 0
                threshold2 = np.percentile([row['p-value'] for row in self.cohdindex.get_chi_square(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['p-value'] != 0], COHD_method_percentile)  # calculate the percentile after removing the extreme value e.g. 0
                threshold = max(threshold1, threshold2)  # pick the maximum one for threshold
                average_threshold = average_threshold + threshold
                count = count + 1
                omop_pairs = [f"{omop1}_{omop2}" for (omop1, omop2) in itertools.product(source_qnode_omop_ids[source_preferred_key], target_qnode_omop_ids[target_preferred_key])]

                if len(omop_pairs) != 0:
                    res = self.cohdIndex.get_chi_square(concept_id_pair=omop_pairs, domain="", dataset_id=3)  # use the hierarchical dataset
                    if len(res) != 0:
                        minimum_pvalue = res[0]['p-value']  # the result returned from get_paired_concept_freq was sorted by decreasing order
                        value = minimum_pvalue

                if value <= threshold:
                    swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "chi_square_pvalue", value)
                else:
                    continue

                source_dict[source_preferred_key] = source_qnode_key
                target_dict[target_preferred_key] = target_qnode_key

                # Finally add the current edge to our answer knowledge graph
                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of chi square pvalue is {threshold/count}")
            return final_kg

        elif source_qnode_omop_ids is not None:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for source_preferred_key in source_qnode_omop_ids:

                if source_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(source_preferred_key)[source_preferred_key]['preferred_category'] == source_qnode.category:
                        pass
                    else:
                        continue

                if len(source_qnode_omop_ids[source_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                elif len(self.cohdindex.get_obs_exp_ratio(concept_id_1=source_qnode_omop_ids[source_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for source preferred id '{source_preferred_key}'' with qnode id '{qedge.subject}'")
                    continue
                else:
                    pass

                new_edge[source_preferred_key] = dict()
                threshold = np.percentile([row['p-value'] for row in self.cohdindex.get_chi_square(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['p-value'] != 0], (100 - COHD_method_percentile))
                average_threshold = average_threshold + threshold
                count = count + 1
                pvalue_data_list = [row for row in self.cohdindex.get_chi_square(concept_id_1=source_qnode_omop_ids[source_preferred_key], domain="", dataset_id=3) if row['p-value'] <= threshold]
                for pvalue_data in pvalue_data_list:
                    if target_qnode.category is None:
                        preferred_target_list = self.cohdindex.get_curies_from_concept_id(pvalue_data['concept_id_2'])
                    else:
                        preferred_target_list = [preferred_target_curie for preferred_target_curie in self.cohdindex.get_curies_from_concept_id(pvalue_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_target_curie)[preferred_target_curie]['preferred_category'] == target_qnode.category]

                    for target_preferred_key in preferred_target_list:
                        if target_preferred_key not in new_edge[source_preferred_key]:
                            new_edge[source_preferred_key][target_preferred_key] = pvalue_data['p-value']
                        else:
                            if pvalue_data['p-value'] < new_edge[source_preferred_key][target_preferred_key]:
                                new_edge[source_preferred_key][target_preferred_key] = pvalue_data['p-value']

                if len(new_edge[source_preferred_key]) != 0:
                    for target_preferred_key in new_edge[source_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "chi_square_pvalue", new_edge[source_preferred_key][target_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of chi square pvalue is {threshold/count}")

            return final_kg

        else:
            source_dict = dict()
            target_dict = dict()
            new_edge = dict()
            average_threshold = 0
            count = 0
            for target_preferred_key in target_qnode_omop_ids:

                if target_qnode.category is None:
                    pass
                else:
                    if self.synonymizer.get_canonical_curies(target_preferred_key)[target_preferred_key]['preferred_category'] == target_qnode.category:
                        pass
                    else:
                        continue

                if len(target_qnode_omop_ids[target_preferred_key]) == 0:
                    log.warning(f"No OMOP concept id was found for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                elif len(self.cohdindex.get_paired_concept_freq(concept_id_1=target_qnode_omop_ids[target_preferred_key], dataset_id=3)) == 0:
                    log.warning(f"No paired concept frequency was found from COHD database for target preferred id '{target_preferred_key}'' with qnode id '{qedge.object}'")
                    continue
                else:
                    pass

                new_edge[target_preferred_key] = dict()
                threshold = np.percentile([row['p-value'] for row in self.cohdindex.get_chi_square(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['p-value'] != 0], COHD_method_percentile)
                average_threshold = average_threshold + threshold
                count = count + 1
                pvalue_data_list = [row for row in self.cohdindex.get_chi_square(concept_id_1=target_qnode_omop_ids[target_preferred_key], domain="", dataset_id=3) if row['p-value'] <= threshold]
                for pvalue_data in pvalue_data_list:
                    if source_qnode.category is None:
                        preferred_source_list = self.cohdindex.get_curies_from_concept_id(pvalue_data['concept_id_2'])
                    else:
                        preferred_source_list = [preferred_source_curie for preferred_source_curie in self.cohdindex.get_curies_from_concept_id(pvalue_data['concept_id_2']) if self.synonymizer.get_canonical_curies(preferred_source_curie)[preferred_source_curie]['preferred_category'] == source_qnode.category]

                    for source_preferred_key in preferred_source_list:
                        if source_preferred_key not in new_edge[target_preferred_key]:
                            new_edge[target_preferred_key][source_preferred_key] = pvalue_data['p-value']
                        else:
                            if pvalue_data['p-value'] < new_edge[target_preferred_key][source_preferred_key]:
                                new_edge[target_preferred_key][source_preferred_key] = pvalue_data['p-value']

                if len(new_edge[target_preferred_key]) != 0:
                    for source_preferred_key in new_edge[target_preferred_key]:
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_preferred_key, target_preferred_key, "chi_square_pvalue", new_edge[target_preferred_key][source_preferred_key])

                        source_dict[source_preferred_key] = source_qnode_key
                        target_dict[target_preferred_key] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_preferred_key in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_preferred_key])
            if len(target_dict) != 0:
                for target_preferred_key in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_preferred_key)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_preferred_key])

            if count != 0:
                log.info(f"The average threshold based on {COHD_method_percentile}th percentile of chi square pvalue is {threshold/count}")

            return final_kg

    def _get_omop_id_from_curies(self, qnode_key: str, qg: QueryGraph, log: ARAXResponse) -> Dict[str, list]:
        log.info(f"Getting the OMOP id for {qnode_key}")
        qnode = qg.nodes[qnode_key]

        # check if the input qnode is valid
        if not isinstance(qnode.id, str) and not isinstance(qnode.id, list):
            log.error(f"{qnode_key} has no curie id", error_code="NoCurie")
            return {}

        res_dict = {}
        if isinstance(qnode.id, str):
            # res = self.synonymizer.get_canonical_curies(curies=qnode.id)
            # if res[qnode.id] is None:
            #     log.error("Can't find the preferred curie for {qnode.id}", error_code="NoPreferredCurie")
            #     return {}
            # else:
            #     preferred_curie = res[qnode.id]['preferred_curie']
            try:
                omop_ids = self.cohdindex.get_concept_ids(qnode.id)
            except:
                log.error(f"Internal error accessing local COHD database.", error_code="DatabaseError")
                return {}
            res_dict[qnode.id] = omop_ids

        else:
            # classify the curies based on the preferred curie
            # res = self.synonymizer.get_canonical_curies(curies=qnode.id)
            # for curie in res:
            #     if res[curie] is None:
            #         log.error("Can't find the preferred curie for {curie}", error_code="NoPreferredCurie")
            #         return {}
            #     else:
            #         if res[curie]['preferred_curie'] not in res_dict:
            #             res_dict[res[curie]['preferred_curie']] = []

            for curie in qnode.id:
                try:
                    omop_ids = self.cohdindex.get_concept_ids(curie)
                except:
                    log.error(f"Internal error accessing local COHD database.", error_code="DatabaseError")
                    return {}
                res_dict[curie] = omop_ids

        return res_dict

    def _convert_to_swagger_edge(self, subject: str, object: str, name: str, value: float) -> Tuple[str, Edge]:
        swagger_edge = Edge()
        self.count = self.count + 1
        swagger_edge.predicate = f"biolink:has_{name}_with"
        swagger_edge.subject = subject
        swagger_edge.object = object
        swagger_edge_key = f"COHD:{subject}-has_{name}_with-{object}"
        swagger_edge.relation = None

        type = "EDAM:data_0951"
        url = "http://cohd.smart-api.info/"

        swagger_edge.attributes = [Attribute(type=type, name=name, value=str(value), url=url),
                                   Attribute(name="provided_by", value="ARAX/COHD", type=eu.get_attribute_type("provided_by")),
                                   Attribute(name="is_defined_by", value="ARAX", type=eu.get_attribute_type("is_defined_by"))]

        return swagger_edge_key, swagger_edge

    def _convert_to_swagger_node(self, node_key: str) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = node_key
        swagger_node.name = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_name']
        swagger_node.description = None
        swagger_node.category = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_category']

        return swagger_node_key, swagger_node
