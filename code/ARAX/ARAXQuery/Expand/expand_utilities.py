#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import sys
import os
import traceback
from typing import List, Dict, Union, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class DictKnowledgeGraph:
    def __init__(self, nodes: Dict[str, Dict[str, Node]] = None, edges: Dict[str, Dict[str, Edge]] = None):
        self.nodes_by_qg_id = nodes if nodes else dict()
        self.edges_by_qg_id = edges if edges else dict()

    def add_node(self, node: Node, qnode_id: str):
        if qnode_id not in self.nodes_by_qg_id:
            self.nodes_by_qg_id[qnode_id] = dict()
        self.nodes_by_qg_id[qnode_id][node.id] = node

    def add_edge(self, edge: Edge, qedge_id: str):
        if qedge_id not in self.edges_by_qg_id:
            self.edges_by_qg_id[qedge_id] = dict()
        self.edges_by_qg_id[qedge_id][edge.id] = edge


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


def copy_qedge(old_qedge: QEdge) -> QEdge:
    new_qedge = QEdge()
    for edge_property in new_qedge.to_dict():
        value = getattr(old_qedge, edge_property)
        setattr(new_qedge, edge_property, value)
    return new_qedge


def copy_qnode(old_qnode: QNode) -> QNode:
    new_qnode = QNode()
    for node_property in new_qnode.to_dict():
        value = getattr(old_qnode, node_property)
        setattr(new_qnode, node_property, value)
    return new_qnode


def convert_string_to_pascal_case(input_string: str) -> str:
    # Converts a string like 'chemical_substance' or 'chemicalSubstance' to 'ChemicalSubstance'
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
    # Converts a string like 'ChemicalSubstance' or 'chemicalSubstance' to 'chemical_substance'
    if len(input_string) > 1:
        snake_string = input_string[0].lower()
        for letter in input_string[1:]:
            if letter.isupper():
                snake_string += "_"
            snake_string += letter.lower()
        return snake_string
    else:
        return input_string.lower()


def convert_string_or_list_to_list(string_or_list: Union[str, List[str]]) -> List[str]:
    if isinstance(string_or_list, str):
        return [string_or_list]
    elif isinstance(string_or_list, list):
        return string_or_list
    else:
        return []


def get_counts_by_qg_id(dict_kg: DictKnowledgeGraph) -> Dict[str, int]:
    counts_by_qg_id = dict()
    for qnode_id, nodes_dict in dict_kg.nodes_by_qg_id.items():
        counts_by_qg_id[qnode_id] = len(nodes_dict)
    for qedge_id, edges_dict in dict_kg.edges_by_qg_id.items():
        counts_by_qg_id[qedge_id] = len(edges_dict)
    return counts_by_qg_id


def get_printable_counts_by_qg_id(dict_kg: DictKnowledgeGraph) -> str:
    counts_by_qg_id = get_counts_by_qg_id(dict_kg)
    return ", ".join([f"{qg_id}: {counts_by_qg_id[qg_id]}" for qg_id in sorted(counts_by_qg_id)])


def get_query_node(query_graph: QueryGraph, qnode_id: str) -> QNode:
    matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
    return matching_nodes[0] if matching_nodes else None


def convert_standard_kg_to_dict_kg(knowledge_graph: KnowledgeGraph) -> DictKnowledgeGraph:
    dict_kg = DictKnowledgeGraph()
    if knowledge_graph.nodes:
        for node in knowledge_graph.nodes:
            for qnode_id in node.qnode_ids:
                if qnode_id not in dict_kg.nodes_by_qg_id:
                    dict_kg.nodes_by_qg_id[qnode_id] = dict()
                dict_kg.nodes_by_qg_id[qnode_id][node.id] = node
    if knowledge_graph.edges:
        for edge in knowledge_graph.edges:
            for qedge_id in edge.qedge_ids:
                if qedge_id not in dict_kg.edges_by_qg_id:
                    dict_kg.edges_by_qg_id[qedge_id] = dict()
                dict_kg.edges_by_qg_id[qedge_id][edge.id] = edge
    return dict_kg


def convert_dict_kg_to_standard_kg(dict_kg: DictKnowledgeGraph) -> KnowledgeGraph:
    almost_standard_kg = KnowledgeGraph(nodes=dict(), edges=dict())
    for qnode_id, nodes_for_this_qnode_id in dict_kg.nodes_by_qg_id.items():
        for node_key, node in nodes_for_this_qnode_id.items():
            if node_key in almost_standard_kg.nodes:
                almost_standard_kg.nodes[node_key].qnode_ids.append(qnode_id)
            else:
                node.qnode_ids = [qnode_id]
                almost_standard_kg.nodes[node_key] = node
    for qedge_id, edges_for_this_qedge_id in dict_kg.edges_by_qg_id.items():
        for edge_key, edge in edges_for_this_qedge_id.items():
            if edge_key in almost_standard_kg.edges:
                almost_standard_kg.edges[edge_key].qedge_ids.append(qedge_id)
            else:
                edge.qedge_ids = [qedge_id]
                almost_standard_kg.edges[edge_key] = edge
    standard_kg = KnowledgeGraph(nodes=list(almost_standard_kg.nodes.values()), edges=list(almost_standard_kg.edges.values()))
    return standard_kg


def convert_curie_to_arax_format(curie: str) -> str:
    prefix = get_curie_prefix(curie)
    local_id = get_curie_local_id(curie)
    if prefix == "Reactome":
        prefix = "REACT"
    elif prefix == "UNIPROTKB":
        prefix = "UniProtKB"
    return prefix + ':' + local_id


def convert_curie_to_bte_format(curie: str) -> str:
    prefix = get_curie_prefix(curie)
    local_id = get_curie_local_id(curie)
    if prefix == "REACT":
        prefix = "Reactome"
    elif prefix == "UniProtKB":
        prefix = prefix.upper()
    return prefix + ':' + local_id


def get_curie_synonyms(curie: Union[str, List[str]], log: ARAXResponse) -> List[str]:
    curies = convert_string_or_list_to_list(curie)
    try:
        synonymizer = NodeSynonymizer()
        log.debug(f"Sending NodeSynonymizer.get_equivalent_nodes() a list of {len(curies)} curies")
        equivalent_curies_dict = synonymizer.get_equivalent_nodes(curies, kg_name="KG2")
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


def get_canonical_curies_dict(curie: Union[str, List[str]], log: ARAXResponse) -> Dict[str, Dict[str, str]]:
    curies = convert_string_or_list_to_list(curie)
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
                log.warning(f"NodeSynonymizer did not return canonical info for: {unrecognized_curies}")
            return canonical_curies_dict
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return {}


def get_canonical_curies_list(curie: Union[str, List[str]], log: ARAXResponse) -> List[str]:
    curies = convert_string_or_list_to_list(curie)
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
                log.warning(f"NodeSynonymizer did not return canonical info for: {unrecognized_curies}")
            canonical_curies = {canonical_curies_dict[recognized_curie].get('preferred_curie') for recognized_curie in recognized_input_curies}
            return list(canonical_curies)
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return []


def qg_is_fulfilled(query_graph: QueryGraph, dict_kg: DictKnowledgeGraph) -> bool:
    qnode_ids = [qnode.id for qnode in query_graph.nodes]
    qedge_ids = [qedge.id for qedge in query_graph.edges]

    for qnode_id in qnode_ids:
        if qnode_id not in dict_kg.nodes_by_qg_id or not dict_kg.nodes_by_qg_id[qnode_id]:
            return False
    for qedge_id in qedge_ids:
        if qedge_id not in dict_kg.edges_by_qg_id or not dict_kg.edges_by_qg_id[qedge_id]:
            return False
    return True


def switch_kg_to_arax_curie_format(dict_kg: DictKnowledgeGraph) -> DictKnowledgeGraph:
    converted_kg = DictKnowledgeGraph(nodes={qnode_id: dict() for qnode_id in dict_kg.nodes_by_qg_id},
                                      edges={qedge_id: dict() for qedge_id in dict_kg.edges_by_qg_id})
    for qnode_id, nodes in dict_kg.nodes_by_qg_id.items():
        for node_id, node in nodes.items():
            node.id = convert_curie_to_arax_format(node.id)
            converted_kg.add_node(node, qnode_id)
    for qedge_id, edges in dict_kg.edges_by_qg_id.items():
        for edge_id, edge in edges.items():
            edge.source_id = convert_curie_to_arax_format(edge.source_id)
            edge.target_id = convert_curie_to_arax_format(edge.target_id)
            converted_kg.add_edge(edge, qedge_id)
    return converted_kg
