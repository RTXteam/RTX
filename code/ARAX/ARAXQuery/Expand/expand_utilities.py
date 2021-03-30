#!/bin/env python3
# This file contains utilities/helper functions for general use within the Expand module
import sys
import os
import traceback
from typing import List, Dict, Union, Set, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer


class QGOrganizedKnowledgeGraph:
    def __init__(self, nodes: Dict[str, Dict[str, Node]] = None, edges: Dict[str, Dict[str, Edge]] = None):
        self.nodes_by_qg_id = nodes if nodes else dict()
        self.edges_by_qg_id = edges if edges else dict()

    def __str__(self):
        return f"nodes_by_qg_id:\n{self.nodes_by_qg_id}\nedges_by_qg_id:\n{self.edges_by_qg_id}"

    def add_node(self, node_key: str, node: Node, qnode_key: str):
        if qnode_key not in self.nodes_by_qg_id:
            self.nodes_by_qg_id[qnode_key] = dict()
        self.nodes_by_qg_id[qnode_key][node_key] = node

    def add_edge(self, edge_key: str, edge: Edge, qedge_key: str):
        if qedge_key not in self.edges_by_qg_id:
            self.edges_by_qg_id[qedge_key] = dict()
        self.edges_by_qg_id[qedge_key][edge_key] = edge

    def get_all_node_keys_used_by_edges(self) -> Set[str]:
        return {node_key for edges in self.edges_by_qg_id.values() for edge in edges.values()
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


def copy_qg(qg: QueryGraph) -> QueryGraph:
    return QueryGraph(nodes={qnode_key: copy_qnode(qnode) for qnode_key, qnode in qg.nodes.items()},
                      edges={qedge_key: copy_qedge(qedge) for qedge_key, qedge in qg.edges.items()})


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


def get_node_category_overrides_for_kp(kp_name: str) -> Union[Dict[str, str], None]:
    overrides = {"MolePro": {"biolink:Protein": "biolink:Gene"},
                 "GeneticsKP": {"biolink:Protein": "biolink:Gene"}}
    return overrides.get(kp_name)


def get_kp_preferred_prefixes(kp_name: str) -> Union[Dict[str, str], None]:
    # TODO: Dynamically determine these down the road once meta_knowledge_map endpoint is added to TRAPI
    preferred_prefixes = {"MolePro": {"biolink:ChemicalSubstance": "CHEMBL.COMPOUND",
                                      "biolink:Gene": "HGNC",
                                      "biolink:Disease": "MONDO"},
                          "GeneticsKP": {"biolink:Gene": "NCBIGene",
                                         "biolink:Pathway": "GO",
                                         "biolink:PhenotypicFeature": "EFO",
                                         "biolink:Disease": "EFO"}}
    return preferred_prefixes.get(kp_name)


def kp_supports_category_lists(kp_name: str) -> bool:
    # TRAPI 1.0 specifies qnode.category can be a list, but not all KPs support that
    list_support = {"ARAX/KG2": True,
                    "MolePro": False,
                    "GeneticsKP": False,
                    "BTE": False}
    return list_support.get(kp_name, True)


def kp_supports_predicate_lists(kp_name: str) -> bool:
    # TRAPI 1.0 specifies qedge.predicate can be a list, but not all KPs support that
    list_support = {"ARAX/KG2": True,
                    "MolePro": False,
                    "GeneticsKP": False,
                    "BTE": False}
    return list_support.get(kp_name, True)


def kp_supports_none_for_predicate(kp_name: str) -> bool:
    # This information isn't captured in TRAPI anywhere currently, so hardcoding it
    none_predicates = {"ARAX/KG2": True,
                       "MolePro": True,
                       "GeneticsKP": False,
                       "BTE": True}
    return none_predicates.get(kp_name, True)


def kp_supports_none_for_category(kp_name: str) -> bool:
    # This information isn't captured in TRAPI anywhere currently, so hardcoding it
    none_categories = {"ARAX/KG2": True,
                       "MolePro": False,
                       "GeneticsKP": False,
                       "BTE": True}
    return none_categories.get(kp_name, True)


def get_curie_synonyms(curie: Union[str, List[str]], log: ARAXResponse) -> List[str]:
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
                log.warning(f"NodeSynonymizer did not return canonical info for: {unrecognized_curies}")
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
                log.warning(f"NodeSynonymizer did not return canonical info for: {unrecognized_curies}")
            canonical_curies = {canonical_curies_dict[recognized_curie].get('preferred_curie') for recognized_curie in recognized_input_curies}
            # Include any original curies we weren't able to find a canonical version for
            canonical_curies.update(unrecognized_curies)
            if not canonical_curies:
                log.error(f"Final list of canonical curies is empty. This shouldn't happen!", error_code="CanonicalCurieIssue")
            return list(canonical_curies)
        else:
            log.error(f"NodeSynonymizer returned None", error_code="NodeNormalizationIssue")
            return []


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


def get_attribute_type(attribute_name: str) -> str:
    # These are placeholder types for attributes (plan is to discuss such types in API working group #1192)
    attribute_type_map = {
        "all_names": "biolink:synonym",
        "deprecated": "biolink:Unknown",
        "equivalent_curies": "biolink:synonym",
        "full_name": "biolink:full_name",
        "is_defined_by": "biolink:Unknown",
        "negated": "biolink:negated",
        "probability": "biolink:p_value",
        "provided_by": "biolink:provided_by",
        "publications": "biolink:publications",
        "relation": "biolink:relation",
        "symbol": "biolink:symbol",
        "synonym": "biolink:synonym",
        "update_date": "metatype:Datetime",
        "uri": "metatype:Uri",
        "iri": "biolink:IriType"
    }
    return attribute_type_map.get(attribute_name, "biolink:Unknown")


def get_kp_endpoint_url(kp_name: str) -> Union[str, None]:
    endpoint_map = {
        "BTE": "https://api.bte.ncats.io/v1",
        "GeneticsKP": "https://translator.broadinstitute.org/genetics_provider/trapi/v1.0",
        "MolePro": "https://translator.broadinstitute.org/molepro/trapi/v1.0",
        "ARAX/KG2": "https://arax.ncats.io/api/rtxkg2/v1.0"
    }
    return endpoint_map.get(kp_name)


def switch_back_to_str_or_list_types(qg: QueryGraph) -> QueryGraph:
    # Switches QG back to old style where qnode.category and qedge.predicate can be strings OR lists (vs. always lists)
    for qnode in qg.nodes.values():
        if not qnode.category:
            qnode.category = None
        elif len(qnode.category) == 1:
            qnode.category = qnode.category[0]
    for qedge in qg.edges.values():
        if not qedge.predicate:
            qedge.predicate = None
        elif len(qedge.predicate) == 1:
            qedge.predicate = qedge.predicate[0]
    return qg


def make_qg_use_old_snake_case_types(qg: QueryGraph) -> QueryGraph:
    # This is a temporary patch needed for KPs not yet TRAPI 1.0 compliant
    qg_copy = QueryGraph(nodes={qnode_key: copy_qnode(qnode) for qnode_key, qnode in qg.nodes.items()},
                         edges={qedge_key: copy_qedge(qedge) for qedge_key, qedge in qg.edges.items()})
    for qnode in qg_copy.nodes.values():
        if qnode.category:
            categories = convert_to_list(qnode.category)
            prefixless_categories = [category.split(":")[-1] for category in categories]
            qnode.category = [convert_string_to_snake_case(category) for category in prefixless_categories]
    for qedge in qg_copy.edges.values():
        if qedge.predicate:
            predicates = convert_to_list(qedge.predicate)
            qedge.predicate = [predicate.split(":")[-1] for predicate in predicates]
    return qg_copy
