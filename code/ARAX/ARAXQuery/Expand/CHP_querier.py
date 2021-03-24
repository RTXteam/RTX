#!/bin/env python3
import sys
import os
import traceback
import ast
import itertools
import numpy as np
from typing import List, Dict, Tuple
from neo4j import GraphDatabase
from chp_client import get_client
from chp_client.query import build_query

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
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

class CHPQuerier:

    def __init__(self, response_object: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        self.response = response_object
        self.synonymizer = NodeSynonymizer()
        self.kp_name = "CHP"
        # Instantiate a client
        self.client = get_client()

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using CHP client.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_keys for each edge. Example:
              {'CHP:111221': {'n00': 'ENSEMBL:ENSG00000132155', 'n01': 'CHEMBL.COMPOUND:CHEMBL88'}, 'CHP:111223': {'n00': 'ENSEMBL:ENSG00000141510', 'n01': 'CHEMBL.COMPOUND:CHEMBL88'}}
        """
        # Set up the required parameters
        log = self.response
        self.CHP_survival_threshold = float(self.response.data['parameters']['CHP_survival_threshold'])
        allowable_curies = self.client.curies()
        self.allowable_gene_curies = list(allowable_curies['biolink:Gene'].keys())
        self.allowable_drug_curies = [curie_id.replace('CHEMBL:','CHEMBL.COMPOUND:') for curie_id in list(allowable_curies['biolink:Drug'].keys())]
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()

        final_kg, edge_to_nodes_map = self._answer_query_using_CHP_client(query_graph, log)

        return final_kg, edge_to_nodes_map

    def _answer_query_using_CHP_client(self, query_graph: QueryGraph, log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using CHP client")
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        gene_label_list = ['gene']
        drug_label_list = ['drug', 'chemicalsubstance']
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
            return final_kg, edge_to_nodes_map

        # check if the query nodes are drug or disease
        if source_qnode.id is not None:

            if type(source_qnode.id) is str:
                source_pass_nodes = [source_qnode.id]
            else:
                source_pass_nodes = source_qnode.id
            has_error, pass_nodes, not_pass_nodes = self._check_id(source_qnode.id, log)
            if has_error:
                return final_kg, edge_to_nodes_map
            else:
                if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
                    source_pass_nodes = pass_nodes
                elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
                    source_pass_nodes = pass_nodes
                    if len(not_pass_nodes)==1:
                        log.warning(f"The curie id of {not_pass_nodes[0]} is not allowable based on CHP client")
                    else:
                        log.warning(f"The curie ids of these nodes {not_pass_nodes} are not allowable based on CHP client")
                else:
                    if type(source_qnode.id) is str:
                        log.error(f"The curie id of {source_qnode.id} is not allowable based on CHP client", error_code="NotAllowable")
                        return final_kg, edge_to_nodes_map
                    else:
                        log.error(f"The curie ids of {source_qnode.id} are not allowable based on CHP client", error_code="NotAllowable")
                        return final_kg, edge_to_nodes_map
        else:
            category = source_qnode.category.replace('biolink:','').replace('_','').lower()
            source_category = category
            if (category in drug_label_list) or (category in gene_label_list):
                source_category = category
            else:
                log.error(f"The category of query node {source_qnode_key} is unsatisfiable. It has to be drug/chemical_substance or gene", error_code="CategoryError")
                return final_kg, edge_to_nodes_map

        if target_qnode.id is not None:

            if type(target_qnode.id) is str:
                target_pass_nodes = [target_qnode.id]
            else:
                target_pass_nodes = target_qnode.id
            has_error, pass_nodes, not_pass_nodes = self._check_id(target_qnode.id, log)
            if has_error:
                return final_kg, edge_to_nodes_map
            else:
                if len(not_pass_nodes)==0 and len(pass_nodes)!=0:
                    target_pass_nodes = pass_nodes
                elif len(not_pass_nodes)!=0 and len(pass_nodes)!=0:
                    target_pass_nodes = pass_nodes
                    if len(not_pass_nodes)==1:
                        log.warning(f"The curie id of {not_pass_nodes[0]} is not allowable based on CHP client")
                    else:
                        log.warning(f"The curie ids of these nodes {not_pass_nodes} are not allowable based on CHP client")
                else:
                    if type(target_qnode.id) is str:
                        log.error(f"The curie id of {target_qnode.id} is not allowable based on CHP client", error_code="CategoryError")
                        return final_kg, edge_to_nodes_map
                    else:
                        log.error(f"The curie ids of {target_qnode.id} are not allowable based on CHP client", error_code="CategoryError")
                        return final_kg, edge_to_nodes_map
        else:
            category = target_qnode.category.replace('biolink:','').replace('_','').lower()
            target_category = category
            if (category in drug_label_list) or (category in gene_label_list):
                target_category = category
            else:
                log.error(f"The category of query node {target_qnode_key} is unsatisfiable. It has to be drug/chemical_substance or gene", error_code="CategoryError")
                return final_kg, edge_to_nodes_map

        if (source_pass_nodes is None) and (target_pass_nodes is None):
            return final_kg, edge_to_nodes_map

        elif (source_pass_nodes is not None) and (target_pass_nodes is not None):
            source_dict = dict()
            target_dict = dict()
            if source_pass_nodes[0] in self.allowable_drug_curies:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'gene'
            if target_pass_nodes[0] in self.allowable_drug_curies:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'gene'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg, edge_to_nodes_map
            else:
                for (source_curie, target_curie) in itertools.product(source_pass_nodes, target_pass_nodes):

                    if source_category_temp == 'drug':
                        source_curie_temp = source_curie.replace('CHEMBL.COMPOUND:','CHEMBL:')
                        # Let's build a simple single query
                        q = build_query(genes=[target_curie],
                                        therapeutic=source_curie_temp,
                                        disease='MONDO:0007254',
                                        outcome=('EFO:0000714', '>=', self.CHP_survival_threshold))

                        response = self.client.query(q)
                        max_probability = self.client.get_outcome_prob(response)
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, source_curie, "paired_with", max_probability)
                    else:
                        target_curie_temp = target_curie.replace('CHEMBL.COMPOUND:','CHEMBL:')
                        # Let's build a simple single query
                        q = build_query(genes=[source_curie],
                                        therapeutic=target_curie_temp,
                                        disease='MONDO:0007254',
                                        outcome=('EFO:0000714', '>=', self.CHP_survival_threshold))

                        response = self.client.query(q)
                        max_probability = self.client.get_outcome_prob(response)
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, target_curie, "paired_with", max_probability)

                    source_dict[source_curie] = source_qnode_key
                    target_dict[target_curie] = target_qnode_key

                    # Record which of this edge's nodes correspond to which qnode_key
                    if swagger_edge_key not in edge_to_nodes_map:
                        edge_to_nodes_map[swagger_edge_key] = dict()
                    edge_to_nodes_map[swagger_edge_key][source_qnode_key] = source_curie
                    edge_to_nodes_map[swagger_edge_key][target_qnode_key] = target_curie

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

                return final_kg, edge_to_nodes_map

        elif source_pass_nodes is not None:
            source_dict = dict()
            target_dict = dict()

            if source_pass_nodes[0] in self.allowable_drug_curies:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'gene'
            if target_category in drug_label_list:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'gene'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg, edge_to_nodes_map
            else:
                if source_category_temp == 'drug':
                    for source_curie in source_pass_nodes:

                        genes = [curie for curie in self.allowable_gene_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and target_category in [category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]]
                        therapeutic = source_curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:')
                        disease = 'MONDO:0007254'
                        outcome = ('EFO:0000714', '>=', self.CHP_survival_threshold)

                        queries = []
                        for gene in genes:
                            queries.append(build_query(
                                genes=[gene],
                                therapeutic=therapeutic,
                                disease=disease,
                                outcome=outcome,
                            ))

                        # use the query_all endpoint to run the batch of queries
                        res = self.client.query_all(queries)

                        for result, gene in zip(res["message"], genes):
                            prob = self.client.get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(gene, source_curie, "paired_with", prob)

                            source_dict[source_curie] = source_qnode_key
                            target_dict[gene] = target_qnode_key

                            # Record which of this edge's nodes correspond to which qnode_key
                            if swagger_edge_key not in edge_to_nodes_map:
                                edge_to_nodes_map[swagger_edge_key] = dict()
                            edge_to_nodes_map[swagger_edge_key][source_qnode_key] = source_curie
                            edge_to_nodes_map[swagger_edge_key][target_qnode_key] = gene

                            # Finally add the current edge to our answer knowledge graph
                            final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                else:
                    for source_curie in source_pass_nodes:

                        genes = [source_curie]
                        therapeutic = [curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:') for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'))[curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:')] is not None and target_category in [category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'), return_all_categories=True)[curie.replace('CHEMBL:','CHEMBL.COMPOUND:')]['all_categories'].keys())]]
                        disease = 'MONDO:0007254'
                        outcome = ('EFO:0000714', '>=', self.CHP_survival_threshold)

                        queries = []
                        for drug in therapeutic:
                            queries.append(build_query(
                                genes=genes,
                                therapeutic=drug,
                                disease=disease,
                                outcome=outcome,
                            ))

                        # use the query_all endpoint to run the batch of queries
                        res = self.client.query_all(queries)

                        for result, drug in zip(res["message"], therapeutic):
                            drug = drug.replace('CHEMBL:', 'CHEMBL.COMPOUND:')
                            prob = self.client.get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, drug, "paired_with", prob)

                            source_dict[source_curie] = source_qnode_key
                            target_dict[drug] = target_qnode_key

                            # Record which of this edge's nodes correspond to which qnode_key
                            if swagger_edge_key not in edge_to_nodes_map:
                                edge_to_nodes_map[swagger_edge_key] = dict()
                            edge_to_nodes_map[swagger_edge_key][source_qnode_key] = source_curie
                            edge_to_nodes_map[swagger_edge_key][target_qnode_key] = drug

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

                return final_kg, edge_to_nodes_map
        else:
            source_dict = dict()
            target_dict = dict()

            if target_pass_nodes[0] in self.allowable_drug_curies:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'gene'
            if source_category in drug_label_list:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'gene'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg, edge_to_nodes_map
            else:
                if target_category_temp == 'drug':
                    for target_curie in target_pass_nodes:

                        genes = [curie for curie in self.allowable_gene_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and source_category in [category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]]
                        therapeutic = target_curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:')
                        disease = 'MONDO:0007254'
                        outcome = ('EFO:0000714', '>=', self.CHP_survival_threshold)

                        queries = []
                        for gene in genes:
                            queries.append(build_query(
                                genes=[gene],
                                therapeutic=therapeutic,
                                disease=disease,
                                outcome=outcome,
                            ))

                        # use the query_all endpoint to run the batch of queries
                        res = self.client.query_all(queries)

                        for result, gene in zip(res["message"], genes):
                            prob = self.client.get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(gene, target_curie, "paired_with", prob)

                            source_dict[gene] = source_qnode_key
                            target_dict[target_curie] = target_qnode_key

                            # Record which of this edge's nodes correspond to which qnode_key
                            if swagger_edge_key not in edge_to_nodes_map:
                                edge_to_nodes_map[swagger_edge_key] = dict()
                            edge_to_nodes_map[swagger_edge_key][source_qnode_key] = gene
                            edge_to_nodes_map[swagger_edge_key][target_qnode_key] = target_curie

                            # Finally add the current edge to our answer knowledge graph
                            final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

                else:
                    for target_curie in target_pass_nodes:

                        genes = [target_curie]
                        therapeutic = [curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:') for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'))[curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:')] is not None and source_category in [category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'), return_all_categories=True)[curie.replace('CHEMBL:','CHEMBL.COMPOUND:')]['all_categories'].keys())]]
                        disease = 'MONDO:0007254'
                        outcome = ('EFO:0000714', '>=', self.CHP_survival_threshold)

                        queries = []
                        for drug in therapeutic:
                            queries.append(build_query(
                                genes=genes,
                                therapeutic=drug,
                                disease=disease,
                                outcome=outcome,
                            ))

                        # use the query_all endpoint to run the batch of queries
                        res = self.client.query_all(queries)

                        for result, drug in zip(res["message"], therapeutic):
                            drug = drug.replace('CHEMBL:', 'CHEMBL.COMPOUND:')
                            prob = self.client.get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, drug, "paired_with", prob)

                            source_dict[drug] = source_qnode_key
                            target_dict[target_curie] = target_qnode_key

                            # Record which of this edge's nodes correspond to which qnode_key
                            if swagger_edge_key not in edge_to_nodes_map:
                                edge_to_nodes_map[swagger_edge_key] = dict()
                            edge_to_nodes_map[swagger_edge_key][source_qnode_key] = drug
                            edge_to_nodes_map[swagger_edge_key][target_qnode_key] = target_curie

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

                return final_kg, edge_to_nodes_map

    def _check_id(self, qnode_id, log):

        if type(qnode_id) is str:
            if qnode_id in self.allowable_gene_curies or qnode_id in self.allowable_drug_curies:
                return [False, [qnode_id], []]
            else:
                return [False, [], [qnode_id]]
        else:
            pass_nodes_gene_temp = list()
            pass_nodes_drug_temp = list()
            not_pass_nodes = list()
            for curie in qnode_id:
                if curie in self.allowable_gene_curies:
                    pass_nodes_gene_temp += [curie]
                elif curie in self.allowable_drug_curies:
                    pass_nodes_drug_temp += [curie]
                else:
                    not_pass_nodes += [curie]

            if len(pass_nodes_gene_temp)!=0 and len(pass_nodes_drug_temp) != 0:
                log.error(f"The curie ids of {qnode_id} contain both gene and drug", error_code="MixedTypes")
                return [True, [], []]
            else:
                pass_nodes = pass_nodes_gene_temp + pass_nodes_drug_temp
                return [False, pass_nodes, not_pass_nodes]

    def _convert_to_swagger_edge(self, subject: str, object: str, name: str, value: float) -> Tuple[str, Edge]:
        swagger_edge = Edge()
        swagger_edge.predicate = f"biolink:{name}"
        swagger_edge.subject = subject
        swagger_edge.object = object
        swagger_edge_key = f"CHP:{subject}-{name}-{object}"
        swagger_edge.relation = None

        type = "EDAM:data_0951"
        url = "https://github.com/di2ag/chp_client"

        swagger_edge.attributes = [Attribute(type=type, name=name, value=str(value), url=url),
                                   Attribute(name="provided_by", value=self.kp_name, type=eu.get_attribute_type("provided_by")),
                                   Attribute(name="is_defined_by", value="ARAX", type=eu.get_attribute_type("is_defined_by"))]
        return swagger_edge_key, swagger_edge

    def _convert_to_swagger_node(self, node_key: str) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = node_key
        swagger_node.name = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_name']
        swagger_node.description = None
        swagger_node.category = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_type']

        return swagger_node_key, swagger_node

