#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/kg-construction/")
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


def add_node_to_kg(dict_kg, node, qnode_id):
    if qnode_id not in dict_kg['nodes']:
        dict_kg['nodes'][qnode_id] = dict()
    dict_kg['nodes'][qnode_id][node.id] = node


def add_edge_to_kg(dict_kg, edge, qedge_id):
    if qedge_id not in dict_kg['edges']:
        dict_kg['edges'][qedge_id] = dict()
    dict_kg['edges'][qedge_id][edge.id] = edge


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


def get_counts_by_qg_id(dict_kg):
    counts_by_qg_id = dict()
    for qnode_id, nodes_dict in dict_kg['nodes'].items():
        counts_by_qg_id[qnode_id] = len(nodes_dict)
    for qedge_id, edges_dict in dict_kg['edges'].items():
        counts_by_qg_id[qedge_id] = len(edges_dict)
    return counts_by_qg_id


def get_query_node(query_graph, qnode_id):
    matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
    return matching_nodes[0] if matching_nodes else None


def get_best_equivalent_curie(equivalent_curies, node_type):
    # Curie prefixes in order of preference for different node types (not all-inclusive)
    preferred_node_prefixes_dict = {'chemical_substance': ['CHEMBL.COMPOUND', 'CHEBI'],
                                    'protein': ['UNIPROTKB', 'PR'],
                                    'gene': ['NCBIGENE', 'ENSEMBL', 'HGNC', 'GO'],
                                    'disease': ['DOID', 'MONDO', 'OMIM', 'MESH'],
                                    'phenotypic_feature': ['HP', 'OMIM'],
                                    'anatomical_entity': ['UBERON', 'FMA', 'CL'],
                                    'pathway': ['REACT', 'REACTOME'],
                                    'biological_process': ['GO'],
                                    'cellular_component': ['GO']}
    prefixes_in_order_of_preference = preferred_node_prefixes_dict.get(convert_string_to_snake_case(node_type), [])

    # Pick the curie that uses the (relatively) most preferred prefix
    lowest_ranking = 10000
    best_curie = None
    for curie in equivalent_curies:
        uppercase_prefix = get_curie_prefix(curie).upper()
        if uppercase_prefix in prefixes_in_order_of_preference:
            ranking = prefixes_in_order_of_preference.index(uppercase_prefix)
            if ranking < lowest_ranking:
                lowest_ranking = ranking
                best_curie = curie
    # Otherwise, just try to pick one that isn't 'NAME:___'
    if not best_curie:
        non_name_curies = [curie for curie in equivalent_curies if get_curie_prefix(curie).upper() != 'NAME']
        best_curie = non_name_curies[0] if non_name_curies else equivalent_curies[0]
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


def convert_curie_to_arax_format(curie):
    prefix = get_curie_prefix(curie)
    local_id = get_curie_local_id(curie)
    if prefix == "UMLS":
        prefix = "CUI"
    elif prefix == "Reactome":
        prefix = "REACT"
    elif prefix == "UNIPROTKB":
        prefix = "UniProtKB"
    return prefix + ':' + local_id


def convert_curie_to_bte_format(curie):
    prefix = get_curie_prefix(curie)
    local_id = get_curie_local_id(curie)
    if prefix == "CUI":
        prefix = "UMLS"
    elif prefix == "REACT":
        prefix = "Reactome"
    elif prefix == "UniProtKB":
        prefix = prefix.upper()
    return prefix + ':' + local_id


def get_curie_synonyms(curie, arax_kg='KG2'):
    curies = convert_string_or_list_to_list(curie)

    # Find whatever we can using KG2/KG1
    kgni = KGNodeIndex()
    equivalent_curies_using_arax_kg = set()
    for curie in curies:
        equivalent_curies = kgni.get_equivalent_curies(curie=convert_curie_to_arax_format(curie), kg_name=arax_kg)
        equivalent_curies_using_arax_kg = equivalent_curies_using_arax_kg.union(set(equivalent_curies))

    # TODO: Use SRI team's node normalizer to find more synonyms

    return list(equivalent_curies_using_arax_kg)


def add_curie_synonyms_to_query_nodes(qnodes, log, arax_kg='KG2', override_node_type=True, format_for_bte=False, qnodes_using_curies_from_prior_step=None):
    log.debug("Looking for query nodes to use curie synonyms for")
    if not qnodes_using_curies_from_prior_step:
        qnodes_using_curies_from_prior_step = set()
    curie_map = dict()

    for qnode in qnodes:
        if qnode.curie and (qnode.id not in qnodes_using_curies_from_prior_step):
            curie_map[qnode.id] = dict()
            input_curies = convert_string_or_list_to_list(qnode.curie)
            final_curie_list = []
            for curie in input_curies:
                original_curie = curie
                equivalent_curies = get_curie_synonyms(curie=original_curie, arax_kg=arax_kg)
                if format_for_bte:
                    equivalent_curies = [convert_curie_to_bte_format(curie) for curie in equivalent_curies]
                if len(equivalent_curies) > 1:
                    log.debug(f"Found synonyms for curie {original_curie}: {equivalent_curies}")
                    final_curie_list += equivalent_curies
                    curie_map[qnode.id][original_curie] = equivalent_curies
                    if override_node_type:
                        qnode.type = None  # Equivalent curie types may be different than the original, so we clear this
                elif len(equivalent_curies) <= 1:
                    log.debug(f"Could not find any synonyms for curie {original_curie}")
                    final_curie_list.append(original_curie)
                    curie_map[qnode.id][original_curie] = [original_curie]

            # Use our new synonyms list only if we actually found any synonyms
            if set(final_curie_list) != set(input_curies):
                qnode.curie = final_curie_list

    # Don't consider curie a synonym for another if it was also an entered curie (maybe a bug in kgnodeindex method?)
    for qnode_id, curie_mappings in curie_map.items():
        for original_curie, curies_to_use in curie_mappings.items():
            curies_to_remove = [curie for curie in curies_to_use if curie in curie_mappings.keys() and curie != original_curie]
            for curie in curies_to_remove:
                curie_mappings[original_curie].remove(curie)

    return curie_map


def qg_is_fulfilled(query_graph, dict_kg):
    qnode_ids = [qnode.id for qnode in query_graph.nodes]
    qedge_ids = [qedge.id for qedge in query_graph.edges]

    for qnode_id in qnode_ids:
        if qnode_id not in dict_kg['nodes'] or not len(dict_kg['nodes'][qnode_id]):
            return False
    for qedge_id in qedge_ids:
        if qedge_id not in dict_kg['edges'] or not len(dict_kg['edges'][qedge_id]):
            return False
    return True


def edge_using_node_exists(curie, qnode_id, edge_to_nodes_map):
    for edge_id, node_usages in edge_to_nodes_map.items():
        if node_usages[qnode_id] == curie:
            return True
    return False


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


def get_original_curie(returned_curie, qnode_id, curie_map, log):
    original_curie_matches = [original_curie for original_curie, used_curies in curie_map[qnode_id].items() if
                              returned_curie in used_curies]
    if not original_curie_matches:
        log.error(f"Could not find returned {qnode_id} node {returned_curie} in the curie map",
                  error_code="SynonymMappingError")
        return None
    elif len(original_curie_matches) > 1:
        log.error(f"More than 1 possible remapping for returned {qnode_id} node {returned_curie}",
                  error_code="SynonymMappingError")
    return original_curie_matches[0]


def guess_qnode_type(qnode_curie, log):
    kgni = KGNodeIndex()
    curie_list = convert_string_or_list_to_list(qnode_curie)
    node_types = set()
    for curie in curie_list:
        curie_info = kgni.get_equivalent_entities(curie=curie).get(curie)
        if curie_info:
            node_type = curie_info['type'][0] if curie_info['type'] else None
            if node_type:
                node_types.add(node_type)

    # Only use this node type if we found the same type for all curies in the list
    if len(node_types) == 1:
        node_type = node_types.pop()
        log.warning(f"No type was specified for qnode with curie {qnode_curie}; using type '{node_type}' found via KGNodeIndex")
        return node_type
    elif not node_types:
        log.warning(f"Could not guess a node type to use for qnode with curie {qnode_curie} (curie is not in KGNodeIndex)")
        return ""
    else:
        log.warning(f"Could not guess a node type to use for qnode with curie {qnode_curie} (more than one possible "
                    f"node type was found: {', '.join(node_types)})")
        return ""
