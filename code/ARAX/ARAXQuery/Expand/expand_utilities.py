#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import copy
import sys
import os
import traceback
import yaml
from typing import List, Dict, Union, Set, Tuple, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.message import Message
from openapi_server.models.response import Response
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_resultify import ARAXResultify
from ARAX_overlay import ARAXOverlay
from ARAX_ranker import ARAXRanker
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from smartapi import SmartAPI
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../BiolinkHelper/")
from biolink_helper import BiolinkHelper

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"

class QGOrganizedKnowledgeGraph:
    def __init__(self, nodes: Dict[str, Dict[str, Node]] = None, edges: Dict[str, Dict[str, Edge]] = None):
        self.nodes_by_qg_id = nodes if nodes else dict()
        self.edges_by_qg_id = edges if edges else dict()

    def __str__(self):
        return f"nodes_by_qg_id:\n{self.nodes_by_qg_id}\nedges_by_qg_id:\n{self.edges_by_qg_id}"

    def add_node(self, node_key: str, node: Node, qnode_key: str):
        if qnode_key not in self.nodes_by_qg_id:
            self.nodes_by_qg_id[qnode_key] = dict()
        # Merge attributes if this node already exists
        if node_key in self.nodes_by_qg_id[qnode_key]:
            existing_node = self.nodes_by_qg_id[qnode_key][node_key]
            new_node_attributes = node.attributes if node.attributes else []
            if existing_node.attributes:
                existing_attribute_triples = {get_attribute_triple(attribute) for attribute in existing_node.attributes}
                new_attributes_unique = [attribute for attribute in new_node_attributes
                                         if get_attribute_triple(attribute) not in existing_attribute_triples]
                existing_node.attributes += new_attributes_unique
            else:
                existing_node.attributes = new_node_attributes
        else:
            self.nodes_by_qg_id[qnode_key][node_key] = node

    def add_edge(self, edge_key: str, edge: Edge, qedge_key: str):
        if qedge_key not in self.edges_by_qg_id:
            self.edges_by_qg_id[qedge_key] = dict()
        self.edges_by_qg_id[qedge_key][edge_key] = edge

    def remove_nodes(self, node_keys_to_delete: Set[str], target_qnode_key: str, qg: QueryGraph):
        # First delete the specified nodes
        for node_key in node_keys_to_delete:
            del self.nodes_by_qg_id[target_qnode_key][node_key]
        # Then delete any edges orphaned by removal of those nodes
        connected_qedge_keys = {qedge_key for qedge_key, qedge in qg.edges.items() if qedge.subject == target_qnode_key or qedge.object == target_qnode_key}
        fulfilled_connected_qedge_keys = connected_qedge_keys.intersection(set(self.edges_by_qg_id))
        for connected_qedge_key in fulfilled_connected_qedge_keys:
            edges_to_delete = {edge_key for edge_key, edge in self.edges_by_qg_id[connected_qedge_key].items()
                               if {edge.subject, edge.object}.intersection(node_keys_to_delete)}
            for edge_key in edges_to_delete:
                del self.edges_by_qg_id[connected_qedge_key][edge_key]
        # Then delete any nodes orphaned by removal of the orphaned edges (if they shouldn't be orphans)
        non_orphan_qnode_keys_to_check = {qnode_key for qedge_key in fulfilled_connected_qedge_keys
                                          for qnode_key in {qg.edges[qedge_key].subject, qg.edges[qedge_key].object}}.difference({target_qnode_key})
        for non_orphan_qnode_key in non_orphan_qnode_keys_to_check:
            node_keys_fulfilling_qnode = set(self.nodes_by_qg_id[non_orphan_qnode_key])
            connected_qedge_keys = get_connected_qedge_keys(non_orphan_qnode_key, qg)
            node_keys_used_by_edges = {node_key for qedge_key in connected_qedge_keys
                                       for node_key in self.get_node_keys_used_by_edges_fulfilling_qedge(qedge_key)}
            orphan_node_keys = node_keys_fulfilling_qnode.difference(node_keys_used_by_edges)
            for orphan_node_key in orphan_node_keys:
                del self.nodes_by_qg_id[non_orphan_qnode_key][orphan_node_key]

    def get_all_node_keys_used_by_edges(self) -> Set[str]:
        return {node_key for edges in self.edges_by_qg_id.values() for edge in edges.values()
                for node_key in [edge.subject, edge.object]}

    def get_node_keys_used_by_edges_fulfilling_qedge(self, qedge_key: str) -> Set[str]:
        relevant_edges = self.edges_by_qg_id.get(qedge_key, dict())
        return {node_key for edge in relevant_edges.values()
                for node_key in [edge.subject, edge.object]}

    def get_all_node_keys(self) -> Set[str]:
        return {node_key for nodes in self.nodes_by_qg_id.values() for node_key in nodes}

    def is_empty(self) -> bool:
        return True if not self.nodes_by_qg_id.values() else False


def get_curie_prefix(curie: str) -> str:
    if ':' in curie:
        return curie.split(':')[0]
    else:
        return curie


def get_curie_local_id(curie: str) -> str:
    if ':' in curie:
        return curie.split(':')[-1]  # Note: Taking last item gets around "PR:PR:000001" situation
    else:
        return curie


def get_attribute_triple(attribute: Attribute) -> str:
    return f"{attribute.attribute_type_id}--{attribute.value}--{attribute.attribute_source}"


def remove_orphan_edges(kg: QGOrganizedKnowledgeGraph, qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
    fulfilled_qedge_keys = set(kg.edges_by_qg_id)
    for qedge_key in fulfilled_qedge_keys:
        qedge = qg.edges[qedge_key]
        edge_keys = set(kg.edges_by_qg_id[qedge_key])
        for edge_key in edge_keys:
            edge = kg.edges_by_qg_id[qedge_key][edge_key]
            if not ((edge.subject in kg.nodes_by_qg_id[qedge.subject] and edge.object in kg.nodes_by_qg_id[qedge.object]) or
                    (edge.object in kg.nodes_by_qg_id[qedge.subject] and edge.subject in kg.nodes_by_qg_id[qedge.object])):
                del kg.edges_by_qg_id[qedge_key][edge_key]
    return kg


def convert_string_to_pascal_case(input_string: str) -> str:
    # Converts a string like 'chemical_entity' or 'chemicalEntity' to 'ChemicalEntity'
    if not input_string:
        return ""
    elif "_" in input_string:
        words = input_string.split('_')
        return "".join([word.capitalize() for word in words])
    elif len(input_string) > 1:
        return input_string[0].upper() + input_string[1:]
    else:
        return input_string.capitalize()


def convert_string_to_snake_case(input_string: str) -> str:
    # Converts a string like 'ChemicalEntity' or 'chemicalEntity' to 'chemical_entity'
    if len(input_string) > 1:
        snake_string = input_string[0].lower()
        for letter in input_string[1:]:
            if letter.isupper():
                snake_string += "_"
            snake_string += letter.lower()
        return snake_string
    else:
        return input_string.lower()


def convert_to_list(string_or_list: Union[str, List[str], None]) -> List[str]:
    if isinstance(string_or_list, str):
        return [string_or_list]
    elif isinstance(string_or_list, list):
        return string_or_list
    else:
        return []


def get_node_keys_used_by_edges(edges_dict: Dict[str, Edge]) -> Set[str]:
    return {node_key for edge in edges_dict.values() for node_key in [edge.subject, edge.object]}


def get_counts_by_qg_id(dict_kg: QGOrganizedKnowledgeGraph) -> Dict[str, int]:
    counts_by_qg_id = dict()
    for qnode_key, nodes_dict in dict_kg.nodes_by_qg_id.items():
        counts_by_qg_id[qnode_key] = len(nodes_dict)
    for qedge_key, edges_dict in dict_kg.edges_by_qg_id.items():
        counts_by_qg_id[qedge_key] = len(edges_dict)
    return counts_by_qg_id


def get_printable_counts_by_qg_id(dict_kg: QGOrganizedKnowledgeGraph) -> str:
    counts_by_qg_id = get_counts_by_qg_id(dict_kg)
    counts_string = ", ".join([f"{qg_id}: {counts_by_qg_id[qg_id]}" for qg_id in sorted(counts_by_qg_id)])
    return counts_string if counts_string else "no answers"


def get_qg_without_kryptonite_portion(qg: QueryGraph) -> QueryGraph:
    kryptonite_qedge_keys = [qedge_key for qedge_key, qedge in qg.edges.items() if qedge.exclude]
    normal_qedge_keys = set(qg.edges).difference(kryptonite_qedge_keys)
    qnode_keys_used_by_kryptonite_qedges = {qnode_key for qedge_key in kryptonite_qedge_keys for qnode_key in
                                            {qg.edges[qedge_key].subject, qg.edges[qedge_key].object}}
    qnode_keys_used_by_normal_qedges = {qnode_key for qedge_key in normal_qedge_keys for qnode_key in
                                        {qg.edges[qedge_key].subject, qg.edges[qedge_key].object}}
    qnode_keys_used_only_by_kryptonite_qedges = qnode_keys_used_by_kryptonite_qedges.difference(qnode_keys_used_by_normal_qedges)
    normal_qnode_keys = set(qg.nodes).difference(qnode_keys_used_only_by_kryptonite_qedges)
    return QueryGraph(nodes={qnode_key: qnode for qnode_key, qnode in qg.nodes.items() if qnode_key in normal_qnode_keys},
                      edges={qedge_key: qedge for qedge_key, qedge in qg.edges.items() if qedge_key in normal_qedge_keys})


def get_required_portion_of_qg(query_graph: QueryGraph) -> QueryGraph:
    return QueryGraph(nodes={qnode_key: qnode for qnode_key, qnode in query_graph.nodes.items() if not qnode.option_group_id},
                      edges={qedge_key: qedge for qedge_key, qedge in query_graph.edges.items() if not qedge.option_group_id})


def edges_are_parallel(edge_a: Union[QEdge, Edge], edge_b: Union[QEdge, Edge]) -> Union[QEdge, Edge]:
    return {edge_a.subject, edge_a.object} == {edge_b.subject, edge_b.object}


def merge_two_kgs(kg_a: QGOrganizedKnowledgeGraph, kg_b: QGOrganizedKnowledgeGraph) -> QGOrganizedKnowledgeGraph:
    for qnode_key, nodes in kg_a.nodes_by_qg_id.items():
        for node_key, node in nodes.items():
            kg_b.add_node(node_key, node, qnode_key)
    for qedge_key, edges in kg_a.edges_by_qg_id.items():
        for edge_key, edge in edges.items():
            kg_b.add_edge(edge_key, edge, qedge_key)
    return kg_b


def convert_standard_kg_to_qg_organized_kg(standard_kg: KnowledgeGraph) -> QGOrganizedKnowledgeGraph:
    organized_kg = QGOrganizedKnowledgeGraph()
    if standard_kg.nodes:
        for node_key, node in standard_kg.nodes.items():
            for qnode_key in node.qnode_keys:
                if qnode_key not in organized_kg.nodes_by_qg_id:
                    organized_kg.nodes_by_qg_id[qnode_key] = dict()
                organized_kg.nodes_by_qg_id[qnode_key][node_key] = node
    if standard_kg.edges:
        for edge_key, edge in standard_kg.edges.items():
            for qedge_key in edge.qedge_keys:
                if qedge_key not in organized_kg.edges_by_qg_id:
                    organized_kg.edges_by_qg_id[qedge_key] = dict()
                organized_kg.edges_by_qg_id[qedge_key][edge_key] = edge
    return organized_kg


def convert_qg_organized_kg_to_standard_kg(organized_kg: QGOrganizedKnowledgeGraph) -> KnowledgeGraph:
    standard_kg = KnowledgeGraph(nodes=dict(), edges=dict())
    for qnode_key, nodes_for_this_qnode_key in organized_kg.nodes_by_qg_id.items():
        for node_key, node in nodes_for_this_qnode_key.items():
            if node_key in standard_kg.nodes:
                standard_kg.nodes[node_key].qnode_keys.append(qnode_key)
            else:
                node.qnode_keys = [qnode_key]
                standard_kg.nodes[node_key] = node
    for qedge_key, edges_for_this_qedge_key in organized_kg.edges_by_qg_id.items():
        for edge_key, edge in edges_for_this_qedge_key.items():
            if edge_key in standard_kg.edges:
                standard_kg.edges[edge_key].qedge_keys.append(qedge_key)
            else:
                edge.qedge_keys = [qedge_key]
                standard_kg.edges[edge_key] = edge
    return standard_kg


def get_curie_synonyms(curie: Union[str, List[str]], log: Optional[ARAXResponse] = ARAXResponse()) -> List[str]:
    curies = convert_to_list(curie)
    try:
        synonymizer = NodeSynonymizer()
        log.debug(f"Sending NodeSynonymizer.get_equivalent_nodes() a list of {len(curies)} curies")
        equivalent_curies_dict = synonymizer.get_equivalent_nodes(curies)
        log.debug(f"Got response back from NodeSynonymizer")
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        log.error(f"Encountered a problem using NodeSynonymizer: {tb}", error_code=error_type.__name__)
        return []
    else:
        if equivalent_curies_dict is not None:
            curies_missing_info = {curie for curie in equivalent_curies_dict if not equivalent_curies_dict.get(curie)}
            if curies_missing_info:
                log.warning(f"NodeSynonymizer did not find any equivalent curies for: {curies_missing_info}")
            equivalent_curies = {curie for curie_dict in equivalent_curies_dict.values() if curie_dict for curie in
                                 curie_dict}
            all_curies = equivalent_curies.union(set(curies))  # Make sure even curies without synonyms are included
            return sorted(list(all_curies))
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return []


def get_curie_synonyms_dict(curie: Union[str, List[str]], log: Optional[ARAXResponse] = ARAXResponse()) -> Dict[str, List[str]]:
    curies = convert_to_list(curie)
    try:
        synonymizer = NodeSynonymizer()
        log.debug(f"Sending NodeSynonymizer.get_equivalent_nodes() a list of {len(curies)} curies")
        equivalent_curies_dict = synonymizer.get_equivalent_nodes(curies)
        log.debug(f"Got response back from NodeSynonymizer")
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        log.error(f"Encountered a problem using NodeSynonymizer: {tb}", error_code=error_type.__name__)
        return dict()
    else:
        if equivalent_curies_dict is not None:
            curies_missing_info = {curie for curie in equivalent_curies_dict if not equivalent_curies_dict.get(curie)}
            if curies_missing_info:
                log.warning(f"NodeSynonymizer did not find any equivalent curies for: {curies_missing_info}")
            final_curie_dict = dict()
            for input_curie in curies:
                curie_dict = equivalent_curies_dict.get(input_curie)
                final_curie_dict[input_curie] = list(curie_dict) if curie_dict else [input_curie]
            return final_curie_dict
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return dict()


def get_canonical_curies_dict(curie: Union[str, List[str]], log: ARAXResponse) -> Dict[str, Dict[str, str]]:
    curies = convert_to_list(curie)
    try:
        synonymizer = NodeSynonymizer()
        log.debug(f"Sending NodeSynonymizer.get_canonical_curies() a list of {len(curies)} curies")
        canonical_curies_dict = synonymizer.get_canonical_curies(curies)
        log.debug(f"Got response back from NodeSynonymizer")
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        log.error(f"Encountered a problem using NodeSynonymizer: {tb}", error_code=error_type.__name__)
        return {}
    else:
        if canonical_curies_dict is not None:
            unrecognized_curies = {input_curie for input_curie in canonical_curies_dict if not canonical_curies_dict.get(input_curie)}
            if unrecognized_curies:
                log.warning(f"NodeSynonymizer did not recognize: {unrecognized_curies}")
            return canonical_curies_dict
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return {}


def get_canonical_curies_list(curie: Union[str, List[str]], log: ARAXResponse) -> List[str]:
    curies = convert_to_list(curie)
    try:
        synonymizer = NodeSynonymizer()
        log.debug(f"Sending NodeSynonymizer.get_canonical_curies() a list of {len(curies)} curies")
        canonical_curies_dict = synonymizer.get_canonical_curies(curies)
        log.debug(f"Got response back from NodeSynonymizer")
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        log.error(f"Encountered a problem using NodeSynonymizer: {tb}", error_code=error_type.__name__)
        return []
    else:
        if canonical_curies_dict is not None:
            recognized_input_curies = {input_curie for input_curie in canonical_curies_dict if canonical_curies_dict.get(input_curie)}
            unrecognized_curies = set(curies).difference(recognized_input_curies)
            if unrecognized_curies:
                log.warning(f"NodeSynonymizer did not recognize: {unrecognized_curies}")
            canonical_curies = {canonical_curies_dict[recognized_curie].get('preferred_curie') for recognized_curie in recognized_input_curies}
            # Include any original curies we weren't able to find a canonical version for
            canonical_curies.update(unrecognized_curies)
            if not canonical_curies:
                log.error(f"Final list of canonical curies is empty. This shouldn't happen!", error_code="CanonicalCurieIssue")
            return list(canonical_curies)
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return []


def get_preferred_categories(curie: Union[str, List[str]], log: ARAXResponse) -> Optional[List[str]]:
    curies = convert_to_list(curie)
    synonymizer = NodeSynonymizer()
    log.debug(f"Sending NodeSynonymizer.get_canonical_curies() a list of {len(curies)} curies")
    canonical_curies_dict = synonymizer.get_canonical_curies(curies)
    log.debug(f"Got response back from NodeSynonymizer")
    if canonical_curies_dict is not None:
        recognized_input_curies = {input_curie for input_curie in canonical_curies_dict if canonical_curies_dict.get(input_curie)}
        unrecognized_curies = set(curies).difference(recognized_input_curies)
        if unrecognized_curies:
            log.warning(f"NodeSynonymizer did not recognize: {unrecognized_curies}")
        preferred_categories = {canonical_curies_dict[recognized_curie].get('preferred_category')
                                for recognized_curie in recognized_input_curies}
        if preferred_categories:
            return list(preferred_categories)
        else:
            log.warning(f"Unable to find any preferred categories; will default to biolink:NamedThing")
            return ["biolink:NamedThing"]
    else:
        log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
        return []


def get_curie_names(curie: Union[str, List[str]], log: ARAXResponse) -> Dict[str, str]:
    curies = convert_to_list(curie)
    synonymizer = NodeSynonymizer()
    log.debug(f"Looking up names for {len(curies)} input curies using NodeSynonymizer")
    synonymizer_info = synonymizer.get_normalizer_results(curies)
    curie_to_name_map = dict()
    if synonymizer_info:
        recognized_input_curies = {input_curie for input_curie in synonymizer_info if synonymizer_info.get(input_curie)}
        unrecognized_curies = set(curies).difference(recognized_input_curies)
        if unrecognized_curies:
            log.warning(f"NodeSynonymizer did not recognize: {unrecognized_curies}")
        input_curies_without_matching_node = set()
        for input_curie in recognized_input_curies:
            equivalent_nodes = synonymizer_info[input_curie]["nodes"]
            # Find the 'node' in the synonymizer corresponding to this curie
            input_curie_nodes = [node for node in equivalent_nodes if node["identifier"] == input_curie]
            if not input_curie_nodes:
                # Try looking for slight variation (KG2 vs. SRI discrepancy): "KEGG:C02700" vs. "KEGG.COMPOUND:C02700"
                input_curie_stripped = input_curie.replace(".COMPOUND", "")
                input_curie_nodes = [node for node in equivalent_nodes if node["identifier"] == input_curie_stripped]
            # Record the name for this input curie
            if input_curie_nodes:
                curie_to_name_map[input_curie] = input_curie_nodes[0].get("label")
            else:
                input_curies_without_matching_node.add(input_curie)
        if input_curies_without_matching_node:
            log.warning(f"No matching nodes found in NodeSynonymizer for these input curies: "
                        f"{input_curies_without_matching_node}. Cannot determine their specific names.")
    else:
        log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
    return curie_to_name_map


def qg_is_fulfilled(query_graph: QueryGraph, dict_kg: QGOrganizedKnowledgeGraph, enforce_required_only=False) -> bool:
    if enforce_required_only:
        qg_without_kryptonite_portion = get_qg_without_kryptonite_portion(query_graph)
        query_graph = get_required_portion_of_qg(qg_without_kryptonite_portion)
    for qnode_key in query_graph.nodes:
        if not dict_kg.nodes_by_qg_id.get(qnode_key):
            return False
    for qedge_key in query_graph.edges:
        if not dict_kg.edges_by_qg_id.get(qedge_key):
            return False
    return True


def qg_is_disconnected(qg: QueryGraph) -> bool:
    qnode_keys_examined = {next(qnode_key for qnode_key in qg.nodes)}  # Start with any qnode
    qnode_keys_remaining = set(qg.nodes).difference(qnode_keys_examined)
    # Repeatedly look for a qnode connected to at least one of the already examined qnodes
    connected_qnode_key, _ = find_qnode_connected_to_sub_qg(qnode_keys_examined, qnode_keys_remaining, qg)
    while connected_qnode_key and qnode_keys_remaining:
        qnode_keys_remaining.remove(connected_qnode_key)
        qnode_keys_examined.add(connected_qnode_key)
        connected_qnode_key, _ = find_qnode_connected_to_sub_qg(qnode_keys_examined, qnode_keys_remaining, qg)
    # The QG must be disconnected if there are qnodes remaining that are not connected to any of our examined ones
    return True if not connected_qnode_key and qnode_keys_remaining else False


def find_qnode_connected_to_sub_qg(qnode_keys_to_connect_to: Set[str], qnode_keys_to_choose_from: Set[str], qg: QueryGraph) -> Tuple[str, Set[str]]:
    """
    This function selects a qnode ID from the qnode_keys_to_choose_from that connects to one or more of the qnode IDs
    in the qnode_keys_to_connect_to (which itself could be considered a sub-graph of the QG). It also returns the IDs
    of the connection points (all qnode ID(s) in qnode_keys_to_connect_to that the chosen node connects to).
    """
    for qnode_key_option in qnode_keys_to_choose_from:
        all_qedge_keys_using_qnode = get_connected_qedge_keys(qnode_key_option, qg)
        all_connected_qnode_keys = {qnode_key for qedge_key in all_qedge_keys_using_qnode for qnode_key in
                                    {qg.edges[qedge_key].subject, qg.edges[qedge_key].object}}.difference({qnode_key_option})
        subgraph_connections = qnode_keys_to_connect_to.intersection(all_connected_qnode_keys)
        if subgraph_connections:
            return qnode_key_option, subgraph_connections
    return "", set()


def get_connected_qedge_keys(qnode_key: str, qg: QueryGraph) -> Set[str]:
    return {qedge_key for qedge_key, qedge in qg.edges.items() if qnode_key in {qedge.subject, qedge.object}}


def flip_edge(edge: Edge, new_predicate: str) -> Edge:
    edge.predicate = new_predicate
    original_subject = edge.subject
    edge.subject = edge.object
    edge.object = original_subject
    return edge


def flip_qedge(qedge: QEdge, new_predicates: List[str]):
    qedge.predicates = new_predicates
    original_subject = qedge.subject
    qedge.subject = qedge.object
    qedge.object = original_subject


def check_for_canonical_predicates(kg: QGOrganizedKnowledgeGraph, kp_name: str, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
    non_canonical_predicates_used = set()
    biolink_helper = BiolinkHelper()
    for qedge_id, edges in kg.edges_by_qg_id.items():
        for edge in edges.values():
            canonical_predicate = biolink_helper.get_canonical_predicates(edge.predicate)[0]
            if canonical_predicate != edge.predicate:
                non_canonical_predicates_used.add(edge.predicate)
                _ = flip_edge(edge, canonical_predicate)
    if non_canonical_predicates_used:
        log.warning(f"{kp_name}: Found edges in {kp_name}'s answer that use non-canonical "
                    f"predicates: {non_canonical_predicates_used}. I corrected these.")
    return kg


def get_arax_source_attribute() -> Attribute:
    arax_infores_curie = "infores:arax"
    return Attribute(attribute_type_id="biolink:aggregator_knowledge_source",
                     value=arax_infores_curie,
                     value_type_id="biolink:InformationResource",
                     attribute_source=arax_infores_curie)


def get_kp_source_attribute(kp_name: str, arax_kp: bool = False, description: Optional[str] = None) -> Attribute:
    if not arax_kp and not description:
        description = f"ARAX inserted this attribute because the KP ({kp_name}) did not seem to provide such " \
                      f"an attribute (indicating that this edge came from them)."
    return Attribute(attribute_type_id="biolink:knowledge_source",
                     value=kp_name,
                     value_type_id="biolink:InformationResource",
                     description=description,
                     attribute_source="infores:arax")


def get_computed_value_attribute() -> Attribute:
    arax_infores_curie = "infores:arax"
    return Attribute(attribute_type_id="biolink:computed_value",
                     value=True,
                     value_type_id="metatype:Boolean",
                     attribute_source=arax_infores_curie,
                     description="This edge is a container for a computed value between two nodes that is not "
                                 "directly attachable to other edges.")


def get_kp_endpoint_url(kp_name: str) -> Union[str, None]:
    endpoint_map = {
        "infores:biothings-explorer": "https://api.bte.ncats.io/v1",  # TODO: Enter 1.2 endpoint once available..
        "infores:genetics-data-provider": "https://translator.broadinstitute.org/genetics_provider/trapi/v1.2",
        "infores:molepro": "https://translator.broadinstitute.org/molepro/trapi/v1.2",
        "infores:rtx-kg2": RTXConfig.rtx_kg2_url,
        "infores:biothings-multiomics-clinical-risk": "https://api.bte.ncats.io/v1/smartapi/d86a24f6027ffe778f84ba10a7a1861a",
        "infores:biothings-multiomics-wellness": "https://api.bte.ncats.io/v1/smartapi/02af7d098ab304e80d6f4806c3527027",
        "infores:spoke": "https://spokekp.healthdatascience.cloud/api/v1.2/",
        "infores:biothings-multiomics-biggim-drug-response": "https://api.bte.ncats.io/v1/smartapi/adf20dd6ff23dfe18e8e012bde686e31",
        "infores:biothings-tcga-mut-freq": "https://api.bte.ncats.io/v1/smartapi/5219cefb9d2b8d5df08c3a956fdd20f3",
        "infores:connections-hypothesis": "http://chp.thayer.dartmouth.edu",  # This always points to their latest TRAPI endpoint (CHP suggested using it over their '/v1.2' URL, which has some issues)
        "infores:cohd": "https://cohd.io/api",
        "infores:icees-dili": "https://icees-dili.renci.org",
        "infores:icees-asthma": "https://icees-asthma.renci.org"
    }
    return endpoint_map.get(kp_name)


def sort_kps_for_asyncio(kp_names: Union[List[str], Set[str]],  log: ARAXResponse) -> List[str]:
    # Order KPs such that those with longer requests will tend to be kicked off earlier
    kp_names = set(kp_names)
    asyncio_start_order = ["infores:connections-hypothesis", "infores:biothings-explorer", "infores:biothings-multiomics-biggim-drug-response", "infores:biothings-multiomics-clinical-risk", "infores:biothings-multiomics-wellness", "infores:spoke", "infores:biothings-tcga-mut-freq",
                           "infores:icees-dili", "infores:icees-asthma", "infores:cohd", "infores:molepro", "infores:rtx-kg2", "infores:genetics-data-provider", "infores:arax-normalized-google-distance", "infores:arax-drug-treats-disease"]
    unordered_kps = kp_names.difference(set(asyncio_start_order))
    if unordered_kps:
        log.warning(f"Selected KP(s) don't have asyncio start ordering specified: {unordered_kps}")
        asyncio_start_order = list(unordered_kps) + asyncio_start_order
    ordered_kps = [kp for kp in asyncio_start_order if kp in kp_names]
    return ordered_kps


def make_qg_use_old_snake_case_types(qg: QueryGraph) -> QueryGraph:
    # This is a temporary patch needed for KPs not yet TRAPI 1.0 compliant
    qg_copy = copy.deepcopy(qg)
    for qnode in qg_copy.nodes.values():
        if qnode.categories:
            prefixless_categories = [category.split(":")[-1] for category in qnode.categories]
            qnode.categories = [convert_string_to_snake_case(category) for category in prefixless_categories]
    for qedge in qg_copy.edges.values():
        if qedge.predicates:
            qedge.predicates = [predicate.split(":")[-1] for predicate in qedge.predicates]
    return qg_copy


def remove_edges_with_qedge_key(kg: KnowledgeGraph, qedge_key: str):
    edge_keys = set(kg.edges)
    for edge_key in edge_keys:
        edge = kg.edges[edge_key]
        if qedge_key in edge.qedge_keys:
            del kg.edges[edge_key]


def create_results(qg: QueryGraph, kg: QGOrganizedKnowledgeGraph, log: ARAXResponse, overlay_fet: bool = False,
                   rank_results: bool = False, qnode_key_to_prune: Optional[str] = None,) -> Response:
    regular_format_kg = convert_qg_organized_kg_to_standard_kg(kg)
    resultifier = ARAXResultify()
    prune_response = ARAXResponse()
    prune_response.envelope = Response()
    prune_response.envelope.message = Message()
    prune_message = prune_response.envelope.message
    prune_message.query_graph = qg
    prune_message.knowledge_graph = regular_format_kg
    if overlay_fet:
        log.debug(f"Using FET to assess quality of intermediate answers in Expand")
        connected_qedges = [qedge for qedge in qg.edges.values()
                            if qedge.subject == qnode_key_to_prune or qedge.object == qnode_key_to_prune]
        qnode_pairs_to_overlay = {(qedge.subject if qedge.subject != qnode_key_to_prune else qedge.object, qnode_key_to_prune)
                                  for qedge in connected_qedges}
        for qnode_pair in qnode_pairs_to_overlay:
            pair_string_id = f"{qnode_pair[0]}-->{qnode_pair[1]}"
            log.debug(f"Overlaying FET for {pair_string_id} (from Expand)")
            fet_qedge_key = f"FET{pair_string_id}"
            try:
                overlayer = ARAXOverlay()
                params = {"action": "fisher_exact_test",
                          "subject_qnode_key": qnode_pair[0],
                          "object_qnode_key": qnode_pair[1],
                          "virtual_relation_label": fet_qedge_key}
                overlayer.apply(prune_response, params)
            except Exception as error:
                exception_type, exception_value, exception_traceback = sys.exc_info()
                log.warning(f"An uncaught error occurred when overlaying with FET during Expand's pruning: {error}: "
                            f"{repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}")
            if prune_response.status != "OK":
                log.warning(f"FET produced an error when Expand tried to use it to prune the KG. "
                            f"Log was: {prune_response.show()}")
                log.debug(f"Will continue pruning without overlaying FET")
                # Get rid of any FET edges that might be in the KG/QG, since this step failed
                remove_edges_with_qedge_key(prune_response.envelope.message.knowledge_graph, fet_qedge_key)
                qg.edges.pop(fet_qedge_key, None)
                prune_response.status = "OK"  # Clear this so we can continue without overlaying
            else:
                if fet_qedge_key in qg.edges:
                    qg.edges[fet_qedge_key].option_group_id = f"FET_VIRTUAL_GROUP_{pair_string_id}"
                else:
                    log.warning(f"Attempted to overlay FET from Expand, but it didn't work. Pruning without it.")

    # Create results and rank them as appropriate
    log.debug(f"Calling Resultify from Expand for pruning")
    resultifier.apply(prune_response, {})
    if rank_results:
        try:
            log.debug(f"Ranking Expand's intermediate pruning results")
            ranker = ARAXRanker()
            ranker.aggregate_scores_dmk(prune_response)
        except Exception as error:
            exception_type, exception_value, exception_traceback = sys.exc_info()
            log.error(f"An uncaught error occurred when attempting to rank results during Expand's pruning: "
                      f"{error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}."
                      f"Log was: {prune_response.show()}",
                      error_code="UncaughtARAXiError")
            # Give any unranked results a score of 0
            for result in prune_response.envelope.message.results:
                if result.score is None:
                    result.score = 0
    return prune_response


def get_qg_expanded_thus_far(qg: QueryGraph, kg: QGOrganizedKnowledgeGraph) -> QueryGraph:
    expanded_qnodes = {qnode_key for qnode_key in qg.nodes if kg.nodes_by_qg_id.get(qnode_key)}
    expanded_qedges = {qedge_key for qedge_key in qg.edges if kg.edges_by_qg_id.get(qedge_key)}
    qg_expanded_thus_far = QueryGraph(nodes={qnode_key: copy.deepcopy(qg.nodes[qnode_key]) for qnode_key in expanded_qnodes},
                                      edges={qedge_key: copy.deepcopy(qg.edges[qedge_key]) for qedge_key in expanded_qedges})
    return qg_expanded_thus_far


def get_trapi_version():
    code_dir = f"{os.path.dirname(os.path.abspath(__file__))}/../../.."
    openapi_yaml_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
    with open(openapi_yaml_path) as api_file:
        openapi_yaml = yaml.safe_load(api_file)
        trapi_version = openapi_yaml["info"]["x-trapi"]["version"]
        return trapi_version


def get_all_kps() -> Set[str]:
    version = get_trapi_version()
    # remove patch number because version is used for string matching to evaluate compatbility
    minor_version = ".".join( version.split(".")[:2] )
    smartapi = SmartAPI()
    kp_info = smartapi.get_kps(version=minor_version,req_maturity="production")
    kp_urls = {kp["infores_name"] : kp["servers"][0]["url"] for kp in kp_info}
    kp_urls |= {"infores:arax-drug-treats-disease":None, "infores:arax-normalized-google-distance":None}
    return kp_urls


def merge_two_dicts(dict_a: dict, dict_b: dict) -> dict:
    new_dict = copy.deepcopy(dict_a)
    new_dict.update(dict_b)
    return new_dict
