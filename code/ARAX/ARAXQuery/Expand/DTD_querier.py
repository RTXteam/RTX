#!/bin/env python3
import sys
import os
import traceback
import ast
import itertools
import numpy as np
from typing import List, Dict, Tuple
from neo4j import GraphDatabase

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
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/ARAXQuery/")
from Overlay.predictor.predictor import predictor
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

class DTDQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.RTXConfig = RTXConfiguration()
        self.response = response_object
        self.synonymizer = NodeSynonymizer()

        ## check if the new model files exists in /predictor/retrain_data. If not, scp it from arax.ncats.io
        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])

        ## check if there is LogModel.pkl
        self.pkl_file = f"{filepath}/{self.RTXConfig.log_model_path.split('/')[-1]}"
        if os.path.exists(self.pkl_file):
            pass
        else:
            os.system(f"scp {self.RTXConfig.log_model_username}@{self.RTXConfig.log_model_host}:{self.RTXConfig.log_model_path} " + self.pkl_file)

        ## check if there is GRAPH.sqlite
        self.db_file = f"{filepath}/{self.RTXConfig.graph_database_path.split('/')[-1]}"
        if os.path.exists(self.db_file):
            pass
        else:
            os.system(f"scp {self.RTXConfig.graph_database_username}@{self.RTXConfig.graph_database_host}:{self.RTXConfig.graph_database_path} " + self.db_file)

        ## check if there is DTD_probability_database.db
        self.DTD_prob_db_file = f"{filepath}/{self.RTXConfig.dtd_prob_path.split('/')[-1]}"
        if os.path.exists(self.DTD_prob_db_file):
            pass
        else:
            os.system(f"scp {self.RTXConfig.dtd_prob_username}@{self.RTXConfig.dtd_prob_host}:{self.RTXConfig.dtd_prob_path} " + self.DTD_prob_db_file)

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using DTD database.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        # Set up the required parameters
        log = self.response
        self.count = 0
        self.DTD_threshold = float(self.response.data['parameters']['DTD_threshold'])
        DTD_slow_mode = self.response.data['parameters']['DTD_slow_mode']
        final_kg = QGOrganizedKnowledgeGraph()
        # Switch QG back to old style where category/predicate can be strings OR lists
        query_graph = eu.switch_back_to_str_or_list_types(query_graph)

        if 0.8 <= self.DTD_threshold <=1:
            if not DTD_slow_mode:
                # Use DTD database
                try:
                    self.pred = predictor(DTD_prob_file=self.DTD_prob_db_file, use_prob_db=True)
                except:
                    tb = traceback.format_exc()
                    error_type, error, _ = sys.exc_info()
                    log.error(tb, error_code=error_type.__name__)
                    log.error(f"Internal Error encountered connecting to the local DTD prediction database while expanding edges with kp=DTD.", error_code="DatabaseError")

                final_kg = self._answer_query_using_DTD_database(query_graph, log)
            else:
                # Use DTD model
                try:
                    self.pred = predictor(model_file=self.pkl_file, use_prob_db=False)
                except:
                    tb = traceback.format_exc()
                    error_type, error, _ = sys.exc_info()
                    self.response.error(tb, error_code=error_type.__name__)
                    self.response.error(f"Internal Error encountered connecting to the local LogModel.pkl file while expanding edges with kp=DTD.")
                try:
                    self.pred.import_file(None, graph_database=self.db_file)
                except:
                    tb = traceback.format_exc()
                    error_type, error, _ = sys.exc_info()
                    self.response.error(tb, error_code=error_type.__name__)
                    self.response.error(f"Internal Error encountered connecting to the local graph database file while expanding edges with kp=DTD.")

                final_kg = self._answer_query_using_DTD_model(query_graph, log)

        elif 0 <= self.DTD_threshold < 0.8:
            if not DTD_slow_mode:
                self.response.warning(f"Since DTD_threshold < 0.8, DTD_slow_mode=true is automatically set to call DTD model. Calling DTD model will be quite time-consuming.")
            else:
                pass
            # Use DTD model
            try:
                self.pred = predictor(model_file=self.pkl_file, use_prob_db=False)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Internal Error encountered connecting to the local LogModel.pkl file while expanding edges with kp=DTD.")
            try:
                self.pred.import_file(None, graph_database=self.db_file)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Internal Error encountered connecting to the local graph database file while expanding edges with kp=DTD.")

            final_kg = self._answer_query_using_DTD_model(query_graph, log)
        else:
            log.error("The 'DTD_threshold' in Expander should be between 0 and 1", error_code="ParameterError")


        return final_kg

    def _answer_query_using_DTD_database(self, query_graph: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using DTD database")
        final_kg = QGOrganizedKnowledgeGraph()
        drug_label_list = ['chemicalSubstance', 'drug']
        disease_label_list = ['disease', 'phenotypicFeature', 'diseaseorphenotypicfeature']
        # use for checking the requirement
        source_pass_nodes = None
        source_category = None
        target_pass_nodes = None
        target_category = None

        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]

        # check if both ends of edge have no curie
        if (source_qnode.id is None) and (target_qnode.id is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # check if the query nodes are drug or disease
        if source_qnode.id is not None:

            if type(source_qnode.id) is str:
                source_pass_nodes = [source_qnode.id]
            else:
                source_pass_nodes = source_qnode.id
            has_error, pass_nodes, not_pass_nodes = self._check_id(source_qnode.id, log)
            if has_error:
                return final_kg
            else:
                if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
                    source_pass_nodes = pass_nodes
                elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
                    source_pass_nodes = pass_nodes
                    if len(not_pass_nodes)==1:
                        log.warning(f"All potential categories of {not_pass_nodes[0]} don't contain drug or disease")
                    else:
                        log.warning(f"All potential categories of these nodes {not_pass_nodes} don't contain drug or disease")
                else:
                    if type(source_qnode.id) is str:
                        log.error(f"All potential categories of {source_qnode.id} don't contain drug or disease", error_code="CategoryError")
                        return final_kg
                    else:
                        log.error(f"All potential categories of {source_qnode.id} don't contain drug or disease", error_code="CategoryError")
                        return final_kg
        else:
            category = source_qnode.category.replace('biolink:','').replace('_','').lower()
            source_category = category
            if (category in drug_label_list) or (category in disease_label_list):
                source_category = category
            else:
                log.error(f"The category of query node {source_qnode_key} is unsatisfiable. It has to be drug or disase", error_code="CategoryError")
                return final_kg

        if target_qnode.id is not None:

            if type(target_qnode.id) is str:
                target_pass_nodes = [target_qnode.id]
            else:
                target_pass_nodes = target_qnode.id
            has_error, pass_nodes, not_pass_nodes = self._check_id(target_qnode.id, log)
            if has_error:
                return final_kg
            else:
                if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
                    target_pass_nodes = pass_nodes
                elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
                    target_pass_nodes = pass_nodes
                    if len(not_pass_nodes)==1:
                        log.warning(f"All potential categories of {not_pass_nodes[0]} don't contain drug or disease")
                    else:
                        log.warning(f"All potential categories of these nodes {not_pass_nodes} don't contain drug or disease")
                else:
                    if type(target_qnode.id) is str:
                        log.error(f"All potential categories of {target_qnode.id} don't contain drug or disease", error_code="CategoryError")
                        return final_kg
                    else:
                        log.error(f"All potential categories of {target_qnode.id} don't contain drug or disease", error_code="CategoryError")
                        return final_kg
        else:
            category = target_qnode.category.replace('biolink:','').replace('_','').lower()
            target_category = category
            if (category in drug_label_list) or (category in disease_label_list):
                target_category = category
            else:
                log.error(f"The category of query node {target_qnode_key} is unsatisfiable. It has to be drug or disase", error_code="CategoryError")
                return final_kg

        if (source_pass_nodes is None) and (target_pass_nodes is None):
            return final_kg

        elif (source_pass_nodes is not None) and (target_pass_nodes is not None):
            source_dict = dict()
            target_dict = dict()
            normalizer_result = self.synonymizer.get_canonical_curies(source_pass_nodes[0])
            all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[source_pass_nodes[0]]['all_categories'].keys())]
            if len(set(drug_label_list).intersection(set(all_types))) > 0:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'disease'
            normalizer_result = self.synonymizer.get_canonical_curies(target_pass_nodes[0])
            all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[target_pass_nodes[0]]['all_categories'].keys())]
            if len(set(drug_label_list).intersection(set(all_types))) > 0:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'disease'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg
            else:
                for (source_curie, target_curie) in itertools.product(source_pass_nodes, target_pass_nodes):

                    max_probability = -1

                    converted_source_curie = source_curie
                    converted_target_curie = target_curie
                    normalizer_result = self.synonymizer.get_canonical_curies(source_curie)
                    converted_source_curie = normalizer_result[source_curie]
                    normalizer_result = self.synonymizer.get_canonical_curies(target_curie)
                    converted_target_curie = normalizer_result[target_curie]
                    if source_category_temp == 'drug':
                        converted_source_curie = converted_source_curie['preferred_curie']
                        converted_target_curie = converted_target_curie['preferred_curie']
                    else:
                        temp = converted_source_curie['preferred_curie']
                        converted_source_curie = converted_target_curie['preferred_curie']
                        converted_target_curie = temp
                    probability = self.pred.get_prob_from_DTD_db(converted_source_curie, converted_target_curie)
                    if probability is not None:
                        if np.isfinite(probability):
                            max_probability = probability

                    if max_probability >= self.DTD_threshold:
                        if source_category_temp == 'drug':
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, target_curie, "probability_treats", max_probability)
                        else:
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, source_curie, "probability_treats", max_probability)

                        source_dict[source_curie] = source_qnode_key
                        target_dict[target_curie] = target_qnode_key

                        # Finally add the current edge to our answer knowledge graph
                        final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                    else:
                        continue

                # Add the nodes to our answer knowledge graph
                if len(source_dict) != 0:
                    for source_curie in source_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
                if len(target_dict) != 0:
                    for target_curie in target_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

                return final_kg

        elif source_pass_nodes is not None:
            source_dict = dict()
            target_dict = dict()

            normalizer_result = self.synonymizer.get_canonical_curies(source_pass_nodes[0])
            all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[source_pass_nodes[0]]['all_categories'].keys())]
            if len(set(drug_label_list).intersection(set(all_types))) > 0:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'disease'
            if target_category in drug_label_list:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'disease'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg
            else:
                if source_category_temp == 'drug':
                    for source_curie in source_pass_nodes:
                        normalizer_result = self.synonymizer.get_canonical_curies(source_curie)
                        res = self.pred.get_probs_from_DTD_db_based_on_drug([normalizer_result[source_curie]['preferred_curie']])
                        if res is not None:
                            res = [row for row in res if row[2]>=self.DTD_threshold and target_category in [item.replace('biolink:','').replace('_','').lower() for item in list(self.synonymizer.get_canonical_curies(row[0])[row[0]]['all_categories'].keys())]]

                            for row in res:
                                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, row[0], "probability_treats", row[2])

                                source_dict[source_curie] = source_qnode_key
                                target_dict[row[0]] = target_qnode_key

                                # Finally add the current edge to our answer knowledge graph
                                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                else:
                    for source_curie in source_pass_nodes:
                        normalizer_result = self.synonymizer.get_canonical_curies(source_curie)
                        res = self.pred.get_probs_from_DTD_db_based_on_disease([normalizer_result[source_curie]['preferred_curie']])
                        if res is not None:
                            res = [row for row in res if row[2]>=self.DTD_threshold and target_category in [item.replace('biolink:','').replace('_','').lower() for item in list(self.synonymizer.get_canonical_curies(row[0])[row[0]]['all_categories'].keys())]]

                            for row in res:
                                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[1], source_curie, "probability_treats", row[2])

                                source_dict[source_curie] = source_qnode_key
                                target_dict[row[1]] = target_qnode_key

                                # Finally add the current edge to our answer knowledge graph
                                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

                # Add the nodes to our answer knowledge graph
                if len(source_dict) != 0:
                    for source_curie in source_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
                if len(target_dict) != 0:
                    for target_curie in target_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

                return final_kg
        else:
            source_dict = dict()
            target_dict = dict()

            normalizer_result = self.synonymizer.get_canonical_curies(target_pass_nodes[0])
            all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[target_pass_nodes[0]]['all_categories'].keys())]
            if len(set(drug_label_list).intersection(set(all_types))) > 0:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'disease'
            if source_category in drug_label_list:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'disease'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg
            else:
                if target_category_temp == 'drug':
                    for target_curie in target_pass_nodes:
                        normalizer_result = self.synonymizer.get_canonical_curies(target_curie)
                        res = self.pred.get_probs_from_DTD_db_based_on_drug([normalizer_result[target_curie]['preferred_curie']])
                        if res is not None:
                            res = [row for row in res if row[2]>=self.DTD_threshold and source_category in [item.replace('biolink:','').replace('_','').lower() for item in list(self.synonymizer.get_canonical_curies(row[0])[row[0]]['all_categories'].keys())]]

                            for row in res:
                                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, row[0], "probability_treats", row[2])

                                source_dict[row[0]] = source_qnode_key
                                target_dict[target_curie] = target_qnode_key

                                # Finally add the current edge to our answer knowledge graph
                                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                else:
                    for target_curie in target_pass_nodes:
                        normalizer_result = self.synonymizer.get_canonical_curies(target_curie)
                        res = self.pred.get_probs_from_DTD_db_based_on_disease([normalizer_result[target_curie]['preferred_curie']])
                        if res is not None:
                            res = [row for row in res if row[2]>=self.DTD_threshold and source_category in [item.replace('biolink:','').replace('_','').lower() for item in list(self.synonymizer.get_canonical_curies(row[0])[row[0]]['all_categories'].keys())]]

                            for row in res:
                                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[1], target_curie, "probability_treats", row[2])

                                source_dict[row[1]] = source_qnode_key
                                target_dict[target_curie] = target_qnode_key

                                # Finally add the current edge to our answer knowledge graph
                                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

                # Add the nodes to our answer knowledge graph
                if len(source_dict) != 0:
                    for source_curie in source_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
                if len(target_dict) != 0:
                    for target_curie in target_dict:
                        swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                        final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

                return final_kg


    def _answer_query_using_DTD_model(self, query_graph: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using DTD model")
        final_kg = QGOrganizedKnowledgeGraph()
        drug_label_list = ['chemicalsubstance','drug']
        disease_label_list = ['disease','phenotypicfeature','diseaseorphenotypicfeature']
        # use for checking the requirement
        source_pass_nodes = None
        source_category = None
        target_pass_nodes = None
        target_category = None

        qedge = query_graph.edges[qedge_key]
        source_qnode_key = qedge.subject
        target_qnode_key = qedge.object
        source_qnode = query_graph.nodes[source_qnode_key]
        target_qnode = query_graph.nodes[target_qnode_key]

        # check if both ends of edge have no curie
        if (source_qnode.id is None) and (target_qnode.id is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # check if the query nodes are drug or disease
        if source_qnode.id is not None:

            if type(source_qnode.id) is str:
                source_pass_nodes = [source_qnode.id]
            else:
                source_pass_nodes = source_qnode.id
            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # has_error, pass_nodes, not_pass_nodes = self._check_id(source_qnode.id, log)
            # if has_error:
            #     return final_kg, edge_to_nodes_map
            # else:
            #     if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
            #         source_pass_nodes = pass_nodes
            #     elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
            #         source_pass_nodes = pass_nodes
            #         if len(not_pass_nodes)==1:
            #             log.warning(f"The preferred label of {not_pass_nodes[0]} is not drug or disease")
            #         else:
            #             log.warning(f"The preferred labels of {not_pass_nodes} are not drug or disease")
            #     else:
            #         if type(source_qnode.id) is str:
            #             log.error(f"The preferred label of {source_qnode.id} is not drug or disease", error_code="CategoryError")
            #             return final_kg, edge_to_nodes_map
            #         else:
            #             log.error(f"The preferred labels of {source_qnode.id} are not drug or disease", error_code="CategoryError")
            #             return final_kg, edge_to_nodes_map
        else:
            category = source_qnode.category.replace('biolink:','').replace('_','').lower()
            source_category = category
            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # if (category in drug_label_list) or (category in disease_label_list):
            #     source_category = category
            # else:
            #     log.error(f"The category of query node {source_qnode_key} is unsatisfiable", error_code="CategoryError")
            #     return final_kg, edge_to_nodes_map

        if target_qnode.id is not None:

            if type(target_qnode.id) is str:
                target_pass_nodes = [target_qnode.id]
            else:
                target_pass_nodes = target_qnode.id
            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # has_error, pass_nodes, not_pass_nodes = self._check_id(target_qnode.id, log)
            # if has_error:
            #     return final_kg, edge_to_nodes_map
            # else:
            #     if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
            #         target_pass_nodes = pass_nodes
            #     elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
            #         target_pass_nodes = pass_nodes
            #         if len(not_pass_nodes)==1:
            #             log.warning(f"The preferred label of {not_pass_nodes[0]} is not drug or disease")
            #         else:
            #             log.warning(f"The preferred labels of {not_pass_nodes} are not drug or disease")
            #     else:
            #         if type(target_qnode.id) is str:
            #             log.error(f"The preferred label of {target_qnode.id} is not drug or disease", error_code="CategoryError")
            #             return final_kg, edge_to_nodes_map
            #         else:
            #             log.error(f"The preferred labels of {target_qnode.id} are not drug or disease", error_code="CategoryError")
            #             return final_kg, edge_to_nodes_map
        else:
            category = target_qnode.category.replace('biolink:','').replace('_','').lower()
            target_category = category
            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # if (category in drug_label_list) or (category in disease_label_list):
            #     target_category = category
            # else:
            #     log.error(f"The category of query node {target_qnode_key} is unsatisfiable", error_code="CategoryError")
            #     return final_kg, edge_to_nodes_map

        if (source_pass_nodes is None) and (target_pass_nodes is None):
            return final_kg

        elif (source_pass_nodes is not None) and (target_pass_nodes is not None):
            source_dict = dict()
            target_dict = dict()

            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # normalizer_result = self.synonymizer.get_canonical_curies(source_pass_nodes[0])
            # preferred_type = normalizer_result[source_pass_nodes[0]]['preferred_type'].replace('biolink:','').replace('_','').lower()
            # if preferred_type in drug_label_list:
            #     source_category_temp = 'drug'
            # else:
            #     source_category_temp = 'disease'
            # normalizer_result = self.synonymizer.get_canonical_curies(target_pass_nodes[0])
            # preferred_type = normalizer_result[target_pass_nodes[0]]['preferred_type'].replace('biolink:','').replace('_','').lower()
            # if preferred_type in drug_label_list:
            #     target_category_temp = 'drug'
            # else:
            #     target_category_temp = 'disease'
            # if source_category_temp == target_category_temp:
            #     log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
            #     return final_kg, edge_to_nodes_map
            # else:
            for (source_curie, target_curie) in itertools.product(source_pass_nodes, target_pass_nodes):

                max_probability = -1
                normalizer_result = self.synonymizer.get_canonical_curies(source_curie)
                converted_source_curie = normalizer_result[source_curie]
                normalizer_result = self.synonymizer.get_canonical_curies(target_curie)
                converted_target_curie = normalizer_result[target_curie]
                # if source_category_temp == 'drug':
                #     converted_source_curie = converted_source_curie['preferred_curie']
                #     converted_target_curie = converted_target_curie['preferred_curie']
                # else:
                #     temp = converted_source_curie['preferred_curie']
                #     converted_source_curie = converted_target_curie['preferred_curie']
                #     converted_target_curie = temp
                # probability = self.pred.prob_single(converted_source_curie, converted_target_curie)
                probability = self.pred.prob_single(converted_source_curie['preferred_curie'], converted_target_curie['preferred_curie'])
                if probability is not None:
                    probability = probability[0]
                    if np.isfinite(probability):
                        max_probability = probability

                if max_probability >= self.DTD_threshold:
                    # if source_category_temp == 'drug':
                    swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, target_curie, "probability_treats", max_probability)
                    # else:
                    #     swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, source_curie, "probability_treats", max_probability)

                    source_dict[source_curie] = source_qnode_key
                    target_dict[target_curie] = target_qnode_key

                    # Finally add the current edge to our answer knowledge graph
                    final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                else:
                    continue

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_curie in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
            if len(target_dict) != 0:
                for target_curie in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

            return final_kg

        elif source_pass_nodes is not None:
            source_dict = dict()
            target_dict = dict()

            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # normalizer_result = self.synonymizer.get_canonical_curies(source_pass_nodes[0])
            # preferred_type = normalizer_result[source_pass_nodes[0]]['preferred_type'].replace('biolink:','').replace('_','').lower()
            # if preferred_type in drug_label_list:
            #     source_category_temp = 'drug'
            # else:
            #     source_category_temp = 'disease'
            # if target_category in drug_label_list:
            #     target_category_temp = 'drug'
            # else:
            #     target_category_temp = 'disease'
            # if source_category_temp == target_category_temp:
            #     log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
            #     return final_kg, edge_to_nodes_map
            # else:
            cypher_query = self._convert_one_hop_query_graph_to_cypher_query(query_graph, False, log)
            if log.status != 'OK':
                return final_kg
            neo4j_results = self._answer_query_using_neo4j(cypher_query, qedge_key, "KG2c", log)
            if log.status != 'OK':
                return final_kg
            results_table = neo4j_results[0]
            column_names = [column_name for column_name in results_table]
            res = [(neo4j_edge.get('n0'),neo4j_edge.get('n1')) for column_name in column_names if column_name.startswith('edges') for neo4j_edge in results_table.get(column_name)]
            if len(res) != 0:
                all_probabilities = self.pred.prob_all(res)
                if all_probabilities is not None:
                    res, all_probabilities = all_probabilities
                    res = [(res[index][0],res[index][1],all_probabilities[index]) for index in range(len(all_probabilities)) if np.isfinite(all_probabilities[index]) and res[index][0] in source_pass_nodes and all_probabilities[index] >= self.DTD_threshold]
                else:
                    return final_kg
            else:
                return final_kg

            # if source_category_temp == 'drug':
            for row in res:
                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[0], row[1], "probability_treats", row[2])

                source_dict[row[0]] = source_qnode_key
                target_dict[row[1]] = target_qnode_key

                # Finally add the current edge to our answer knowledge graph
                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
            # else:
            #     for row in res:
            #         swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[1], row[0], "probability_treats", row[2])

            #         source_dict[row[0]] = source_qnode_key
            #         target_dict[row[1]] = target_qnode_key

            #         # Record which of this edge's nodes correspond to which qnode_key
            #         if swagger_edge_key not in edge_to_nodes_map:
            #             edge_to_nodes_map[swagger_edge_key] = dict()
            #         edge_to_nodes_map[swagger_edge_key][source_qnode_key] = row[0]
            #         edge_to_nodes_map[swagger_edge_key][target_qnode_key] = row[1]

            #         # Finally add the current edge to our answer knowledge graph
            #         final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_curie in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
            if len(target_dict) != 0:
                for target_curie in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

            return final_kg
        else:
            source_dict = dict()
            target_dict = dict()

            # *The code below was commented because we don't need to check the type of input nodes #issue1240
            # normalizer_result = self.synonymizer.get_canonical_curies(target_pass_nodes[0])
            # preferred_type = normalizer_result[target_pass_nodes[0]]['preferred_type'].replace('biolink:','').replace('_','').lower()
            # if preferred_type in drug_label_list:
            #     target_category_temp = 'drug'
            # else:
            #     target_category_temp = 'disease'
            # if source_category in drug_label_list:
            #     source_category_temp = 'drug'
            # else:
            #     source_category_temp = 'disease'
            # if source_category_temp == target_category_temp:
            #     log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
            #     return final_kg, edge_to_nodes_map
            # else:
            cypher_query = self._convert_one_hop_query_graph_to_cypher_query(query_graph, False, log)
            if log.status != 'OK':
                return final_kg
            neo4j_results = self._answer_query_using_neo4j(cypher_query, qedge_key, "KG2c", log)
            if log.status != 'OK':
                return final_kg
            results_table = neo4j_results[0]
            column_names = [column_name for column_name in results_table]
            res = [(neo4j_edge.get('n0'),neo4j_edge.get('n1')) for column_name in column_names if column_name.startswith('edges') for neo4j_edge in results_table.get(column_name)]
            if len(res) != 0:
                all_probabilities = self.pred.prob_all(res)
                if all_probabilities is not None:
                    res, all_probabilities = all_probabilities
                    res = [(res[index][0],res[index][1],all_probabilities[index]) for index in range(len(all_probabilities)) if np.isfinite(all_probabilities[index]) and res[index][1] in target_pass_nodes and all_probabilities[index] >= self.DTD_threshold]
                else:
                    return final_kg
            else:
                return final_kg

                # if target_category_temp == 'drug':
                #     for row in res:
                #         swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[1], row[0], "probability_treats", row[2])

                #         source_dict[row[0]] = source_qnode_key
                #         target_dict[row[1]] = target_qnode_key

                #         # Record which of this edge's nodes correspond to which qnode_key
                #         if swagger_edge_key not in edge_to_nodes_map:
                #             edge_to_nodes_map[swagger_edge_key] = dict()
                #         edge_to_nodes_map[swagger_edge_key][source_qnode_key] = row[0]
                #         edge_to_nodes_map[swagger_edge_key][target_qnode_key] = row[1]

                #         # Finally add the current edge to our answer knowledge graph
                #         final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                # else:
            for row in res:
                swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(row[0], row[1], "probability_treats", row[2])

                source_dict[row[0]] = source_qnode_key
                target_dict[row[1]] = target_qnode_key

                # Finally add the current edge to our answer knowledge graph
                final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

            # Add the nodes to our answer knowledge graph
            if len(source_dict) != 0:
                for source_curie in source_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(source_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, source_dict[source_curie])
            if len(target_dict) != 0:
                for target_curie in target_dict:
                    swagger_node_key, swagger_node = self._convert_to_swagger_node(target_curie)
                    final_kg.add_node(swagger_node_key, swagger_node, target_dict[target_curie])

            return final_kg


    def _check_id(self, qnode_id, log):

        drug_label_list = ['chemicalsubstance','drug']
        disease_label_list = ['disease','phenotypicfeature','diseaseorphenotypicfeature']

        if type(qnode_id) is str:
            normalizer_result = self.synonymizer.get_canonical_curies(curies=[qnode_id], return_all_categories=True)
            if normalizer_result[qnode_id] is not None:
                all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[qnode_id]['all_categories'].keys())]
                if (len(set(drug_label_list).intersection(set(all_types))) > 0) or (len(set(disease_label_list).intersection(set(all_types))) > 0):
                    return [False, [qnode_id], []]
                else:
                    return [False, [], [qnode_id]]
            else:
                log.error(f"Query node '{qnode_id}' can't get its canonical curie from NodeSynonymizer", error_code="NoPreferredCurie")
                return [True, [], []]
        else:
            pass_nodes_drug_temp = list()
            pass_nodes_disease_temp = list()
            not_pass_nodes = list()
            normalizer_result = self.synonymizer.get_canonical_curies(curies=[qnode_id], return_all_categories=True)
            for curie in qnode_id:
                if normalizer_result[curie] is not None:
                    all_types = [item.replace('biolink:','').replace('_','').lower() for item in list(normalizer_result[curie]['all_categories'].keys())]
                    if (len(set(drug_label_list).intersection(set(all_types))) > 0):
                        pass_nodes_drug_temp += [curie]
                    elif (len(set(disease_label_list).intersection(set(all_types))) > 0):
                        pass_nodes_disease_temp += [curie]
                    else:
                        not_pass_nodes += [curie]
                else:
                    log.error(f"Query node '{curie}' can't get its canonical curie from NodeSynonymizer", error_code="NoPreferredCurie")
                    return [True, [], []]

            if len(pass_nodes_drug_temp)!=0 and len(pass_nodes_disease_temp) != 0:
                log.error(f"The preferred types of {qnode_id} contain both drug and disease", error_code="MixedTypes")
                return [True, [], []]
            else:
                pass_nodes = pass_nodes_drug_temp + pass_nodes_disease_temp
                return [False, pass_nodes, not_pass_nodes]

    def _convert_one_hop_query_graph_to_cypher_query(self, qg: QueryGraph, enforce_directionality: bool, log: ARAXResponse) -> str:
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        log.debug(f"Generating cypher for edge {qedge_key} query graph")
        try:
            # Build the match clause
            subject_qnode_key = qedge.subject
            object_qnode_key = qedge.object
            qedge_cypher = self._get_cypher_for_query_edge(qedge_key, qg, enforce_directionality)
            source_qnode_cypher = self._get_cypher_for_query_node(subject_qnode_key, qg)
            target_qnode_cypher = self._get_cypher_for_query_node(object_qnode_key, qg)
            match_clause = f"MATCH {source_qnode_cypher}{qedge_cypher}{target_qnode_cypher}"

            # Build the where clause
            where_fragments = []
            for qnode_key in [subject_qnode_key, object_qnode_key]:
                qnode = qg.nodes[qnode_key]
                if qnode.id and isinstance(qnode.id, list) and len(qnode.id) > 1:
                    where_fragments.append(f"{qnode_key}.id in {qnode.id}")
                if qnode.category:
                    qnode.category = eu.convert_to_list(qnode.category)
                    if len(qnode.category) > 1:
                        # Create where fragment that looks like 'n00:biolink:Disease OR n00:biolink:PhenotypicFeature..'
                        category_sub_fragments = [f"{qnode_key}:`{category}`" for category in qnode.category]
                        category_where_fragment = f"({' OR '.join(category_sub_fragments)})"
                        where_fragments.append(category_where_fragment)
            where_clause = f"WHERE {' AND '.join(where_fragments)}" if where_fragments else ""

            # Build the with clause
            source_qnode_col_name = f"nodes_{subject_qnode_key}"
            target_qnode_col_name = f"nodes_{object_qnode_key}"
            qedge_col_name = f"edges_{qedge_key}"
            # This line grabs the edge's ID and a record of which of its nodes correspond to which qnode ID
            extra_edge_properties = "{.*, " + f"id:ID({qedge_key}), {subject_qnode_key}:{subject_qnode_key}.id, {object_qnode_key}:{object_qnode_key}.id" + "}"
            with_clause = f"WITH collect(distinct {subject_qnode_key}) as {source_qnode_col_name}, " \
                          f"collect(distinct {object_qnode_key}) as {target_qnode_col_name}, " \
                          f"collect(distinct {qedge_key}{extra_edge_properties}) as {qedge_col_name}"

            # Build the return clause
            return_clause = f"RETURN {source_qnode_col_name}, {target_qnode_col_name}, {qedge_col_name}"

            cypher_query = f"{match_clause} {where_clause} {with_clause} {return_clause}"
            return cypher_query
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)
            return ""

    def _convert_to_swagger_edge(self, subject: str, object: str, name: str, value: float) -> Tuple[str, Edge]:
        swagger_edge = Edge()
        self.count = self.count + 1
        swagger_edge.predicate = f"biolink:{name}"
        swagger_edge.subject = subject
        swagger_edge.object = object
        swagger_edge_key = f"DTD:{subject}-{name}-{object}"
        swagger_edge.relation = None

        type = "EDAM:data_0951"
        url = "https://doi.org/10.1101/765305"

        swagger_edge.attributes = [Attribute(type=type, name=name, value=str(value), url=url),
                                   Attribute(name="provided_by", value="ARAX/DTD", type=eu.get_attribute_type("provided_by")),
                                   Attribute(name="is_defined_by", value="ARAX", type=eu.get_attribute_type("is_defined_by"))]

        return swagger_edge_key, swagger_edge

    def _convert_to_swagger_node(self, node_key: str) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = node_key
        swagger_node.name = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_name']
        swagger_node.description = None
        swagger_node.category = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_category']

        return swagger_node_key, swagger_node

    def _answer_query_using_neo4j(self, cypher_query: str, qedge_key: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, List[Dict[str, any]]]]:
        log.info(f"Sending cypher query for edge {qedge_key} to {kg_name} neo4j")
        results_from_neo4j = self._run_cypher_query(cypher_query, kg_name, log)
        if log.status == 'OK':
            columns_with_lengths = dict()
            for column in results_from_neo4j[0]:
                columns_with_lengths[column] = len(results_from_neo4j[0].get(column))
        return results_from_neo4j

    @staticmethod
    def _run_cypher_query(cypher_query: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, any]]:
        rtxc = RTXConfiguration()
        if "KG2" in kg_name:  # Flip into KG2 mode if that's our KP (rtx config is set to KG1 info by default)
            rtxc.live = kg_name
        try:
            driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
            with driver.session() as session:
                query_results = session.run(cypher_query).data()
            driver.close()
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Encountered an error interacting with {kg_name} neo4j. {tb}", error_code=error_type.__name__)
            return []
        else:
            return query_results

    @staticmethod
    def _get_cypher_for_query_node(qnode_key: str, qg: QueryGraph) -> str:
        qnode = qg.nodes[qnode_key]
        # Add in node label if there's only one category
        category_cypher = f":`{qnode.category[0]}`" if isinstance(qnode.category, list) and len(qnode.category) == 1 else ""
        if qnode.id and (isinstance(qnode.id, str) or len(qnode.id) == 1):
            curie = qnode.id if isinstance(qnode.id, str) else qnode.id[0]
            curie_cypher = f" {{id:'{curie}'}}"
        else:
            curie_cypher = ""
        qnode_cypher = f"({qnode_key}{category_cypher}{curie_cypher})"
        return qnode_cypher

    @staticmethod
    def _get_cypher_for_query_edge(qedge_key: str, qg: QueryGraph, enforce_directionality: bool) -> str:
        qedge = qg.edges[qedge_key]
        qedge_type_cypher = f":`{qedge.predicate}`" if qedge.predicate else ""
        full_qedge_cypher = f"-[{qedge_key}{qedge_type_cypher}]-"
        if enforce_directionality:
            full_qedge_cypher += ">"
        return full_qedge_cypher
