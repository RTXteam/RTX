#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import sys
import os
from typing import List, Dict, Tuple, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/kg-construction/")
from KGNodeIndex import KGNodeIndex


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


def add_node_to_kg(dict_kg, node: Node, qnode_id: str):
    if qnode_id not in dict_kg['nodes']:
        dict_kg['nodes'][qnode_id] = dict()
    dict_kg['nodes'][qnode_id][node.id] = node


def add_edge_to_kg(dict_kg, edge: Edge, qedge_id: str):
    if qedge_id not in dict_kg['edges']:
        dict_kg['edges'][qedge_id] = dict()
    dict_kg['edges'][qedge_id][edge.id] = edge


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


def get_counts_by_qg_id(dict_kg):
    counts_by_qg_id = dict()
    for qnode_id, nodes_dict in dict_kg['nodes'].items():
        counts_by_qg_id[qnode_id] = len(nodes_dict)
    for qedge_id, edges_dict in dict_kg['edges'].items():
        counts_by_qg_id[qedge_id] = len(edges_dict)
    return counts_by_qg_id


def get_query_node(query_graph: QueryGraph, qnode_id: str) -> QNode:
    matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
    return matching_nodes[0] if matching_nodes else None


def get_preferred_curie(curie: str) -> str:
    # Curie prefixes in order of preference for different node types (not all-inclusive)
    prefixes_in_order_of_preference = ['DOID', 'CHEMBL.COMPOUND', 'UNIPROTKB', 'NCBIGENE', 'CHEBI', 'HP', 'MONDO',
                                       'OMIM', 'ENSEMBL', 'HGNC', 'GO', 'REACT', 'REACTOME', 'FMA', 'CL', 'MESH']
    synonym_group = sorted(get_curie_synonyms(curie))

    # Pick the curie that uses the (relatively) most preferred prefix
    lowest_ranking = 10000
    best_curie = None
    for curie in synonym_group:
        uppercase_prefix = get_curie_prefix(curie).upper()
        if uppercase_prefix in prefixes_in_order_of_preference:
            ranking = prefixes_in_order_of_preference.index(uppercase_prefix)
            if ranking < lowest_ranking:
                lowest_ranking = ranking
                best_curie = curie

    if not best_curie:
        best_curie = synonym_group[0] if synonym_group else curie
    return best_curie


def convert_standard_kg_to_dict_kg(knowledge_graph: KnowledgeGraph):
    dict_kg = {'nodes': dict(), 'edges': dict()}
    if knowledge_graph.nodes:
        for node in knowledge_graph.nodes:
            for qnode_id in node.qnode_ids:
                if qnode_id not in dict_kg['nodes']:
                    dict_kg['nodes'][qnode_id] = dict()
                dict_kg['nodes'][qnode_id][node.id] = node
    if knowledge_graph.edges:
        for edge in knowledge_graph.edges:
            for qedge_id in edge.qedge_ids:
                if qedge_id not in dict_kg['edges']:
                    dict_kg['edges'][qedge_id] = dict()
                dict_kg['edges'][qedge_id][edge.id] = edge
    return dict_kg


def convert_dict_kg_to_standard_kg(dict_kg) -> KnowledgeGraph:
    almost_standard_kg = KnowledgeGraph(nodes=dict(), edges=dict())
    for qnode_id, nodes_for_this_qnode_id in dict_kg.get('nodes').items():
        for node_key, node in nodes_for_this_qnode_id.items():
            if node_key in almost_standard_kg.nodes:
                almost_standard_kg.nodes[node_key].qnode_ids.append(qnode_id)
            else:
                node.qnode_ids = [qnode_id]
                almost_standard_kg.nodes[node_key] = node
    for qedge_id, edges_for_this_qedge_id in dict_kg.get('edges').items():
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
    if prefix == "UMLS":
        prefix = "CUI"
    elif prefix == "Reactome":
        prefix = "REACT"
    elif prefix == "UNIPROTKB":
        prefix = "UniProtKB"
    return prefix + ':' + local_id


def convert_curie_to_bte_format(curie: str) -> str:
    prefix = get_curie_prefix(curie)
    local_id = get_curie_local_id(curie)
    if prefix == "CUI":
        prefix = "UMLS"
    elif prefix == "REACT":
        prefix = "Reactome"
    elif prefix == "UniProtKB":
        prefix = prefix.upper()
    return prefix + ':' + local_id


def get_curie_synonyms(curie: str, arax_kg='KG2') -> List[str]:
    curies = convert_string_or_list_to_list(curie)

    # Find whatever we can using KG2/KG1
    kgni = KGNodeIndex()
    equivalent_curies_using_arax_kg = set()
    for curie in curies:
        equivalent_curies = kgni.get_equivalent_curies(curie=convert_curie_to_arax_format(curie), kg_name=arax_kg)
        equivalent_curies_using_arax_kg = equivalent_curies_using_arax_kg.union(set(equivalent_curies))

    # TODO: Use SRI team's node normalizer to find more synonyms

    return list(equivalent_curies_using_arax_kg)


def qg_is_fulfilled(query_graph: QueryGraph, dict_kg) -> bool:
    qnode_ids = [qnode.id for qnode in query_graph.nodes]
    qedge_ids = [qedge.id for qedge in query_graph.edges]

    for qnode_id in qnode_ids:
        if qnode_id not in dict_kg['nodes'] or not dict_kg['nodes'][qnode_id]:
            return False
    for qedge_id in qedge_ids:
        if qedge_id not in dict_kg['edges'] or not dict_kg['edges'][qedge_id]:
            return False
    return True


def switch_kg_to_arax_curie_format(dict_kg):
    converted_kg = {'nodes': {qnode_id: dict() for qnode_id in dict_kg['nodes']},
                    'edges': {qedge_id: dict() for qedge_id in dict_kg['edges']}}
    for qnode_id, nodes in dict_kg['nodes'].items():
        for node_id, node in nodes.items():
            node.id = convert_curie_to_arax_format(node.id)
            add_node_to_kg(converted_kg, node, qnode_id)
    for qedge_id, edges in dict_kg['edges'].items():
        for edge_id, edge in edges.items():
            edge.source_id = convert_curie_to_arax_format(edge.source_id)
            edge.target_id = convert_curie_to_arax_format(edge.target_id)
            add_edge_to_kg(converted_kg, edge, qedge_id)
    return converted_kg
