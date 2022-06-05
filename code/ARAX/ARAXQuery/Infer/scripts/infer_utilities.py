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
import traceback
from collections import Counter
from collections.abc import Hashable
from itertools import combinations
import copy

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer




class InferUtilities:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.report_stats = True  

    def __get_formated_edge_key(self, edge: Edge, kp: str = 'infores:rtx-kg2') -> str:
        return f"{kp}:{edge.subject}-{edge.predicate}-{edge.object}"

    def __none_to_zero(self, val):
        if val is None:
            return 0
        else: 
            return val

    def genrete_treat_subgraphs(self, response: ARAXResponse, top_drugs: pd.DataFrame, top_paths: dict, kedge_global_iter: int=0, qedge_global_iter: int=0, qnode_global_iter: int=0, option_global_iter: int=0):
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

        expander = ARAXExpander()
        messenger = ARAXMessenger()
        synonymizer = NodeSynonymizer()
        decorator = ARAXDecorator()

        kp = 'infores:rtx-kg2'

        # FW: This would be an example of how to get node info from curies instead of names
        #node_curies = set([y for paths in top_paths.values() for x in paths for y in x[0].split("->")[::2] if y != ''])
        #node_info = synonymizer.get_canonical_curies(curies=list(node_curies))
        node_names = set([y for paths in top_paths.values() for x in paths for y in x[0].split("->")[::2] if y != ''])
        node_info = synonymizer.get_canonical_curies(names=list(node_names))
        node_name_to_id = {k:v['preferred_curie'] for k,v in node_info.items() if v is not None}
        path_lengths = set([math.floor(len(x[0].split("->"))/2.) for paths in top_paths.values() for x in paths])
        max_path_len = max(path_lengths)
        disease = list(top_paths.keys())[0][1]
        disease_name = list(top_paths.values())[0][0][0].split("->")[-1]
        add_qnode_params = {
            'key' : "disease",
            'name': disease
        }
        self.response = messenger.add_qnode(self.response, add_qnode_params)
        self.response.envelope.message.knowledge_graph.nodes[disease] = Node(name=disease_name, categories=['biolink:DiseaseOrPhenotypicFeature'])
        self.response.envelope.message.knowledge_graph.nodes[disease].qnode_keys = ['disease']
        node_name_to_id[disease_name] = disease
        add_qnode_params = {
            'key' : "drug",
            'categories': ['biolink:Drug']
        }
        self.response = messenger.add_qnode(self.response, add_qnode_params)
        add_qedge_params = {
            'key' : "probably_treats",
            'subject' : "drug",
            'object' : "disease",
            'predicates': ["biolink:probably_treats"]
        }
        self.response = messenger.add_qedge(self.response, add_qedge_params)
        path_keys = [{} for i in range(max_path_len)]
        for i in range(max_path_len+1):
            if (i+1) in path_lengths:
                path_qnodes = ["drug"]
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
                path_qnodes.append("disease")
                qnode_pairs = list(zip(path_qnodes,path_qnodes[1:]))
                qedge_key_list = []
                for qnode_pair in qnode_pairs:
                    add_qedge_params = {
                        'key' : f"creative_DTD_qedge_{self.qedge_global_iter}",
                        'subject' : qnode_pair[0],
                        'object' : qnode_pair[1],
                        'option_group_id': f"creative_DTD_option_group_{self.option_global_iter}"
                    }
                    qedge_key_list.append(f"creative_DTD_qedge_{self.qedge_global_iter}")
                    self.qedge_global_iter += 1
                    self.response = messenger.add_qedge(self.response, add_qedge_params)
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
                drug_name = path[0]
                if any([x not in node_name_to_id for x in path[::2]]):
                    continue
                n_elements = len(path)
                # Creates edge tuples of the form (node name 1, edge predicate, node name 2)
                edge_tuples = [(path[i],path[i+1],path[i+2]) for i in range(0,n_elements-2,2)]
                path_idx = len(edge_tuples)-1
                added_nodes = set()
                for i in range(path_idx+1):
                    subject_qnode_key = path_keys[path_idx]["qnode_pairs"][i][0]
                    subject_name = edge_tuples[i][0]
                    subject_curie = node_name_to_id[subject_name]
                    subject_category = node_info[subject_name]['preferred_category']
                    if subject_curie not in self.response.envelope.message.knowledge_graph.nodes:
                        self.response.envelope.message.knowledge_graph.nodes[subject_curie] = Node(name=subject_name, categories=[subject_category])
                        self.response.envelope.message.knowledge_graph.nodes[subject_curie].qnode_keys = [subject_qnode_key]
                    elif subject_qnode_key not in self.response.envelope.message.knowledge_graph.nodes[subject_curie].qnode_keys:
                        self.response.envelope.message.knowledge_graph.nodes[subject_curie].qnode_keys.append(subject_qnode_key)
                    object_qnode_key = path_keys[path_idx]["qnode_pairs"][i][1]
                    object_name = edge_tuples[i][2]
                    object_curie = node_name_to_id[object_name]
                    object_category = node_info[object_name]['preferred_category']
                    if object_curie not in self.response.envelope.message.knowledge_graph.nodes:
                        self.response.envelope.message.knowledge_graph.nodes[object_curie] = Node(name=object_name, categories=[object_category])
                        self.response.envelope.message.knowledge_graph.nodes[object_curie].qnode_keys = [object_qnode_key]
                    elif object_qnode_key not in self.response.envelope.message.knowledge_graph.nodes[object_curie].qnode_keys:
                        self.response.envelope.message.knowledge_graph.nodes[object_curie].qnode_keys.append(object_qnode_key)
                    new_edge = Edge(subject=subject_curie, object=object_curie, predicate=edge_tuples[i][1], attributes=[])
                    new_edge.attributes.append(EdgeAttribute(attribute_type_id="biolink:aggregator_knowledge_source",
                                         value=kp,
                                         value_type_id="biolink:InformationResource",
                                         attribute_source=kp))
                    new_edge_key = self.__get_formated_edge_key(edge=new_edge, kp=kp)
                    self.response.envelope.message.knowledge_graph.edges[new_edge_key] = new_edge
                    self.response.envelope.message.knowledge_graph.edges[new_edge_key].qedge_keys = [path_keys[path_idx]["qedge_keys"][i]]
                path_added = True
            if path_added:
                treat_score = top_drugs.loc[top_drugs['drug_id'] == drug]["tp_score"].iloc[0]
                essence_scores[drug_name] = treat_score
                edge_attribute_list = [
                    # EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                    EdgeAttribute(original_attribute_name="provided_by", value="infores:arax", attribute_type_id="biolink:aggregator_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                    EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="biolink:computed_value", attribute_source="infores:arax-reasoner-ara", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    EdgeAttribute(attribute_type_id="EDAM:data_0951", original_attribute_name="probability_treats", value=str(treat_score))
                ]
                fixed_edge = Edge(predicate="biolink:probably_treats", subject=node_name_to_id[drug_name], object=node_name_to_id[disease_name],
                                attributes=edge_attribute_list)
                fixed_edge.qedge_keys = ["probably_treats"]
                self.response.envelope.message.knowledge_graph.edges[f"creative_DTD_prediction_{self.kedge_global_iter}"] = fixed_edge
                self.kedge_global_iter += 1
            else:
                self.response.warning(f"Something went wrong when adding the subgraph for the drug-disease pair ({drug},{disease}) to the knowledge graph. Skipping this result....")
        self.response = decorator.decorate_nodes(self.response)
        if self.response.status != 'OK':
            return self.response
        self.response = decorator.decorate_edges(self.response)
        if self.response.status != 'OK':
            return self.response
        resultifier = ARAXResultify()
        resultify_params = {
            "ignore_edge_direction": "true"
        }
        self.response = resultifier.apply(self.response, resultify_params)
        for result in self.response.envelope.message.results:
            if result.essence in essence_scores:
                result.score = essence_scores[result.essence]
            else:
                result.score = None
                self.response.warning(f"Error retrieving score for result essence {result.essence}. Setting result score to None.")
        self.response.envelope.message.results.sort(key=lambda x: self.__none_to_zero(x.score), reverse=True)
        

        return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter

