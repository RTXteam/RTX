#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
import pandas as pd
import math
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_expander import ARAXExpander
from ARAX_resultify import ARAXResultify
from ARAX_decorator import ARAXDecorator
from biolink_helper import BiolinkHelper
import traceback
from collections import Counter
from collections.abc import Hashable
from itertools import combinations
import copy
from typing import List, Dict, Set, Union, Optional
from datetime import datetime

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.attribute import Attribute
from openapi_server.models.qualifier import Qualifier
from openapi_server.models.retrieval_source import RetrievalSource
from openapi_server.models.qualifier_constraint import QualifierConstraint as QConstraint
from openapi_server.models.knowledge_graph import KnowledgeGraph

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'scripts']))
from build_mapping_db import xDTDMappingDB

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()


class InferUtilities:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.report_stats = True
        self.bh = BiolinkHelper()

    def __get_formated_edge_key(self, edge: Edge, primary_knowledge_source: str, kp: str = 'infores:rtx-kg2') -> str:
        return f"{kp}:{edge.subject}-{edge.predicate}-{edge.object}-{primary_knowledge_source}"

    def __none_to_zero(self, val):
        if val is None:
            return 0
        else: 
            return val

    def resultify_and_sort(self, essence_scores):
        message = self.response.envelope.message
        resultifier = ARAXResultify()
        resultify_params = {
            "ignore_edge_direction": "true"
        }
        self.response = resultifier.apply(self.response, resultify_params)

        for result in message.results:
            if result.essence in essence_scores:
                result.score = essence_scores[result.essence]
            else:
                result.score = None
                # result.analyses[0].score = essence_scores[result.essence]
                self.response.warning(
                    f"Error retrieving score for result essence {result.essence}. Setting result score to None.")
        message.results.sort(key=lambda x: self.__none_to_zero(x.score), reverse=True)

    def genrete_treat_subgraphs(self, response: ARAXResponse, top_drugs: pd.DataFrame, top_paths: dict, qedge_id=None, kedge_global_iter: int=0, qedge_global_iter: int=0, qnode_global_iter: int=0, option_global_iter: int=0):
        """
        top_drugs and top_paths returned by Chunyu's createDTD.py code (predict_top_n_drugs and predict_top_m_paths respectively).
        Ammends the response effectively TRAPI-ifying the paths returned by Chunyu's code.
        May not work on partially filled out response (as it assumes fresh QG and KG, i.e. not stuff partially filled out).
        The *_global_iter vars are to keep count of qedge and kedge if this is run multiple times. But see previous line for proviso.
        Returns the response and all the *_global_iters
        """
        self.response = response
        self.kedge_global_iter = 0
        self.qedge_global_iter = 0
        self.qnode_global_iter = 0
        self.option_global_iter = 0
        self.qedge_id = qedge_id
        message = self.response.envelope.message
        # check to make sure that the qedge_id either exists and is in the QG, or else does not exist and the QG is empty
        if qedge_id is not None:
            if not hasattr(message, 'query_graph') or qedge_id not in message.query_graph.edges:
                self.response.error(f"qedge_id {qedge_id} not in QG, QG is {message.query_graph}")
                raise Exception(f"qedge_id {qedge_id} not in QG")
        elif hasattr(message, 'query_graph'):
            if len(message.query_graph.edges) > 0:
                self.response.error("qedge_id is None but QG is not empty")
                raise Exception("qedge_id is None but QG is not empty")

        expander = ARAXExpander()
        messenger = ARAXMessenger()
        synonymizer = NodeSynonymizer()
        decorator = ARAXDecorator()
        xdtdmapping = xDTDMappingDB(None, None, RTXConfig.explainable_dtd_db_path.split('/')[-1], mode='run', db_loc=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction']))

        kp = 'infores:rtx-kg2'

        path_lengths = set([math.floor(len(x[0].split("->"))/2.) for paths in top_paths.values() for x in paths])
        try:
            max_path_len = max(path_lengths)
        except ValueError:
            max_path_len = 0

        if len(message.query_graph.edges) !=0 and not hasattr(self.response, 'original_query_graph'):
            self.response.original_query_graph = copy.deepcopy(message.query_graph)

        disease_curie = top_drugs['disease_id'].tolist()[0]
        disease_name = top_drugs['disease_name'].tolist()[0]
        disease_info = xdtdmapping.get_node_info(node_id=disease_curie)
        if disease_info is None:
            self.response.warning(f"Could not find {disease_curie} in NODE_MAPPING table due to using refreshed xDTD database")
            return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
        
        if not message.knowledge_graph or not hasattr(message, 'knowledge_graph'):  # if the knowledge graph is empty, create it
            message.knowledge_graph = KnowledgeGraph()
            message.knowledge_graph.nodes = {}
            message.knowledge_graph.edges = {}
        if not hasattr(message.knowledge_graph, 'nodes'):
            message.knowledge_graph.nodes = {}
        if not hasattr(message.knowledge_graph, 'edges'):
            message.knowledge_graph.edges = {}

        # Only add these in if the query graph is empty
        if len(message.query_graph.edges) == 0:
            qedge_id = "treats"
            add_qnode_params = {
                'key': "disease",
                'name': disease_curie,
            }
            self.response = messenger.add_qnode(self.response, add_qnode_params)
            message.knowledge_graph.nodes[disease_curie] = Node(name=disease_name, categories=[disease_info.category], attributes=[])
            message.knowledge_graph.nodes[disease_curie].qnode_keys = [add_qnode_params['key']]
            add_qnode_params = {
                'key': "drug",
                'categories': ['biolink:Drug', 'biolink:SmallMolecule']
            }
            self.response = messenger.add_qnode(self.response, add_qnode_params)
            add_qedge_params = {
                'key': qedge_id,
                'subject': "drug",
                'object': "disease",
                'predicates': ["biolink:treats"]
            }
            self.response = messenger.add_qedge(self.response, add_qedge_params)
            message.query_graph.edges[add_qedge_params['key']].knowledge_type = "inferred"
            message.query_graph.edges[add_qedge_params['key']].filled = True
            drug_qnode_key = 'drug'
            disease_qnode_key = 'disease'
            self.response.original_query_graph = copy.deepcopy(message.query_graph)

        else:
            message.knowledge_graph.nodes[disease_curie] = Node(name=disease_name, categories=[disease_info.category], attributes=[])
            drug_qnode_key = response.envelope.message.query_graph.edges[qedge_id].subject
            disease_qnode_key = response.envelope.message.query_graph.edges[qedge_id].object
            message.knowledge_graph.nodes[disease_curie].qnode_keys = [disease_qnode_key]
            # Don't add a new edge in for the treats as there is already an edge there with the knowledge type inferred
            # But do say that this edge has been filled
            message.query_graph.edges[qedge_id].filled = True
            message.query_graph.nodes[drug_qnode_key].categories = ['biolink:Drug', 'biolink:SmallMolecule']
            # Just use the drug and disease that are currently in the QG
        # # now that KG and QG are populated with stuff, shorthand them (find a weird problem for this operation, so skip using short name)
        # knodes = message.knowledge_graph.nodes
        # kedges = message.knowledge_graph.edges
        # qnodes = message.query_graph.nodes
        # qedges = message.query_graph.edges
        # If the max path len is 0, that means there are no paths found, so just insert the drugs with the probability_treats on them
        if max_path_len == 0:
            essence_scores = {}
            node_ids = top_drugs['drug_id']
            node_id_to_score = dict(zip(node_ids, top_drugs['tp_score']))
            # Add the drugs to the knowledge graph
            for drug_canonical_id in node_ids:
                try:
                    node_info = xdtdmapping.get_node_info(node_id=drug_canonical_id)
                except:
                    continue
                if not node_info:
                    continue
                drug_categories = [node_info.category]
                # add the node to the knowledge graph
                drug_name = node_info.name
                essence_scores[drug_name] = node_id_to_score[drug_canonical_id]
                if drug_canonical_id not in message.knowledge_graph.nodes:
                    message.knowledge_graph.nodes[drug_canonical_id] = Node(name=drug_name, categories=drug_categories, attributes=[])
                    message.knowledge_graph.nodes[drug_canonical_id].qnode_keys = [drug_qnode_key]
                else:  # it's already in the KG, just pass
                    pass
                # add the edge to the knowledge graph
                treat_score = node_id_to_score[drug_canonical_id]
                edge_attribute_list = [
                    Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                    Attribute(original_attribute_name=None, value=True,
                                    attribute_type_id="EDAM-DATA:1772",
                                    attribute_source="infores:arax", value_type_id="metatype:Boolean",
                                    value_url=None,
                                    description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    Attribute(attribute_type_id="EDAM-DATA:0951", original_attribute_name="probability_treats",
                                    value=str(treat_score))
                ]
                retrieval_source = [
                                    RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                ]
                new_edge = Edge(subject=drug_canonical_id, object=disease_curie, predicate='biolink:treats', attributes=edge_attribute_list, sources=retrieval_source)
                new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source="infores:arax", kp=kp)
                if new_edge_key not in message.knowledge_graph.edges:
                    message.knowledge_graph.edges[new_edge_key] = new_edge
                    message.knowledge_graph.edges[new_edge_key].filled = True
                    message.knowledge_graph.edges[new_edge_key].qedge_keys = [qedge_id]
                self.resultify_and_sort(essence_scores)
            return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter


        # Otherwise we do have paths and we need to handle them
        path_keys = [{} for i in range(max_path_len)]
        for i in range(max_path_len+1):
            if (i+1) in path_lengths:
                path_qnodes = [drug_qnode_key]
                for j in range(i):
                    new_qnode_key = f"creative_DTD_qnode_{self.qnode_global_iter}"
                    path_qnodes.append(new_qnode_key)
                    add_qnode_params = {
                        'key' : new_qnode_key,
                        'option_group_id': f"creative_DTD_option_group_{self.option_global_iter}",
                        "is_set": "true"
                    }
                    self.response = messenger.add_qnode(self.response, add_qnode_params)
                    self.qnode_global_iter += 1
                path_qnodes.append(disease_qnode_key)
                qnode_pairs = list(zip(path_qnodes,path_qnodes[1:]))
                qedge_key_list = []
                for qnode_pair in qnode_pairs:
                    add_qedge_params = {
                        'key': f"creative_DTD_qedge_{self.qedge_global_iter}",
                        'subject': qnode_pair[0],
                        'object': qnode_pair[1],
                        'option_group_id': f"creative_DTD_option_group_{self.option_global_iter}"
                    }
                    qedge_key_list.append(f"creative_DTD_qedge_{self.qedge_global_iter}")
                    self.qedge_global_iter += 1
                    self.response = messenger.add_qedge(self.response, add_qedge_params)
                    message.query_graph.edges[add_qedge_params['key']].filled = True
                path_keys[i]["qnode_pairs"] = qnode_pairs
                path_keys[i]["qedge_keys"] = qedge_key_list
                self.option_global_iter += 1

        # FW: code that will add resulting paths to the query graph and knowledge graph goes here
        essence_scores = {}
        for (drug, disease), paths in top_paths.items():
            path_added = False
            # Splits the paths which are encodes as strings into a list of nodes names and edge predicates
            # The x[0] is here since each element consists of the string path and a score we are currently ignoring the score
            split_paths = [x[0].split("->") for x in paths]
            for path in split_paths:
                drug_curie = path[0]
                n_elements = len(path)

                edges_info = []
                flag = False
                for i in range(0,n_elements-2,2):
                    edge_info = xdtdmapping.get_edge_info(triple_id=(path[i],path[i+1],path[i+2]))
                    if len(edge_info) == 0:
                        flag = True
                    else:
                        edges_info.append(edge_info)
                    
                if flag:
                    continue
                
                path_idx = len(edges_info)-1

                for i in range(path_idx+1):
                    subject_qnode_key = path_keys[path_idx]["qnode_pairs"][i][0]
                    subject_curie = edges_info[i][0].subject
                    try:
                        subject_node_info = xdtdmapping.get_node_info(node_id=subject_curie)
                    except:
                        break_flag = True
                    subject_name = subject_node_info.name
                    subject_category = subject_node_info.category
                    if subject_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[subject_curie] = Node(name=subject_name, categories=[subject_category], attributes=[])
                        message.knowledge_graph.nodes[subject_curie].qnode_keys = [subject_qnode_key]
                    elif subject_qnode_key not in message.knowledge_graph.nodes[subject_curie].qnode_keys:
                        message.knowledge_graph.nodes[subject_curie].qnode_keys.append(subject_qnode_key)
                    object_qnode_key = path_keys[path_idx]["qnode_pairs"][i][1]
                    object_curie = edges_info[i][0].object
                    try:
                        object_node_info = xdtdmapping.get_node_info(node_id=object_curie)
                    except:
                        break_flag = True
                    object_name = object_node_info.name
                    object_category = object_node_info.category
                    if object_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[object_curie] = Node(name=object_name, categories=[object_category], attributes=[])
                        message.knowledge_graph.nodes[object_curie].qnode_keys = [object_qnode_key]
                    elif object_qnode_key not in message.knowledge_graph.nodes[object_curie].qnode_keys:
                        message.knowledge_graph.nodes[object_curie].qnode_keys.append(object_qnode_key)
                    predicate = edges_info[i][0].predicate
                    break_flag = False 
                    for edge_info in edges_info[i]:
                        primary_knowledge_source = edge_info.primary_knowledge_source if edge_info.primary_knowledge_source is not None else "infores:arax"
                        
                        # Handle the self-loop relation
                        if predicate == "SELF_LOOP_RELATION":
                            ## remove self-loop relation requested by issue #2081
                            break_flag = True
                            break
                            # self.response.warning(f"Self-loop relation detected: {subject_name}--{predicate}--{object_name}, replacing with placeholder 'biolink:self_loop_relation'")
                            # predicate = "biolink:self_loop_relation"
                        new_edge = Edge(subject=subject_curie, object=object_curie, predicate=predicate, attributes=[], sources=[])
                        ## add attributes to the path-based edge
                        edge_attribute_list = [
                            Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime")
                        ]
                        if predicate == "biolink:self_loop_relation":
                            edge_attribute_list += [
                                Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This self-loop edge was added by ARAXInfer in the inferene process for flexible path length.")
                            ]
                            retrieval_source = [
                                                RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                            ]
                        else:
                            edge_attribute_list += [
                                Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge was extracted from RTX-KG2.8.4c by ARAXInfer."),
                            ]
                            retrieval_source = [
                                RetrievalSource(resource_id=primary_knowledge_source, resource_role="primary_knowledge_source"),
                                RetrievalSource(resource_id="infores:rtx-kg2", resource_role="aggregator_knowledge_source", upstream_resource_ids=[primary_knowledge_source]),
                                RetrievalSource(resource_id="infores:arax", resource_role="aggregator_knowledge_source", upstream_resource_ids=['infores:rtx-kg2'])
                            ]
                        new_edge.attributes += edge_attribute_list
                        new_edge.sources += retrieval_source
                        new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source=primary_knowledge_source, kp=kp)
                        message.knowledge_graph.edges[new_edge_key] = new_edge
                        message.knowledge_graph.edges[new_edge_key].qedge_keys = [path_keys[path_idx]["qedge_keys"][i]]
                    if break_flag:
                        break
                path_added = True
            if path_added:
                treat_score = top_drugs.loc[top_drugs['drug_id'] == drug]["tp_score"].iloc[0]
                drug_node_info = xdtdmapping.get_node_info(node_id=drug_curie)
                disease_node_info = xdtdmapping.get_node_info(node_id=disease_curie)
                essence_scores[drug_node_info.name] = treat_score
                edge_attribute_list = [
                    Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                    Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    Attribute(attribute_type_id="EDAM-DATA:0951", original_attribute_name="probability_treats", value=str(treat_score))
                ]
                retrieval_source = [
                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                    ]
                #edge_predicate = qedge_id
                edge_predicate = "biolink:treats"
                # comment the following two lines for issue #2253, we now use "biolink:treats_or_applied_or_studied_to_treat" instead of "biolink:treats"
                # if hasattr(message.query_graph.edges[qedge_id], 'predicates') and message.query_graph.edges[qedge_id].predicates:
                #     edge_predicate = message.query_graph.edges[qedge_id].predicates[0]  # FIXME: better way to handle multiple predicates?
                
                fixed_edge = Edge(predicate=edge_predicate, subject=drug_node_info.id, object=disease_node_info.id,
                                attributes=edge_attribute_list, sources=retrieval_source)
                #fixed_edge.qedge_keys = ["treats"]
                fixed_edge.qedge_keys = [qedge_id]
                message.knowledge_graph.edges[f"creative_DTD_prediction_{self.kedge_global_iter}"] = fixed_edge
                self.kedge_global_iter += 1
            else:
                self.response.warning(f"Something went wrong when adding the subgraph for the drug-disease pair ({drug},{disease}) to the knowledge graph. Skipping this result....")

        self.response = decorator.decorate_nodes(self.response)
        if self.response.status != 'OK':
            return self.response
        self.response = decorator.decorate_edges(self.response)
        if self.response.status != 'OK':
            return self.response

        #FIXME: this might cause a problem since it doesn't add optional groups for 1 and 2 hops
        # This might also cause issues when infer is on an intermediate edge
        self.resultify_and_sort(essence_scores)
        

        return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter

    def genrete_regulate_subgraphs(self, response: ARAXResponse, query_chemical: Optional[str], query_gene: Optional[str], top_predictions: pd.DataFrame, top_paths: dict, qedge_id=None, model_type: str = 'increase', kedge_global_iter: int=0, qedge_global_iter: int=0, qnode_global_iter: int=0, option_global_iter: int=0):
        """
        top_predictions and top_paths returned by the createCRG.py code (predict_top_N_chemicals/predict_top_N_genes and predict_top_M_paths respectively).
        Ammends the response effectively TRAPI-ifying the paths returned by the code.
        May not work on partially filled out response (as it assumes fresh QG and KG, i.e. not stuff partially filled out).
        The *_global_iter vars are to keep count of qedge and kedge if this is run multiple times. But see previous line for proviso.
        Returns the response and all the *_global_iters
        """
        self.response = response
        self.kedge_global_iter = 0
        self.qedge_global_iter = 0
        self.qnode_global_iter = 0
        self.option_global_iter = 0
        self.qedge_id = qedge_id
        message = self.response.envelope.message
        # check to make sure that the qedge_id either exists and is in the QG, or else does not exist and the QG is empty
        if qedge_id is not None:
            if not hasattr(message, 'query_graph') or qedge_id not in message.query_graph.edges:
                self.response.error(f"qedge_id {qedge_id} not in QG, QG is {message.query_graph}")
                raise Exception(f"qedge_id {qedge_id} not in QG")
        elif hasattr(message, 'query_graph'):
            if len(message.query_graph.edges) > 0:
                self.response.error("qedge_id is None but QG is not empty")
                raise Exception("qedge_id is None but QG is not empty")

        expander = ARAXExpander()
        messenger = ARAXMessenger()
        synonymizer = NodeSynonymizer()
        decorator = ARAXDecorator()
        #TBD
        # node_ids = set([y for paths in top_paths.values() for x in paths for y in list(x.values())[::2] if y and y != ''])
        node_ids = set([y for paths in top_paths.values() for x in paths for y in x[::2] if y and y != ''])
        node_info = synonymizer.get_canonical_curies(list(node_ids))
        #TBD
        path_lengths = [len(x)//2 for paths in top_paths.values() for x in paths]
        try:
            max_path_len = max(path_lengths)
        except ValueError:
            max_path_len = 0

        if len(message.query_graph.edges) !=0 and not hasattr(self.response, 'original_query_graph'):
            self.response.original_query_graph = copy.deepcopy(message.query_graph)

        if not message.knowledge_graph or not hasattr(message, 'knowledge_graph'):  # if the knowledge graph is empty, create it
            message.knowledge_graph = KnowledgeGraph()
            message.knowledge_graph.nodes = {}
            message.knowledge_graph.edges = {}
        if not hasattr(message.knowledge_graph, 'nodes'):
            message.knowledge_graph.nodes = {}
        if not hasattr(message.knowledge_graph, 'edges'):
            message.knowledge_graph.edges = {}

        # Only add these in if the query graph is empty
        if len(message.query_graph.edges) == 0:

            qedge_id = f"probably_{model_type}_activity"

            if query_chemical:

                chemical_curie = top_predictions['chemical_id'].to_list()[0]
                normalizer_res = synonymizer.get_canonical_curies(chemical_curie)[chemical_curie]
                chemical_name = normalizer_res['preferred_name']
                add_qnode_params = {
                    'key': "chemical",
                    'name': chemical_curie
                }
                self.response = messenger.add_qnode(self.response, add_qnode_params)
                message.knowledge_graph.nodes[chemical_curie] = Node(name=chemical_name, categories=['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule'], attributes=[])
                message.knowledge_graph.nodes[chemical_curie].qnode_keys = ['chemical']
                add_qnode_params = {
                    'key': "gene",
                    'categories': ['biolink:Gene','biolink:Protein']
                }
                self.response = messenger.add_qnode(self.response, add_qnode_params)
            else:
                add_qnode_params = {
                    'key': "chemical",
                    'categories': ['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']
                }
                self.response = messenger.add_qnode(self.response, add_qnode_params)
                gene_curie = top_predictions['gene_id'].to_list()[0]
                normalizer_res = synonymizer.get_canonical_curies(gene_curie)[gene_curie]
                gene_name = normalizer_res['preferred_name']
                add_qnode_params = {
                    'key': "gene",
                    'name': gene_curie
                }
                self.response = messenger.add_qnode(self.response, add_qnode_params)
                message.knowledge_graph.nodes[gene_curie] = Node(name=gene_name, categories=['biolink:Gene','biolink:Protein'], attributes=[])
                message.knowledge_graph.nodes[gene_curie].qnode_keys = ['gene']

            if model_type == 'increase':
                edge_qualifier_direction = 'increased'
            else:
                edge_qualifier_direction = 'decreased'
            qualifier_set = [
                Qualifier(qualifier_type_id='biolink:object_aspect_qualifier', qualifier_value='activity_or_abundance'),
                Qualifier(qualifier_type_id='biolink:object_direction_qualifier', qualifier_value=edge_qualifier_direction)
            ]
            add_qedge_params = {
                'key': qedge_id,
                'subject': "chemical",
                'object': "gene",
                'predicates': ["biolink:affects"]
            }
            self.response = messenger.add_qedge(self.response, add_qedge_params)
            message.query_graph.edges[add_qedge_params['key']].knowledge_type = "inferred"
            message.query_graph.edges[add_qedge_params['key']].qualifier_constraints = [
                QConstraint(qualifier_set=qualifier_set)
            ]
            message.query_graph.edges[add_qedge_params['key']].filled = True
            chemical_qnode_key = 'chemical'
            gene_qnode_key = 'gene'
            self.response.original_query_graph = copy.deepcopy(message.query_graph)

        else:

            categories_to_add = set()
            if query_chemical:

                chemical_curie = top_predictions['chemical_id'].to_list()[0]
                normalizer_res = synonymizer.get_canonical_curies(chemical_curie)[chemical_curie]
                chemical_name = normalizer_res['preferred_name']

                categories_to_add.update(self.bh.get_ancestors(['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']))
                categories_to_add.update(list(synonymizer.get_normalizer_results(chemical_curie)[chemical_curie]['categories'].keys()))
                categories_to_add = list(categories_to_add)
                message.knowledge_graph.nodes[chemical_curie] = Node(name=chemical_name, categories=categories_to_add, attributes=[])
                chemical_qnode_key = message.query_graph.edges[qedge_id].subject
                gene_qnode_key = message.query_graph.edges[qedge_id].object
                message.knowledge_graph.nodes[chemical_curie].qnode_keys = [chemical_qnode_key]
                # Don't add a new edge in for the treats as there is already an edge there with the knowledge type inferred
                # But do say that this edge has been filled
                message.query_graph.edges[qedge_id].filled = True
                # Nuke the drug categories since they vary depending on what the model returns
                categories_set = set(message.query_graph.nodes[gene_qnode_key].categories)
                categories_set.update(set(['biolink:Gene','biolink:Protein']))
                message.query_graph.nodes[gene_qnode_key].categories = list(categories_set)
            else:

                gene_curie = top_predictions['gene_id'].to_list()[0]
                normalizer_res = synonymizer.get_canonical_curies(gene_curie)[gene_curie]
                gene_name = normalizer_res['preferred_name']

                categories_to_add.update(self.bh.get_ancestors(['biolink:Gene','biolink:Protein']))
                categories_to_add.update(list(synonymizer.get_normalizer_results(gene_curie)[gene_curie]['categories'].keys()))
                categories_to_add = list(categories_to_add)
                message.knowledge_graph.nodes[gene_curie] = Node(name=gene_name, categories=categories_to_add, attributes=[])
                chemical_qnode_key = message.query_graph.edges[qedge_id].subject
                gene_qnode_key = message.query_graph.edges[qedge_id].object
                message.knowledge_graph.nodes[gene_curie].qnode_keys = [gene_qnode_key]
                # Don't add a new edge in for the treats as there is already an edge there with the knowledge type inferred
                # But do say that this edge has been filled
                message.query_graph.edges[qedge_id].filled = True
                # Nuke the drug categories since they vary depending on what the model returns
                categories_set = set(message.query_graph.nodes[chemical_qnode_key].categories)
                categories_set.update(set(['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']))
                message.query_graph.nodes[chemical_qnode_key].categories = list(categories_set)


        # # Just use the chemical and gene that are currently in the QG
        # # now that KG and QG are populated with stuff, shorthand them
        # knodes = message.knowledge_graph.nodes
        # kedges = message.knowledge_graph.edges
        # qnodes = message.query_graph.nodes
        # qedges = message.query_graph.edges

        # If the max path len is 0, that means there are no paths found, so just insert the chemicals/genes with the probability_increase/decrease_activity on them
        if max_path_len == 0:

            essence_scores = {}
            if query_chemical:
                node_ids = list(top_predictions['gene_id'].to_numpy())
                node_info = synonymizer.get_canonical_curies(node_ids)
                node_id_to_canonical_id = {k: v['preferred_curie'] for k, v in node_info.items() if v is not None}
                node_id_to_score = dict(zip(node_ids, top_predictions['tp_prob']))
                # Add the genes to the knowledge graph
                for node_id in node_ids:
                    gene_canonical_id = node_id_to_canonical_id[node_id]
                    gene_categories = [node_info[node_id]['preferred_category']]
                    gene_categories.append('biolink:NamedThing')
                    # add the node to the knowledge graph
                    gene_name = node_info[node_id]['preferred_name']
                    essence_scores[gene_name] = node_id_to_score[node_id]
                    if gene_canonical_id not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[gene_canonical_id] = Node(name=gene_name, categories=gene_categories, attributes=[])
                        message.knowledge_graph.nodes[gene_canonical_id].qnode_keys = [gene_qnode_key]
                    else:  # it's already in the KG, just pass
                        pass
                    # add the edge to the knowledge graph
                    prob_score = node_id_to_score[node_id]
                    edge_attribute_list = [
                        Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                        Attribute(original_attribute_name=None, value=True,
                                    attribute_type_id="EDAM-DATA:1772",
                                    attribute_source="infores:arax", value_type_id="metatype:Boolean",
                                    value_url=None,
                                    description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                        Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity",
                                    value=str(prob_score))
                    ]
                    retrieval_source = [
                                    RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                    ]
                    if model_type == 'increase':
                        edge_qualifier_direction = 'increased'
                    else:
                        edge_qualifier_direction = 'decreased'
                    edge_qualifier_list = [
                        Qualifier(qualifier_type_id='biolink:object_aspect_qualifier', qualifier_value='activity_or_abundance'),
                        Qualifier(qualifier_type_id='biolink:object_direction_qualifier', qualifier_value=edge_qualifier_direction)
                    ]
                    new_edge = Edge(subject=chemical_curie, object=gene_canonical_id, predicate=f'biolink:affects', attributes=edge_attribute_list, qualifiers=edge_qualifier_list, sources=retrieval_source)
                    new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source="infores:arax", kp='infores:rtx-kg2')
                    if new_edge_key not in message.knowledge_graph.edges:
                        message.knowledge_graph.edges[new_edge_key] = new_edge
                        message.knowledge_graph.edges[new_edge_key].filled = True
                        message.knowledge_graph.edges[new_edge_key].qedge_keys = [qedge_id]
            else:
                node_ids = list(top_predictions['gene_id'].to_numpy())
                node_info = synonymizer.get_canonical_curies(node_ids)
                node_id_to_canonical_id = {k: v['preferred_curie'] for k, v in node_info.items() if v is not None}
                node_id_to_score = dict(zip(node_ids, top_predictions['tp_prob']))
                # Add the chemicals to the knowledge graph
                for node_id in node_ids:
                    chemical_canonical_id = node_id_to_canonical_id[node_id]
                    chemical_categories = [node_info[node_id]['preferred_category']]
                    chemical_categories.append('biolink:NamedThing')
                    # add the node to the knowledge graph
                    chemical_name = node_info[node_id]['preferred_name']
                    essence_scores[chemical_name] = node_id_to_score[node_id]
                    if chemical_canonical_id not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[chemical_canonical_id] = Node(name=chemical_name, categories=chemical_categories, attributes=[])
                        message.knowledge_graph.nodes[chemical_canonical_id].qnode_keys = [chemical_qnode_key]
                    else:  # it's already in the KG, just pass
                        pass
                    # add the edge to the knowledge graph
                    prob_score = node_id_to_score[node_id]
                    retrieval_source = [
                                    RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                    ]
                    edge_attribute_list = [
                        Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                        Attribute(original_attribute_name=None, value=True,
                                    attribute_type_id="EDAM-DATA:1772",
                                    attribute_source="infores:arax", value_type_id="metatype:Boolean",
                                    value_url=None,
                                    description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                        Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity", value=str(prob_score))
                    ]
                    if model_type == 'increase':
                        edge_qualifier_direction = 'increased'
                    else:
                        edge_qualifier_direction = 'decreased'
                    edge_qualifier_list = [
                        Qualifier(qualifier_type_id='biolink:object_aspect_qualifier', qualifier_value='activity_or_abundance'),
                        Qualifier(qualifier_type_id='biolink:object_direction_qualifier', qualifier_value=edge_qualifier_direction)
                    ]
                    new_edge = Edge(subject=chemical_canonical_id, object=gene_curie, predicate=f'biolink:affects', attributes=edge_attribute_list, qualifiers=edge_qualifier_list, sources=retrieval_source)
                    new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source="infores:arax", kp='infores:rtx-kg2')
                    if new_edge_key not in message.knowledge_graph.edges:
                        message.knowledge_graph.edges[new_edge_key] = new_edge
                        message.knowledge_graph.edges[new_edge_key].filled = True
                        message.knowledge_graph.edges[new_edge_key].qedge_keys = [qedge_id]

            self.resultify_and_sort(essence_scores)
            return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter

        # Otherwise we do have paths and we need to handle them
        path_keys = [{} for i in range(max_path_len)]
        for i in range(max_path_len+1):
            if (i+1) in path_lengths:

                path_qnodes = [chemical_qnode_key]
                for j in range(i):
                    new_qnode_key = f"creative_CRG_qnode_{self.qnode_global_iter}"
                    path_qnodes.append(new_qnode_key)
                    add_qnode_params = {
                        'key' : new_qnode_key,
                        'option_group_id': f"creative_CRG_option_group_{self.option_global_iter}",
                        "is_set": "true"
                    }
                    self.response = messenger.add_qnode(self.response, add_qnode_params)
                    self.qnode_global_iter += 1
                path_qnodes.append(gene_qnode_key)
                qnode_pairs = list(zip(path_qnodes,path_qnodes[1:]))
                qedge_key_list = []
                for qnode_pair in qnode_pairs:
                    add_qedge_params = {
                        'key': f"creative_CRG_qedge_{self.qedge_global_iter}",
                        'subject': qnode_pair[0],
                        'object': qnode_pair[1],
                        'option_group_id': f"creative_CRG_option_group_{self.option_global_iter}"
                    }      
                    qedge_key_list.append(f"creative_CRG_qedge_{self.qedge_global_iter}")
                    self.qedge_global_iter += 1
                    self.response = messenger.add_qedge(self.response, add_qedge_params)
                    message.query_graph.edges[add_qedge_params['key']].filled = True
                path_keys[i]["qnode_pairs"] = qnode_pairs
                path_keys[i]["qedge_keys"] = qedge_key_list
                self.option_global_iter += 1


        # FW: code that will add resulting paths to the query graph and knowledge graph goes here
        essence_scores = {}
        for (curie1, curie2), paths in top_paths.items():
            path_added = False
            for path in paths:
                if query_chemical:
                    chemical_curie = curie1
                    gene_curie = curie2
                    
                else:
                    chemical_curie = curie2
                    gene_curie = curie1
                    path.reverse()
                n_elements = len(path)
                # Creates edge tuples of the form (node name 1, edge predicate, node name 2)
                edge_tuples = [(path[i],path[i+1],path[i+2]) for i in range(0,n_elements-2,2)]
                path_idx = len(edge_tuples)-1
                for i in range(path_idx+1):
                    subject_qnode_key = path_keys[path_idx]["qnode_pairs"][i][0]
                    subject_curie = edge_tuples[i][0]
                    subject_name = node_info[subject_curie]['preferred_name']
                    subject_category = node_info[subject_curie]['preferred_category']
                    if subject_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[subject_curie] = Node(name=subject_name, categories=[subject_category, 'biolink:NamedThing'], attributes=[])
                        message.knowledge_graph.nodes[subject_curie].qnode_keys = [subject_qnode_key]
                    elif subject_qnode_key not in message.knowledge_graph.nodes[subject_curie].qnode_keys:
                        message.knowledge_graph.nodes[subject_curie].qnode_keys.append(subject_qnode_key)
                    object_qnode_key = path_keys[path_idx]["qnode_pairs"][i][1]
                    object_curie = edge_tuples[i][2]
                    object_name = node_info[object_curie]['preferred_name']
                    object_category = node_info[object_curie]['preferred_category']
                    if object_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[object_curie] = Node(name=object_name, categories=[object_category, 'biolink:NamedThing'], attributes=[])
                        message.knowledge_graph.nodes[object_curie].qnode_keys = [object_qnode_key]
                    elif object_qnode_key not in message.knowledge_graph.nodes[object_curie].qnode_keys:
                        message.knowledge_graph.nodes[object_curie].qnode_keys.append(object_qnode_key)
                    new_edge = edge_tuples[i][1]
                    for key in new_edge:
                        edge_name = decorator._get_kg2c_edge_key(new_edge[key])
                        message.knowledge_graph.edges[edge_name] = new_edge[key]
                        message.knowledge_graph.edges[edge_name].qedge_keys = [path_keys[path_idx]["qedge_keys"][i]]

                   
                path_added = True
            if path_added:
                chem_gene_node_info = synonymizer.get_canonical_curies([chemical_curie,gene_curie])
                preferred_chemical_curie = chem_gene_node_info[chemical_curie]['preferred_curie']
                preferred_gene_curie = chem_gene_node_info[gene_curie]['preferred_curie']
                if query_chemical:
                    regulate_score = top_predictions.loc[top_predictions['gene_id'] == gene_curie]["tp_prob"].iloc[0]
                    essence_scores[chem_gene_node_info[gene_curie]['preferred_name']] = regulate_score
                else:
                    regulate_score = top_predictions.loc[top_predictions['chemical_id'] == chemical_curie]["tp_prob"].iloc[0]
                    essence_scores[chem_gene_node_info[chemical_curie]['preferred_name']] = regulate_score
                edge_attribute_list = [
                    Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                    Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity", value=str(regulate_score))
                ]
                retrieval_source = [
                                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                        ]
                
                edge_predicate = f'biolink:affects'
                if hasattr(message.query_graph.edges[qedge_id], 'predicates') and message.query_graph.edges[qedge_id].predicates:
                    edge_predicate = message.query_graph.edges[qedge_id].predicates[0]  # FIXME: better way to handle multiple predicates?
                if model_type == 'increase':
                    edge_qualifier_direction = 'increased'
                else:
                    edge_qualifier_direction = 'decreased'
                edge_qualifier_list = [
                    Qualifier(qualifier_type_id='biolink:object_aspect_qualifier', qualifier_value='activity_or_abundance'),
                    Qualifier(qualifier_type_id='biolink:object_direction_qualifier', qualifier_value=edge_qualifier_direction)
                ]
                
                fixed_edge = Edge(predicate=edge_predicate, subject=preferred_chemical_curie, object=preferred_gene_curie, attributes=edge_attribute_list, qualifiers=edge_qualifier_list, sources=retrieval_source)
                fixed_edge.qedge_keys = [qedge_id]
                message.knowledge_graph.edges[f"creative_CRG_prediction_{self.kedge_global_iter}"] = fixed_edge
                self.kedge_global_iter += 1
            else:
                self.response.warning(f"Something went wrong when adding the subgraph for the chemical-gene pair ({chemical_curie},{gene_curie}) to the knowledge graph. Skipping this result....")
        self.response = decorator.decorate_nodes(self.response)
        if self.response.status != 'OK':
            return self.response
        self.response = decorator.decorate_edges(self.response)
        if self.response.status != 'OK':
            return self.response
        #FIXME: this might cause a problem since it doesn't add optional groups for 1 and 2 hops
        # This might also cause issues when infer is on an intermediate edge
        self.resultify_and_sort(essence_scores)

        return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
