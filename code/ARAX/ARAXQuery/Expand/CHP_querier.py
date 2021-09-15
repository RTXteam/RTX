#!/bin/env python3
import sys
import os
import traceback
import ast
import copy
import itertools
import urllib
import numpy as np
from typing import List, Dict, Tuple
from neo4j import GraphDatabase
import json
import requests
import requests_cache

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
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../ARAX/BiolinkHelper/")
from biolink_helper import BiolinkHelper
class CHPQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.synonymizer = NodeSynonymizer()
        self.biolink_helper = BiolinkHelper()
        self.kp_name = "CHP"

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using CHP client.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        # Set up the required parameters
        log = self.response
        self.CHP_survival_threshold = float(self.response.data['parameters']['CHP_survival_threshold'])
        meta_kg = CHPQuerier._get_CHP_meta_kg()
        self.allowable_gene_curie_prefixes = meta_kg['nodes']['biolink:Gene']['id_prefixes']
        self.allowable_drug_curie_prefixes = list(set(meta_kg['nodes']['biolink:Drug']['id_prefixes'] + meta_kg['nodes']['biolink:ChemicalSubstance']['id_prefixes'] + meta_kg['nodes']['biolink:SmallMolecule']['id_prefixes']))
        self.allowable_disease_curie_prefixes = meta_kg['nodes']['biolink:Disease']['id_prefixes']
        final_kg = QGOrganizedKnowledgeGraph()

        final_kg = self._answer_query_using_CHP_client(query_graph, log)

        return final_kg

    def _answer_query_using_CHP_client(self, query_graph: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        log.debug(f"Processing query results for edge {qedge_key} by using CHP client")
        final_kg = QGOrganizedKnowledgeGraph()
        gene_label_list = ['gene']
        # drug_label_list = list(set([drug_category_ancestor.replace('biolink:','').replace('_','').lower() for drug_cateogry in ['biolink:Drug','biolink:SmallMolecule'] for drug_category_ancestor in self.categorymanager.get_expansive_categories(drug_cateogry)]))
        drug_label_list = [ancestor.replace('biolink:','').replace('_','').lower() for ancestor in self.biolink_helper.get_ancestors(['biolink:Drug','biolink:SmallMolecule'],include_mixins=False)]
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
        if (source_qnode.ids is None) and (target_qnode.ids is None):
            log.error(f"Both ends of edge {qedge_key} are None", error_code="BadEdge")
            return final_kg

        # check if the query nodes are drug or disease
        if source_qnode.ids is not None:

            if type(source_qnode.ids) is str:
                source_pass_nodes = [source_qnode.ids]
            else:
                source_pass_nodes = source_qnode.ids
            has_error, pass_nodes, not_pass_nodes = self._check_id(source_qnode.ids, log)
            if has_error:
                return final_kg
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
                    if type(source_qnode.ids) is str:
                        log.warning(f"The curie id of {source_qnode.ids} is not allowable based on CHP client")
                        return final_kg
                    else:
                        log.warning(f"The curie ids of {source_qnode.ids} are not allowable based on CHP client")
                        return final_kg
        else:
            try:
                categories = [category.replace('biolink:','').replace('_','').lower() for category in source_qnode.categories]
            except AttributeError:
                log.error(f"The category of query node {source_qnode_key} is empty. Please provide a category.", error_code='NoCategoryError')
                return final_kg
            if len(set(categories).intersection(set(drug_label_list))) > 0 or len(set(categories).intersection(set(gene_label_list))) > 0:
                source_category = categories
            else:
                log.error(f"The category of query node {source_qnode_key} is unsatisfiable. It has to be drug or disase", error_code="CategoryError")
                return final_kg

        if target_qnode.ids is not None:

            if type(target_qnode.ids) is str:
                target_pass_nodes = [target_qnode.ids]
            else:
                target_pass_nodes = target_qnode.ids
            has_error, pass_nodes, not_pass_nodes = self._check_id(target_qnode.ids, log)
            if has_error:
                return final_kg
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
                    if type(target_qnode.ids) is str:
                        log.warning(f"The curie id of {target_qnode.ids} is not allowable based on CHP client")
                        return final_kg
                    else:
                        log.warning(f"The curie ids of {target_qnode.ids} are not allowable based on CHP client")
                        return final_kg
        else:
            try:
                categories = [category.replace('biolink:','').replace('_','').lower() for category in target_qnode.categories]
            except AttributeError:
                log.error(f"The category of query node {target_qnode_key} is empty. Please provide a category.", error_code='NoCategoryError')
                return final_kg
            if len(set(categories).intersection(set(drug_label_list))) > 0 or len(set(categories).intersection(set(gene_label_list))) > 0:
                target_category = categories
            else:
                log.error(f"The category of query node {target_qnode_key} is unsatisfiable. It has to be drug/small_molecule or gene", error_code="CategoryError")
                return final_kg

        if (source_pass_nodes is None) and (target_pass_nodes is None):
            return final_kg

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
                return final_kg
            else:
                for (source_curie, target_curie) in itertools.product(source_pass_nodes, target_pass_nodes):

                    if source_category_temp == 'drug':
                        # source_curie_temp = source_curie.replace('CHEMBL.COMPOUND:','CHEMBL:')
                        source_curie_temp = source_curie
                        # Let's build a simple single query
                        q = CHPQuerier._build_standard_query(gene=target_curie, drug=source_curie_temp, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')

                        response = CHPQuerier._query_CHP_api(q)
                        max_probability = CHPQuerier._get_outcome_prob(response)
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, source_curie, "paired_with", max_probability)
                    else:
                        # target_curie_temp = target_curie.replace('CHEMBL.COMPOUND:','CHEMBL:')
                        target_curie_temp = target_curie
                        # Let's build a simple single query
                        q = CHPQuerier._build_standard_query(gene=source_curie, drug=target_curie_temp, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')

                        response = CHPQuerier._query_CHP_api(q)
                        max_probability = CHPQuerier._get_outcome_prob(response)
                        swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, target_curie, "paired_with", max_probability)

                    source_dict[source_curie] = source_qnode_key
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

        elif source_pass_nodes is not None:
            source_dict = dict()
            target_dict = dict()

            if source_pass_nodes[0] in self.allowable_drug_curies:
                source_category_temp = 'drug'
            else:
                source_category_temp = 'gene'
            if len(set(target_category).intersection(set(drug_label_list))) > 0:
                target_category_temp = 'drug'
            else:
                target_category_temp = 'gene'
            if source_category_temp == target_category_temp:
                log.error(f"The query nodes in both ends of edge are the same type which is {source_category_temp}", error_code="CategoryError")
                return final_kg
            else:
                if source_category_temp == 'drug':
                    for source_curie in source_pass_nodes:

                        genes = [curie for curie in self.allowable_gene_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and len(set(target_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]))) > 0]
                        # drug = source_curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:')
                        drug = source_curie

                        for gene in genes:

                            q = CHPQuerier._build_standard_query(gene=gene, drug=drug, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')

                            result = CHPQuerier._query_CHP_api(q)
                            prob = CHPQuerier._get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(gene, source_curie, "paired_with", prob)

                            source_dict[source_curie] = source_qnode_key
                            target_dict[gene] = target_qnode_key

                            # Finally add the current edge to our answer knowledge graph
                            final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)
                else:
                    for source_curie in source_pass_nodes:

                        gene = source_curie
                        # drugs = [curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:') for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'))[curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:')] is not None and len(set(target_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'), return_all_categories=True)[curie.replace('CHEMBL:','CHEMBL.COMPOUND:')]['all_categories'].keys())]))) > 0]
                        drugs = [curie for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and len(set(target_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]))) > 0]

                        for drug in drugs:
                            q = CHPQuerier._build_standard_query(gene=gene, drug=drug, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')
                            # drug = drug.replace('CHEMBL:', 'CHEMBL.COMPOUND:')
                            result = CHPQuerier._query_CHP_api(q)
                            prob = CHPQuerier._get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(source_curie, drug, "paired_with", prob)

                            source_dict[source_curie] = source_qnode_key
                            target_dict[drug] = target_qnode_key

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
                return final_kg
            else:
                if target_category_temp == 'drug':
                    for target_curie in target_pass_nodes:

                        genes = [curie for curie in self.allowable_gene_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and len(set(source_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]))) > 0]
                        # drug = target_curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:')
                        drug = target_curie

                        for gene in genes:

                            q = CHPQuerier._build_standard_query(gene=gene, drug=drug, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')

                            result = CHPQuerier._query_CHP_api(q)
                            prob = CHPQuerier._get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(gene, target_curie, "paired_with", prob)

                            source_dict[gene] = source_qnode_key
                            target_dict[target_curie] = target_qnode_key

                            # Finally add the current edge to our answer knowledge graph
                            final_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

                else:
                    for target_curie in target_pass_nodes:

                        gene = target_curie
                        # drugs = [curie.replace('CHEMBL.COMPOUND:', 'CHEMBL:') for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'))[curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:')] is not None and len(set(source_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie.replace('CHEMBL:', 'CHEMBL.COMPOUND:'), return_all_categories=True)[curie.replace('CHEMBL:','CHEMBL.COMPOUND:')]['all_categories'].keys())]))) > 0]
                        drugs = [curie for curie in self.allowable_drug_curies if self.synonymizer.get_canonical_curies(curie)[curie] is not None and len(set(source_category).intersection(set([category.replace('biolink:','').replace('_','').lower() for category in list(self.synonymizer.get_canonical_curies(curie, return_all_categories=True)[curie]['all_categories'].keys())]))) > 0]

                        for drug in drugs:
                            q = CHPQuerier._build_standard_query(gene=gene, drug=drug, disease='MONDO:0007254', outcome='EFO:0000714', outcome_name='survival_time', outcome_op='>', outcome_value=self.CHP_survival_threshold, trapi_version='1.1')
                            # drug = drug.replace('CHEMBL:', 'CHEMBL.COMPOUND:')

                            result = CHPQuerier._query_CHP_api(q)
                            prob = CHPQuerier._get_outcome_prob(result)
                            swagger_edge_key, swagger_edge = self._convert_to_swagger_edge(target_curie, drug, "paired_with", prob)

                            source_dict[drug] = source_qnode_key
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

        swagger_edge.attributes = [Attribute(attribute_type_id=type, original_attribute_name=name, value=str(value), value_url=url),
                                   eu.get_kp_source_attribute(self.kp_name),
                                   eu.get_arax_source_attribute()]
        return swagger_edge_key, swagger_edge

    def _convert_to_swagger_node(self, node_key: str) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = node_key
        swagger_node.name = self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_name']
        swagger_node.description = None
        if self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_category'] is not None:
            swagger_node.categories = [self.synonymizer.get_canonical_curies(node_key)[node_key]['preferred_category']]
        else:
            swagger_node.categories = None

        return swagger_node_key, swagger_node

    @staticmethod
    def _get_CHP_meta_kg():

        meta_kg_url = 'http://chp.thayer.dartmouth.edu/v1.2/meta_knowledge_graph/'
        with requests_cache.disabled():
            r = urllib.request.urlopen(meta_kg_url).read()
            meta_kg = json.loads(r)

        return meta_kg

    @staticmethod
    def _query_CHP_api(query):

        with requests_cache.disabled():
            r = requests.post('http://chp.thayer.dartmouth.edu/query/', json=query)

        return json.loads(r.content)

    @staticmethod
    def _make_node(categories, ids=None):
        node = {
            'categories':categories,
            'ids':ids,
            'constraints':[]
        }
        return node

    @staticmethod
    def _add_node(query, node_id, node):
        query['message']['query_graph']['nodes']['n{}'.format(node_id)] = node
        node_id += 1
        return query, node_id

    @staticmethod
    def _make_edge(subject, object, predicate):
        edge = {
            'subject':subject,
            'object':object,
            'relation':None,
            'predicates':predicate
        }
        return edge

    @staticmethod
    def _add_edge(query, edge_id, edge):
        query['message']['query_graph']['edges']['e{}'.format(edge_id)] = edge
        edge_id += 1
        return query, edge_id

    @staticmethod
    def _build_CHP_queries(
        gene=None,
        drug=None,
        disease=None,
        wildcard_node=None,
        predicate=None,
        trapi_version='1.2',
        ):
    
        """ _build_CHP_queries builds out CHP valid queries from some specified evidence. This includes wildcard queries and standard probabilistic.
            These queries can be sent to http://chp.thayer.dartmouth.edu/query/ using the _query_CHP_api function. We encourage anyone deeply interested 
            in our underlying computations to refer to: https://di2ag.github.io/chp/chp_documentation#.

            :param gene: a gene curie.
            :type gene: Str (default None).
            :param drug: a drug curie.
            :type drug: Str (default None).
            :param disease: a disease curie.
            :type disease: Str (default None).
            :param wildcard_node: takes on the biolink type for the node that does not have a curie.
            :type disease: Str (default None).
            :param predicate: a predicate curies.
            :type predicate: Str (default None).
            :param outcome: A curie for Survival Time. This adds a constraint when inference over CHP's patient data. This affects the weights
                            return along our edges (e.g., if we constrain survival time to a value of > 1500 days, this will change the end
                            survival time distribution and "contribution weights".). This is only applied if outcome_value is not None.
            :type outcome: Str (default 'EFO:0000714').
            :param outcome_op: the type of operater to apply to the survival time semantics.
            :type outcome_op: Str (default '>'). This is only applied if outcome_value is not None.
            :param outcome_value: A number indicating the number of days for survival to run our probabilistic query or survival time differential
                                analysis. We internally default a survival time value so it is not required to specify here, unless you would like
                                to compare outcomes when using different survival time semantics.
            :type outcome_value: Int (default None).
            :param trapi_version: Ensures CHP is handling the right version of trapi. Internally we default to 1.2.
            :type trapi_version: Str (default '1.2').
        """

        node_id = 0
        edge_id = 0

        query = {
            'message': { 
                'query_graph': {
                'nodes': {},
                'edges': {},
                },
                'knowledge_graph': {
                'nodes': {},
                'edges': {}
                }, 
            'results': [],
            'trapi_version': trapi_version, 
            'biolink_version': None
            }
        }

        assert predicate is not None, 'Predicate must be populated with a CHP compliant predicate (or ancestory) in the form of biolink:<predicate>. Please see http://chp.thayer.dartmouth.edu/meta_knowledge_graph/ for a list of our predicates.'
        assert not all(evidence is None for evidence in [gene,drug,disease]), 'Must specify at least one piece of evidence.'
        assert any(evidence is not None for evidence in [gene,drug,disease]), 'Can specify at most two pieces of evidence in a 1-hop'

        if predicate == 'biolink:genetically_interacts_with':
            assert gene is not None, 'biolink:genetically_interacts_with requires you to specify a gene as evidence.'
            assert drug is None and disease is None, 'Ambiguous evidence types. biolink:genetically_interacts_with only takes a single gene node as evidence.'
            assert wildcard_node == 'biolink:Gene', 'Wildcard node for biolink:genetically_interacts_with must take on a gene.'
            gene_node = CHPQuerier._make_node(['biolink:Gene'], ids = [gene])
            gene_node2 = CHPQuerier._make_node(['biolink:Gene'])
            gene_node_id = 'n{}'.format(node_id)
            query, node_id = CHPQuerier._add_node(query, node_id, gene_node)
            gene_node_2_id = 'n{}'.format(node_id)
            query, node_id = CHPQuerier._add_node(query, node_id, gene_node2)
            edge = CHPQuerier._make_edge(gene_node_id, gene_node_2_id, [predicate])
            predicate_id = 'e{}'.format(edge_id)
            query, edge_id = CHPQuerier._add_edge(query, edge_id, edge)
        elif predicate == 'biolink:gene_associated_with_condition' or predicate == 'biolink:condition_associated_with_gene':
            assert disease is not None, 'Our gene -> disease edge currently does not support disease as a wildcard. Therefore disease must be specified as evidence. We are working on constructing disease wildcards.'
            assert drug is None, 'Ambiguous evidence types. biolink:gene_associated_with_condition does not use drug curies.'
            if gene is not None:
                gene_node = CHPQuerier._make_node(['biolink:Gene'], ids = [gene])
            else:
                assert wildcard_node == 'biolink:Gene', 'For biolink:gene_associated_with_condition, if you only specify a disease as evidence, you must make wildcard_node=\'biolink:Gene\'.'
                gene_node = CHPQuerier._make_node(['biolink:Gene'])
            disease_node = CHPQuerier._make_node(['biolink:Disease'], ids = [disease])
            
            if predicate == 'biolink:gene_associated_with_condition':
                gene_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, gene_node)
                disease_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, disease_node)
                edge = CHPQuerier._make_edge(gene_node_id, disease_node_id, [predicate])
            else:
                disease_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, disease_node)
                gene_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, gene_node)
                edge = CHPQuerier._make_edge(disease_node_id, gene_node_id, [predicate])
            predicate_id = 'e{}'.format(edge_id)
            query, edge_id = CHPQuerier._add_edge(query, edge_id, edge)
        elif predicate == 'biolink:treats' or predicate == 'biolink:treated_by':
            assert disease is not None, 'Our drug -> disease edge currently does not support disease as a wildcard. Therefore disease must be specified as evidence. We are working on constructing disease wildcards.'
            assert gene is None, 'Ambiguous evidence types. biolink:treats does not use gene curies.'
            if drug is not None:
                drug_node = CHPQuerier._make_node(['biolink:Drug'], ids = [drug])
            else:
                assert wildcard_node == 'biolink:Drug', 'For biolink:treats, if you only specify a disease as evidence, you must make wildcard_node=\'biolink:Drug\'.'
                drug_node = CHPQuerier._make_node(['biolink:Drug'])
            disease_node = CHPQuerier._make_node(['biolink:Disease'], ids = [disease])
            
            if predicate == 'biolink:treats':
                drug_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, drug_node)
                disease_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, disease_node)
                edge = CHPQuerier._make_edge(drug_node_id, disease_node_id, [predicate])
            else:
                disease_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, disease_node)
                drug_node_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, drug_node)
                edge = CHPQuerier._make_edge(disease_node_id, drug_node_id, [predicate])
            predicate_id = 'e{}'.format(edge_id)
            query, edge_id = CHPQuerier._add_edge(query, edge_id, edge)
        elif predicate == 'biolink:has_real_world_evidence_of_association_with' or predicate == 'biolink:associated_with_real_world_evidence':
            evidence = []
            if gene is not None:
                gene_node = CHPQuerier._make_node(['biolink:Gene'], ids = [gene])
                evidence.append(gene_node)
            if drug is not None:
                drug_node = CHPQuerier._make_node(['biolink:Drug'], ids = [drug])
                evidence.append(drug_node)
            if disease is not None:
                disease_node = CHPQuerier._make_node(['biolink:Disease'], ids = [disease])
                evidence.append(disease_node)
            assert len(evidence) <= 2, 'Too many evidence are specified for a 1 hop.'
            assert len(evidence) != 0, 'No evidence specified for a 1 hop.'
            if len(evidence) == 2:
                evidence_node_one_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, evidence[0])
                evidence_node_two_id = 'n{}'.format(node_id)
                query, node_id = CHPQuerier._add_node(query, node_id, evidence[1])
                edge = CHPQuerier._make_edge(evidence_node_one_id, evidence_node_two_id, [predicate])
                predicate_id = 'e{}'.format(edge_id)
            else:
                if predicate == 'biolink:has_real_world_evidence_of_association_with':
                    wildcard = CHPQuerier._make_node([wildcard_node])
                    wildcard_node_id = 'n{}'.format(node_id)
                    query, node_id = CHPQuerier._add_node(query, node_id, wildcard)
                    evidence_node_id = 'n{}'.format(node_id)
                    query, node_id = CHPQuerier._add_node(query, node_id, evidence[0])
                    edge = CHPQuerier._make_edge(wildcard_node_id, evidence_node_id, [predicate])
                else:
                    evidence_node_id = 'n{}'.format(node_id)
                    query, node_id = CHPQuerier._add_node(query, node_id, evidence[0])
                    wildcard = CHPQuerier._make_node([wildcard_node])
                    wildcard_node_id = 'n{}'.format(node_id)
                    query, node_id = CHPQuerier._add_node(query, node_id, wildcard)
                    edge = CHPQuerier._make_edge(evidence_node_id, wildcard_node_id, [predicate])
                predicate_id = 'e{}'.format(edge_id)
            query, edge_id = CHPQuerier._add_edge(query, edge_id, edge)
        return query

    @staticmethod
    def _get_outcome_prob(q_resp):
        """ Extracts the probability from a CHP query response.
        """

        # Extract response. Probability is always in first result
        if 'message' in q_resp:
            message = copy.deepcopy(q_resp['message'])
        else:
            message = copy.deepcopy(q_resp)
        kg = message["knowledge_graph"]
        res = message["results"][0]
        # Find the outcome edge
        for qg_id, edge_bind in res["edge_bindings"].items():
            edge = kg["edges"][edge_bind[0]["id"]]
            # if edge["predicate"] == 'biolink:has_phenotype':
            try:
                prob = edge["attributes"][0]["value"]
                break
            except KeyError:
                raise KeyError('Could not find associated probability of query. Possible ill-formed query.')
        return prob
