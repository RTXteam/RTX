#!/bin/env python3
"""
InferUtilities: Builds TRAPI-compliant knowledge graph subgraphs from xDTD/xCRG prediction results.

This module is the bridge between prediction databases and the ARAX TRAPI response.
It takes prediction scores + explanation paths from ExplainableDTD and builds proper
knowledge graph nodes, edges, query graph extensions, and result objects following the TRAPI specification.

Main responsibilities:
  - genrete_treat_subgraphs(): Converts xDTD drug-disease prediction results into TRAPI KG.
  - genrete_regulate_subgraphs(): Converts xCRG chemical-gene prediction results into TRAPI KG.
  - Looks up node/edge metadata from the xDTD mapping database (Translator KG JSONL-based).
  - Handles variable-length explanation paths (1-hop, 2-hop, 3-hop).
  - Creates proper TRAPI attributes, retrieval sources, and qualifiers.

"""

import sys
import os
import json
import math
import copy
from typing import List, Dict, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_resultify import ARAXResultify
from util import get_arax_edge_key
from biolink_helper import get_biolink_helper

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
    """Utility class for building TRAPI-compliant subgraphs from inference results.

    The two main entry points are:
      - genrete_treat_subgraphs(): for drug-disease treatment predictions (xDTD).
      - genrete_regulate_subgraphs(): for chemical-gene regulation predictions (xCRG).
    """

    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.report_stats = True
        self.bh = get_biolink_helper()

    @staticmethod
    def _get_primary_knowledge_source(edge_info):
        """Extract the primary_knowledge_source from the Translator KG edge schema.

        Uses the pipe-delimited resource_id/resource_role fields for fast lookup,
        falling back to parsing the full JSON sources array.

        Returns 'infores:arax-xdtd' if no primary knowledge source is found.
        """
        resource_ids = edge_info.resource_id
        resource_roles = edge_info.resource_role
        if resource_ids and resource_roles:
            ids = resource_ids.split('|')
            roles = resource_roles.split('|')
            for rid, role in zip(ids, roles):
                if role == 'primary_knowledge_source':
                    return rid
        if edge_info.sources:
            try:
                sources = json.loads(edge_info.sources)
                for s in sources:
                    if s.get('resource_role') == 'primary_knowledge_source':
                        return s.get('resource_id', 'infores:arax-xdtd')
            except (json.JSONDecodeError, TypeError):
                pass
        return "infores:arax-xdtd"

    @staticmethod
    def _build_retrieval_sources(edge_info, kp='infores:arax-xdtd'):
        """Build TRAPI RetrievalSource objects from the Translator KG edge sources JSON.

        The sources form an ordered chain: the first entry is the primary_knowledge_source
        (no upstream), and each subsequent entry is an aggregator whose upstream_resource_ids
        points to the previous entry. This method preserves that chain and appends kp as
        the final aggregator.

        Example chain from edge_info.sources:
          [infores:mgi (primary)] -> [infores:agrkb (aggregator, upstream=[infores:mgi])]
        becomes:
          [infores:mgi (primary)] -> [infores:agrkb (aggregator)] -> [infores:arax-xdtd (aggregator)]
        """
        fallback = [RetrievalSource(resource_id=kp, resource_role="primary_knowledge_source")]
        if not edge_info.sources:
            return fallback
        try:
            sources = json.loads(edge_info.sources)
        except (json.JSONDecodeError, TypeError):
            return fallback
        if not sources:
            return fallback

        retrieval_sources = []
        for s in sources:
            retrieval_sources.append(RetrievalSource(
                resource_id=s['resource_id'],
                resource_role=s['resource_role'],
                upstream_resource_ids=s.get('upstream_resource_ids') or None
            ))

        retrieval_sources.append(RetrievalSource(
            resource_id=kp,
            resource_role='aggregator_knowledge_source',
            upstream_resource_ids=[sources[-1]['resource_id']]
        ))
        return retrieval_sources

    def __get_formated_edge_key(self, edge: Edge, primary_knowledge_source: str, kp: str = 'infores:arax-xdtd') -> str:
        """Build an edge key for a knowledge graph edge.

        The edge key is a unique identifier for a knowledge graph edge.
        It is constructed from the subject, predicate, object, qualifier details, and provenancen

        Args:
            edge: The Edge object to build the key for.
            primary_knowledge_source: The primary knowledge source for the edge.
            kp: The knowledge provider for the edge.
        Returns:
            The edge key.
        """
        qualifiers_dict = {qualifier.qualifier_type_id: qualifier.qualifier_value for qualifier in edge.qualifiers} if edge.qualifiers else dict()
        qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate")
        qualified_object_direction = qualifiers_dict.get("biolink:object_direction_qualifier")
        qualified_object_aspect = qualifiers_dict.get("biolink:object_aspect_qualifier")
        qualified_portion = f"{qualified_predicate}--{qualified_object_direction}--{qualified_object_aspect}"
        edge_key = f"{kp}:{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--{primary_knowledge_source}"
        
        return edge_key

    def __none_to_zero(self, val):
        """Coerce None to 0 for safe numeric sorting."""
        if val is None:
            return 0
        else: 
            return val

    def resultify_and_sort(self, essence_scores):
        """Run ARAXResultify to group KG edges into TRAPI Results, then rank by prediction score.

        ARAXResultify matches knowledge graph edges to query graph patterns, producing TRAPI Result
        objects. After resultification, each result's score is set based on ARAX's ranking algorithm
        (which considers the probability_treats attribute), then sorted descending.

        Args:
            essence_scores: Dict mapping result essence (node name) -> prediction probability score.
        """
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
                self.response.warning(
                    f"Error retrieving score for result essence {result.essence}. Setting result score to None.")
        message.results.sort(key=lambda x: self.__none_to_zero(x.score), reverse=True)

    def genrete_treat_subgraphs(self, response: ARAXResponse, top_scores: pd.DataFrame, top_paths: dict, drug_curie: Optional[str], disease_curie: Optional[str], qedge_id=None):
        """
        Convert xDTD prediction results into a TRAPI-compliant knowledge graph subgraph.

        This is the core method that processes the xDTD model's prediction scores and
        explanation paths, inserting them into the ARAX response message as proper nodes, edges,
        query graph extensions, and results.

        The method handles three scenarios:
          1. Both drug_curie and disease_curie given: single pair prediction.
          2. Only drug_curie given: predict diseases treatable by this drug.
          3. Only disease_curie given: predict drugs that can treat this disease.

        Args:
            response: ARAXResponse object to amend.
            top_scores: DataFrame with columns [drug_id, drug_name, disease_id, disease_name, tn_score, tp_score, unknown_score].
            top_paths: Dict mapping (drug_id, disease_id) -> list of [path_string, path_score].
            drug_curie: Preferred drug CURIE (None if querying by disease only).
            disease_curie: Preferred disease CURIE (None if querying by drug only).
            qedge_id: Query edge ID to attach results to (None if QG is empty).

        Returns:
            Tuple of (response, kedge_global_iter, qedge_global_iter, qnode_global_iter, option_global_iter).
        """
        # --- Initialization ---
        self.response = response
        self.kedge_global_iter = 0
        self.qedge_global_iter = 0
        self.qnode_global_iter = 0
        self.option_global_iter = 0
        self.qedge_id = qedge_id
        message = self.response.envelope.message
        self.kp = 'infores:arax-xdtd'

        # Check to make sure that the qedge_id either exists and is in the QG, or else does not exist and the QG is empty
        if qedge_id is not None:
            if not hasattr(message, 'query_graph') or qedge_id not in message.query_graph.edges:
                self.response.error(f"qedge_id {qedge_id} not in QG, QG is {message.query_graph}")
                raise Exception(f"qedge_id {qedge_id} not in QG")
        elif hasattr(message, 'query_graph'):
            if len(message.query_graph.edges) > 0:
                self.response.error("qedge_id is None but QG is not empty")
                raise Exception("qedge_id is None but QG is not empty")

        messenger = ARAXMessenger()

        # Connect to the xDTD mapping database for node/edge metadata lookups.
        # The mapping DB maps xDTD internal node/edge IDs to Translator KG metadata.
        xdtdmapping = xDTDMappingDB(database_name=RTXConfig.explainable_dtd_db_path.split('/')[-1], mode='run', db_loc=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction']))

        
        # Determine the set of distinct path lengths across all drug-disease pairs.
        # Path strings look like "A->pred1->B->pred2->C", so n_elements = 2*n_hops + 1;
        # floor(n_elements/2) gives the number of hops.
        path_lengths = set([math.floor(len(x[0].split("->"))/2.) for paths in top_paths.values() for x in paths])
        try:
            max_path_len = max(path_lengths)
        except ValueError:
            max_path_len = 0

        # Preserve the original query graph before we modify it with inferred edges/nodes
        if len(message.query_graph.edges) !=0 and not hasattr(self.response, 'original_query_graph'):
            self.response.original_query_graph = copy.deepcopy(message.query_graph)

        if drug_curie and disease_curie:
            query_drug_curie = top_scores['drug_id'].tolist()[0]
            query_drug_name = top_scores['drug_name'].tolist()[0]
            query_drug_info = xdtdmapping.get_node_info(node_id=query_drug_curie)
            if query_drug_info is None:
                self.response.warning(f"Could not find {drug_curie} in NODE_MAPPING table")
                return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
            query_drug_categories = query_drug_info.category
            
            query_disease_curie = top_scores['disease_id'].tolist()[0]
            query_disease_name = top_scores['disease_name'].tolist()[0]
            query_disease_info = xdtdmapping.get_node_info(node_id=query_disease_curie)
            if query_disease_info is None:
                self.response.warning(f"Could not find {disease_curie} in NODE_MAPPING table")
                return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
            query_disease_categories = query_disease_info.category
            
            
        elif drug_curie:
            query_drug_curie = top_scores['drug_id'].tolist()[0]
            query_drug_name = top_scores['drug_name'].tolist()[0]
            query_drug_info = xdtdmapping.get_node_info(node_id=query_drug_curie)
            if query_drug_info is None:
                self.response.warning(f"Could not find {drug_curie} in NODE_MAPPING table due to using refreshed xDTD database")
                return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
            query_drug_categories = query_drug_info.category
            
        elif disease_curie:
            query_disease_curie = top_scores['disease_id'].tolist()[0]
            query_disease_name = top_scores['disease_name'].tolist()[0]
            query_disease_info = xdtdmapping.get_node_info(node_id=query_disease_curie)
            if query_disease_info is None:
                self.response.warning(f"Could not find {disease_curie} in NODE_MAPPING table due to using refreshed xDTD database")
                return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
            query_disease_categories = query_disease_info.category

        # if the knowledge graph is empty, create it
        if not message.knowledge_graph or not hasattr(message, 'knowledge_graph'):
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
            
            # Helper function to add a qnode and a kg node
            def _add_qnode_and_kg_node(qnode_key, name=None, categories=None, curie=None, info=None):
                params = {'key': qnode_key}
                if name is not None:
                    params['name'] = name
                if categories is not None:
                    params['categories'] = categories
                self.response = messenger.add_qnode(self.response, params)
                if curie and info:
                    resolved_categories = categories if categories else info.category
                    message.knowledge_graph.nodes[curie] = Node(
                        name=name if name else info.name,
                        categories=resolved_categories,
                        attributes=[]
                    )
                    message.knowledge_graph.nodes[curie].qnode_keys = [qnode_key]

            drug_qnode_key = "drug"
            disease_qnode_key = "disease"

            if drug_curie and disease_curie:
                _add_qnode_and_kg_node(
                    drug_qnode_key, query_drug_name, query_drug_categories, query_drug_curie, query_drug_info
                )
                _add_qnode_and_kg_node(
                    disease_qnode_key, query_disease_name, query_disease_categories, query_disease_curie, query_disease_info
                )
            elif drug_curie:
                _add_qnode_and_kg_node(
                    drug_qnode_key, query_drug_name, query_drug_categories, query_drug_curie, query_drug_info
                )
                _add_qnode_and_kg_node(
                    disease_qnode_key, categories=['biolink:Disease', 'biolink:PhenotypicFeature']
                )
            elif disease_curie:
                _add_qnode_and_kg_node(
                    disease_qnode_key, query_disease_name, query_disease_categories, query_disease_curie, query_disease_info
                )
                _add_qnode_and_kg_node(
                    drug_qnode_key, categories=['biolink:Drug', 'biolink:SmallMolecule', 'biolink:ChemicalEntity']
                )

            add_qedge_params = {
                'key': qedge_id,
                'subject': drug_qnode_key,
                'object': disease_qnode_key,
                'predicates': ["biolink:treats"]
            }
            self.response = messenger.add_qedge(self.response, add_qedge_params)
            message.query_graph.edges[add_qedge_params['key']].knowledge_type = "inferred"
            message.query_graph.edges[add_qedge_params['key']].filled = True
            self.response.original_query_graph = copy.deepcopy(message.query_graph)
        else:
            message.query_graph.edges[qedge_id].filled = True
            drug_qnode_key = response.envelope.message.query_graph.edges[qedge_id].subject
            disease_qnode_key = response.envelope.message.query_graph.edges[qedge_id].object
            if drug_curie and disease_curie:
                message.knowledge_graph.nodes[query_drug_curie] = Node(name=query_drug_name, categories=query_drug_categories, attributes=[])
                message.knowledge_graph.nodes[query_drug_curie].qnode_keys = [drug_qnode_key]
                message.knowledge_graph.nodes[query_disease_curie] = Node(name=query_disease_name, categories=query_disease_categories, attributes=[])
                message.knowledge_graph.nodes[query_disease_curie].qnode_keys = [disease_qnode_key]
            elif drug_curie:
                message.knowledge_graph.nodes[query_drug_curie] = Node(name=query_drug_name, categories=query_drug_categories, attributes=[])
                message.knowledge_graph.nodes[query_drug_curie].qnode_keys = [drug_qnode_key]
                message.query_graph.nodes[disease_qnode_key].categories = ['biolink:Disease', 'biolink:PhenotypicFeature']
            elif disease_curie:
                message.knowledge_graph.nodes[query_disease_curie] = Node(name=query_disease_name, categories=query_disease_categories, attributes=[])
                message.knowledge_graph.nodes[query_disease_curie].qnode_keys = [disease_qnode_key]
                message.query_graph.nodes[drug_qnode_key].categories = ['biolink:Drug', 'biolink:SmallMolecule', 'biolink:ChemicalEntity']


        # If the max path len is 0, that means there are no paths found, so just insert the drugs with the probability_treats on them
        if max_path_len == 0:
            essence_scores = {}
            
            def _add_node_and_edge(node_ids, node_id_to_score, node_role_key, edge_subject_func, edge_object_func):
                for canonical_id in node_ids:
                    try:
                        node_info = xdtdmapping.get_node_info(node_id=canonical_id)
                    except Exception:
                        continue
                    if not node_info:
                        continue
                    categories = node_info.category
                    name = node_info.name
                    essence_scores[name] = node_id_to_score[canonical_id]
                    if canonical_id not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[canonical_id] = Node(name=name, categories=categories, attributes=[])
                        message.knowledge_graph.nodes[canonical_id].qnode_keys = [node_role_key]
                    # Add the edge to the knowledge graph
                    treat_score = node_id_to_score[canonical_id]
                    edge_attribute_list = [
                        Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                        Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source=self.kp, value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                        Attribute(attribute_type_id="EDAM-DATA:0951", original_attribute_name="probability_treats", value=str(treat_score)),
                        Attribute(attribute_source=self.kp, attribute_type_id="biolink:agent_type", value="computational_model"),
                        Attribute(attribute_source=self.kp, attribute_type_id="biolink:knowledge_level", value="prediction"),
                    ]
                    retrieval_source = [
                        RetrievalSource(resource_id=self.kp, resource_role="primary_knowledge_source")
                    ]
                    # Use the functions to determine subject and object based on current canonical_id
                    edge_subject = edge_subject_func(canonical_id)
                    edge_object = edge_object_func(canonical_id)
                    new_edge = Edge(subject=edge_subject, object=edge_object, predicate='biolink:treats', attributes=edge_attribute_list, sources=retrieval_source)
                    new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source=self.kp, kp=self.kp)
                    if new_edge_key not in message.knowledge_graph.edges:
                        message.knowledge_graph.edges[new_edge_key] = new_edge
                        message.knowledge_graph.edges[new_edge_key].filled = True
                        message.knowledge_graph.edges[new_edge_key].qedge_keys = [qedge_id]
                self.resultify_and_sort(essence_scores)
                return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter

            if drug_curie:
                node_ids = top_scores['disease_id']
                node_id_to_score = dict(zip(node_ids, top_scores['tp_score']))
                return _add_node_and_edge(node_ids, node_id_to_score, disease_qnode_key, lambda cid: drug_curie, lambda cid: cid)
            else:
                node_ids = top_scores['drug_id']
                node_id_to_score = dict(zip(node_ids, top_scores['tp_score']))
                return _add_node_and_edge(node_ids, node_id_to_score, drug_qnode_key, lambda cid: cid, lambda cid: disease_curie)
                
    
        # ── Build query graph template for variable-length explanation paths ──
        # Each distinct path length (1-hop, 2-hop, 3-hop) gets its own "option group" in the QG.
        # For a 2-hop path: drug -> intermediate_node -> disease, we create:
        #   - 1 intermediate qnode (creative_DTD_qnode_X)
        #   - 2 qedges (drug->intermediate, intermediate->disease)
        # path_keys[i] stores the qnode_pairs and qedge_keys for paths of length (i+1).
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

        # ── Insert explanation path nodes and edges into the knowledge graph ──
        # Each path string is "node1->predicate1->node2->predicate2->node3".
        # We split it, look up each node/edge in the mapping DB, and insert TRAPI objects.
        essence_scores = {}
        for (drug, disease), paths in top_paths.items():
            path_added = False
            # x[0] is the path string; x[1] is the path score generated by xDTD model 
            split_paths = [x[0].split("->") for x in paths]
            for path in split_paths:
                path_drug_curie = path[0]
                path_disease_curie = path[-1]  # Last element in the path is disease
                n_elements = len(path)

                # Look up each (subject, predicate, object) triple from the mapping DB.
                # Each triple may return multiple edges (e.g., from different knowledge sources).
                edges_info = []
                break_flag = False
                for i in range(0,n_elements-2,2):
                    edge_info = xdtdmapping.get_edge_info(triple_id=(path[i],path[i+1],path[i+2]))
                    if len(edge_info) == 0:
                        break_flag = True
                    else:
                        edges_info.append(edge_info)
                    
                if break_flag:
                    continue
                
                # path_idx is 0-based index into path_keys for the correct QG template
                path_idx = len(edges_info)-1

                for i in range(path_idx+1):
                    subject_qnode_key = path_keys[path_idx]["qnode_pairs"][i][0]
                    subject_curie = edges_info[i][0].subject
                    try:
                        subject_node_info = xdtdmapping.get_node_info(node_id=subject_curie)
                    except Exception:
                        break_flag = True
                        break
                    if subject_node_info is None:
                        break_flag = True
                        break
                    subject_name = subject_node_info.name
                    subject_categories = subject_node_info.category
                    if subject_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[subject_curie] = Node(name=subject_name, categories=subject_categories, attributes=[])
                        message.knowledge_graph.nodes[subject_curie].qnode_keys = [subject_qnode_key]
                    elif subject_qnode_key not in message.knowledge_graph.nodes[subject_curie].qnode_keys:
                        message.knowledge_graph.nodes[subject_curie].qnode_keys.append(subject_qnode_key)
                    object_qnode_key = path_keys[path_idx]["qnode_pairs"][i][1]
                    object_curie = edges_info[i][0].object
                    try:
                        object_node_info = xdtdmapping.get_node_info(node_id=object_curie)
                    except Exception:
                        break_flag = True
                        break
                    if object_node_info is None:
                        break_flag = True
                        break
                    object_name = object_node_info.name
                    object_categories = object_node_info.category
                    if object_curie not in message.knowledge_graph.nodes:
                        message.knowledge_graph.nodes[object_curie] = Node(name=object_name, categories=object_categories, attributes=[])
                        message.knowledge_graph.nodes[object_curie].qnode_keys = [object_qnode_key]
                    elif object_qnode_key not in message.knowledge_graph.nodes[object_curie].qnode_keys:
                        message.knowledge_graph.nodes[object_curie].qnode_keys.append(object_qnode_key)
                    predicate = edges_info[i][0].predicate

                    if predicate == "SELF_LOOP_RELATION":
                        break_flag = True
                        break

                    for edge_info in edges_info[i]:
                        primary_knowledge_source = self._get_primary_knowledge_source(edge_info)
                        new_edge = Edge(subject=subject_curie, object=object_curie, predicate=predicate, attributes=[], sources=[])
                        edge_attribute_list = [
                            Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                            Attribute(attribute_source=self.kp, attribute_type_id="biolink:agent_type", value=edge_info.agent_type),
                            Attribute(attribute_source=self.kp, attribute_type_id="biolink:knowledge_level", value=edge_info.knowledge_level),
                            Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax-xdtd", value_type_id="metatype:Boolean", value_url=None, description="This edge was extracted from Translator KG by ARAXInfer."),
                        ]
                        retrieval_source = self._build_retrieval_sources(edge_info, kp=self.kp)
                        new_edge.attributes += edge_attribute_list
                        new_edge.sources += retrieval_source
                        new_edge_key = self.__get_formated_edge_key(edge=new_edge, primary_knowledge_source=primary_knowledge_source, kp=self.kp)
                        message.knowledge_graph.edges[new_edge_key] = new_edge
                        message.knowledge_graph.edges[new_edge_key].qedge_keys = [path_keys[path_idx]["qedge_keys"][i]]
                    if break_flag:
                        break
                path_added = True
            if path_added:
                # ── Create the primary "treats" prediction edge ──
                # This is the top-level inferred edge connecting the drug to the disease,
                # carrying the xDTD model's probability_treats score as an attribute.
                # The explanation path edges above provide supporting evidence for this prediction.
                treat_score = top_scores.loc[(top_scores['drug_id'] == drug) & (top_scores['disease_id'] == disease)]["tp_score"].iloc[0]
                path_drug_node_info = xdtdmapping.get_node_info(node_id=path_drug_curie)
                path_disease_node_info = xdtdmapping.get_node_info(node_id=path_disease_curie)
                
                # essence_scores maps the "varying" node name to its score for result ranking.
                # The "varying" node is the one predicted by the model (not the query input).
                if drug_curie and disease_curie:
                    # Both are fixed, use drug name for scoring
                    essence_scores[path_drug_node_info.name] = treat_score
                elif drug_curie:
                    # Fixed drug, varying diseases - score the disease
                    essence_scores[path_disease_node_info.name] = treat_score
                else:
                    # Fixed disease, varying drugs - score the drug
                    essence_scores[path_drug_node_info.name] = treat_score
                
                edge_attribute_list = [
                    Attribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                    Attribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source=self.kp, value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges."),
                    Attribute(attribute_type_id="EDAM-DATA:0951", original_attribute_name="probability_treats", value=str(treat_score)),
                    Attribute(attribute_source=self.kp, attribute_type_id="biolink:agent_type", value="computational_model"),
                    Attribute(attribute_source=self.kp, attribute_type_id="biolink:knowledge_level", value="prediction"),
                ]
                retrieval_source = [
                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                    ]
                #edge_predicate = qedge_id
                edge_predicate = "biolink:treats"
                # comment the following two lines for issue #2253, we now use "biolink:treats_or_applied_or_studied_to_treat" instead of "biolink:treats"
                # if hasattr(message.query_graph.edges[qedge_id], 'predicates') and message.query_graph.edges[qedge_id].predicates:
                #     edge_predicate = message.query_graph.edges[qedge_id].predicates[0]  # FIXME: better way to handle multiple predicates?
                
                fixed_edge = Edge(predicate=edge_predicate, subject=path_drug_node_info.id, object=path_disease_node_info.id,
                                attributes=edge_attribute_list, sources=retrieval_source)
                #fixed_edge.qedge_keys = ["treats"]
                fixed_edge.qedge_keys = [qedge_id]
                message.knowledge_graph.edges[f"creative_DTD_prediction_{self.kedge_global_iter}"] = fixed_edge
                self.kedge_global_iter += 1
            else:
                self.response.warning(f"Something went wrong when adding the subgraph for the drug-disease pair ({drug},{disease}) to the knowledge graph. Skipping this result....")

        # TODO(#2731): node/edge EPC backfill via the legacy decorator was removed
        # when the Tier0 sqlite was thinned to publications/neighbors/category_counts.
        # If XDTD subgraphs need full EPC, the right source is a Retriever lookup
        # for the manually-constructed nodes/edges; that is a separate Infer-team
        # follow-up and is intentionally not done here.

        #FIXME: this might cause a problem since it doesn't add optional groups for 1 and 2 hops
        # This might also cause issues when infer is on an intermediate edge
        self.resultify_and_sort(essence_scores)
        

        return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter

    def genrete_regulate_subgraphs(self, response: ARAXResponse, query_chemical: Optional[str], top_predictions: pd.DataFrame, top_paths: dict, qedge_id=None, model_type: str = 'increase'):
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

        messenger = ARAXMessenger()
        synonymizer = NodeSynonymizer()
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
                        Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity", value=str(prob_score)),
                        Attribute(attribute_source="infores:arax", attribute_type_id="biolink:agent_type", value="computational_model"),
                        Attribute(attribute_source="infores:arax", attribute_type_id="biolink:knowledge_level", value="prediction"),
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
                node_ids = list(top_predictions['chemical_id'].to_numpy())
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
                        Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity", value=str(prob_score)),
                        Attribute(attribute_source="infores:arax", attribute_type_id="biolink:agent_type", value="computational_model"),
                        Attribute(attribute_source="infores:arax", attribute_type_id="biolink:knowledge_level", value="prediction"),
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
            if query_chemical:
                chemical_curie = curie1
                gene_curie = curie2
                    
            else:
                chemical_curie = curie2
                gene_curie = curie1
            path_added = False
            for path in paths:
                if not query_chemical:
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
                        edge_name = 'infores:dogpark-tier0:' + get_arax_edge_key(new_edge[key])
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
                    Attribute(attribute_type_id="EDAM-OPERATION:2434", original_attribute_name=f"probably_{model_type}_activity", value=str(regulate_score)),
                    Attribute(attribute_source="infores:arax", attribute_type_id="biolink:agent_type", value="computational_model"),
                    Attribute(attribute_source="infores:arax", attribute_type_id="biolink:knowledge_level", value="prediction"),
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
        # TODO(#2731): see genrete_treat_subgraphs above. Node/edge EPC backfill
        # via the legacy decorator was removed; a Retriever-based replacement is
        # a separate Infer-team follow-up.
        #FIXME: this might cause a problem since it doesn't add optional groups for 1 and 2 hops
        # This might also cause issues when infer is on an intermediate edge
        self.resultify_and_sort(essence_scores)

        return self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter
