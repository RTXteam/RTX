#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from KGNodeIndex import KGNodeIndex


def get_curie_prefix(curie):
    if ':' in curie:
        return curie.split(':')[0]
    else:
        return curie


def get_curie_local_id(curie):
    if ':' in curie:
        return curie.split(':')[-1]  # Note: Taking last item gets around "PR:PR:000001" situation
    else:
        return curie


def add_node_to_kg(kg, swagger_node, qnode_id):
    if qnode_id not in kg['nodes']:
        kg['nodes'][qnode_id] = dict()
    kg['nodes'][qnode_id][swagger_node.id] = swagger_node


def add_edge_to_kg(kg, swagger_edge, qedge_id):
    if qedge_id not in kg['edges']:
        kg['edges'][qedge_id] = dict()
    kg['edges'][qedge_id][swagger_edge.id] = swagger_edge


def copy_qedge(old_qedge):
    new_qedge = QEdge()
    for edge_property in new_qedge.to_dict():
        value = getattr(old_qedge, edge_property)
        setattr(new_qedge, edge_property, value)
    return new_qedge


def copy_qnode(old_qnode):
    new_qnode = QNode()
    for node_property in new_qnode.to_dict():
        value = getattr(old_qnode, node_property)
        setattr(new_qnode, node_property, value)
    return new_qnode


def convert_string_to_pascal_case(input_string):
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


def convert_string_to_snake_case(input_string):
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


def convert_string_or_list_to_list(string_or_list):
    if type(string_or_list) is str:
        return [string_or_list]
    elif type(string_or_list) is list:
        return string_or_list
    else:
        return []


def get_counts_by_qg_id(knowledge_graph):
    counts_by_qg_id = dict()
    for qnode_id, nodes_dict in knowledge_graph['nodes'].items():
        counts_by_qg_id[qnode_id] = len(nodes_dict)
    for qedge_id, edges_dict in knowledge_graph['edges'].items():
        counts_by_qg_id[qedge_id] = len(edges_dict)
    return counts_by_qg_id


def get_query_node(query_graph, qnode_id):
    matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
    return matching_nodes[0] if matching_nodes else None


def get_preferred_prefixes_for_node_type(node_type):
    # Curie prefixes in order of preference for different node types
    preferred_node_prefixes_dict = {'chemical_substance': ['CHEMBL.COMPOUND', 'CHEBI'],
                                    'protein': ['UNIPROTKB', 'PR'],
                                    'gene': ['NCBIGENE', 'ENSEMBL', 'HGNC', 'GO'],
                                    'disease': ['DOID', 'MONDO', 'OMIM', 'MESH'],
                                    'phenotypic_feature': ['HP', 'OMIM'],
                                    'anatomical_entity': ['UBERON', 'FMA', 'CL'],
                                    'pathway': ['REACT', 'REACTOME'],
                                    'biological_process': ['GO'],
                                    'cellular_component': ['GO']}
    return preferred_node_prefixes_dict.get(convert_string_to_snake_case(node_type), [])


def get_best_equivalent_curie(equivalent_curies, node_type):
    prefixes_in_order_of_preference = get_preferred_prefixes_for_node_type(node_type)
    lowest_index = 10000
    best_curie = equivalent_curies[0]
    for curie in equivalent_curies:
        uppercase_prefix = get_curie_prefix(curie).upper()
        if uppercase_prefix in prefixes_in_order_of_preference:
            if prefixes_in_order_of_preference.index(uppercase_prefix) < lowest_index:
                best_curie = curie
    return best_curie


def convert_standard_kg_to_dict_kg(knowledge_graph):
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


def convert_dict_kg_to_standard_kg(dict_kg):
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


def get_curie_synonyms(curie, kg='KG2'):
    curies = convert_string_or_list_to_list(curie)

    # Find whatever we can using KG2/KG1
    kgni = KGNodeIndex()
    equivalent_curies_using_arax_kg = set()
    for curie in curies:
        equivalent_curies = kgni.get_equivalent_curies(curie=curie, kg_name=kg)
        equivalent_curies_using_arax_kg = equivalent_curies_using_arax_kg.union(set(equivalent_curies))

    # TODO: Use SRI team's node normalizer to find more synonyms

    return list(equivalent_curies_using_arax_kg)
