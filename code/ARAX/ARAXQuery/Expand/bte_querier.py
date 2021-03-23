#!/bin/env python3
import itertools
import sys
import os
import traceback
import asyncio
from typing import List, Dict, Tuple, Set

from biothings_explorer.user_query_dispatcher import SingleEdgeQueryDispatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.attribute import Attribute


class BTEQuerier:

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using BTE.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_keys for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        enforce_directionality = self.response.data['parameters'].get('enforce_directionality')
        use_synonyms = self.response.data['parameters'].get('use_synonyms')
        log = self.response
        answer_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        valid_bte_inputs_dict = self._get_valid_bte_inputs_dict()
        query_graph = eu.make_qg_use_old_types(query_graph)  # Temporary patch until KP is TRAPI 1.0 compliant

        # Validate our input to make sure it will work with BTE
        input_qnode_key, output_qnode_key = self._validate_and_pre_process_input(qg=query_graph,
                                                                                 valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                                 enforce_directionality=enforce_directionality,
                                                                                 use_synonyms=use_synonyms,
                                                                                 log=log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map
        input_qnode = query_graph.nodes[input_qnode_key]
        output_qnode = query_graph.nodes[output_qnode_key]

        # Use BTE to answer the query
        answer_kg, accepted_curies = self._answer_query_using_bte(input_qnode_key=input_qnode_key,
                                                                  output_qnode_key=output_qnode_key,
                                                                  qg=query_graph,
                                                                  answer_kg=answer_kg,
                                                                  valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                  log=log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Hack to achieve a curie-to-curie query, if necessary
        if eu.qg_is_fulfilled(query_graph, answer_kg) and input_qnode.id and output_qnode.id:
            answer_kg = self._prune_answers_to_achieve_curie_to_curie_query(answer_kg, output_qnode_key, query_graph)

        # Report our findings
        if eu.qg_is_fulfilled(query_graph, answer_kg):
            answer_kg = eu.switch_kg_to_arax_curie_format(answer_kg)
            edge_to_nodes_map = self._create_edge_to_nodes_map(answer_kg, input_qnode_key, output_qnode_key)
        elif not accepted_curies:
            log.warning(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are: "
                        f"{valid_bte_inputs_dict['curie_prefixes']}")
        return answer_kg, edge_to_nodes_map

    def _answer_query_using_bte(self, input_qnode_key: str, output_qnode_key: str, qg: QueryGraph,
                                answer_kg: QGOrganizedKnowledgeGraph, valid_bte_inputs_dict: Dict[str, Set[str]],
                                log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, Set[str]]:
        accepted_curies = set()
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        input_qnode = qg.nodes[input_qnode_key]
        output_qnode = qg.nodes[output_qnode_key]
        # Send this single-edge query to BTE, input curie by input curie (adding findings to our answer KG as we go)
        for curie in input_qnode.id:
            # Consider all different combinations of qnode types (can be multiple if gene/protein)
            for input_qnode_category, output_qnode_category in itertools.product(input_qnode.category, output_qnode.category):
                if eu.get_curie_prefix(curie) in valid_bte_inputs_dict['curie_prefixes']:
                    accepted_curies.add(curie)
                    try:
                        loop = asyncio.new_event_loop()
                        seqd = SingleEdgeQueryDispatcher(input_cls=input_qnode_category,
                                                         output_cls=output_qnode_category,
                                                         pred=qedge.predicate,
                                                         input_id=eu.get_curie_prefix(curie),
                                                         values=eu.get_curie_local_id(curie),
                                                         loop=loop)
                        log.debug(f"Sending query to BTE: {curie}-{qedge.predicate if qedge.predicate else ''}->{output_qnode_category}")
                        seqd.query()
                        reasoner_std_response = seqd.to_reasoner_std()
                    except Exception:
                        trace_back = traceback.format_exc()
                        error_type, error, _ = sys.exc_info()
                        log.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                  error_code=error_type.__name__)
                        return answer_kg, accepted_curies
                    else:
                        answer_kg = self._add_answers_to_kg(answer_kg, reasoner_std_response, input_qnode_key, output_qnode_key, qedge_key, log)
        return answer_kg, accepted_curies

    def _add_answers_to_kg(self, answer_kg: QGOrganizedKnowledgeGraph, reasoner_std_response: Dict[str, any],
                           input_qnode_key: str, output_qnode_key: str, qedge_key: str, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        kg_to_qg_ids_dict = self._build_kg_to_qg_id_dict(reasoner_std_response['results'])
        if reasoner_std_response['knowledge_graph']['edges']:
            remapped_node_keys = dict()
            log.debug(f"Got results back from BTE for this query "
                      f"({len(reasoner_std_response['knowledge_graph']['edges'])} edges)")

            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                bte_node_key = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.category = eu.convert_to_list(eu.convert_string_to_snake_case(node.get('type')))

                # Map the returned BTE qg_ids back to the original qnode_keys in our query graph
                bte_qg_id = kg_to_qg_ids_dict['nodes'].get(bte_node_key)
                if bte_qg_id == "n0":
                    qnode_key = input_qnode_key
                elif bte_qg_id == "n1":
                    qnode_key = output_qnode_key
                else:
                    log.error("Could not map BTE qg_id to ARAX qnode_key", error_code="UnknownQGID")
                    return answer_kg

                # Find and use the preferred equivalent identifier for this node (if it's an output node)
                if qnode_key == output_qnode_key:
                    if bte_node_key in remapped_node_keys:
                        swagger_node_key = remapped_node_keys.get(bte_node_key)
                    else:
                        equivalent_curies = [f"{prefix}:{eu.get_curie_local_id(local_id)}" for prefix, local_ids in
                                             node.get('equivalent_identifiers').items() for local_id in local_ids]
                        swagger_node_key = self._get_best_equivalent_bte_curie(equivalent_curies, swagger_node.category[0])
                        remapped_node_keys[bte_node_key] = swagger_node_key
                else:
                    swagger_node_key = bte_node_key

                answer_kg.add_node(swagger_node_key, swagger_node, qnode_key)

            for edge in reasoner_std_response['knowledge_graph']['edges']:
                swagger_edge = Edge()
                swagger_edge_key = edge.get("id")
                swagger_edge.predicate = edge.get('type')
                swagger_edge.subject = remapped_node_keys.get(edge.get('source_id'), edge.get('source_id'))
                swagger_edge.object = remapped_node_keys.get(edge.get('target_id'), edge.get('target_id'))
                swagger_edge.attributes = [Attribute(name="provided_by", value=edge.get('edge_source'), type=eu.get_attribute_type("provided_by")),
                                           Attribute(name="is_defined_by", value="BTE", type=eu.get_attribute_type("is_defined_by"))]
                # Map the returned BTE qg_id back to the original qedge_key in our query graph
                bte_qg_id = kg_to_qg_ids_dict['edges'].get(swagger_edge_key)
                if bte_qg_id != "e1":
                    log.error("Could not map BTE qg_id to ARAX qedge_key", error_code="UnknownQGID")
                    return answer_kg
                answer_kg.add_edge(swagger_edge_key, swagger_edge, qedge_key)

        return answer_kg

    @staticmethod
    def _validate_and_pre_process_input(qg: QueryGraph, valid_bte_inputs_dict: Dict[str, Set[str]],
                                        enforce_directionality: bool, use_synonyms: bool, log: ARAXResponse) -> Tuple[str, str]:
        # Make sure we have a valid one-hop query graph
        if len(qg.edges) != 1 or len(qg.nodes) != 2:
            log.error(f"BTE can only accept one-hop query graphs (your QG has {len(qg.nodes)} nodes and "
                      f"{len(qg.edges)} edges)", error_code="InvalidQueryGraph")
            return "", ""
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]

        # Make sure at least one of our qnodes has a curie
        qnodes_with_curies = [qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.id]
        if not qnodes_with_curies:
            log.error(f"Neither qnode for qedge {qedge_key} has a curie specified. BTE requires that at least one of "
                      f"them has a curie. Your query graph is: {qg.to_dict()}", error_code="UnsupportedQueryForKP")
            return "", ""

        # Figure out which query node is input vs. output
        if enforce_directionality:
            input_qnode_key = qedge.subject
            output_qnode_key = qedge.object
        else:
            input_qnode_key = next(qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.id)
            output_qnode_key = list(set(qg.nodes).difference({input_qnode_key}))[0]
            log.warning(f"BTE cannot do bidirectional queries; the query for this edge will be directed, going: "
                        f"{input_qnode_key}-->{output_qnode_key}")
        input_qnode = qg.nodes[input_qnode_key]
        output_qnode = qg.nodes[output_qnode_key]

        # Make sure predicate is allowed
        if qedge.predicate:
            accepted_predicates = set(qedge.predicate).intersection(valid_bte_inputs_dict['predicates'])
            # Throw an error if none of the predicates are supported
            if not accepted_predicates:
                log.error(f"BTE does not accept predicate(s) {qedge.predicate}. Valid options are "
                          f"{valid_bte_inputs_dict['predicates']}", error_code="UnsupportedQueryForKP")
                return "", ""
            # Give a warning if only some of the predicates are supported
            elif len(accepted_predicates) < len(qedge.predicate):
                unaccepted_predicates = set(qedge.predicate).difference(accepted_predicates)
                log.warning(f"Some of qedge {qedge_key}'s predicates are not accepted by BTE: {unaccepted_predicates}."
                            f" Valid options are: {valid_bte_inputs_dict['predicates']}")
                qedge.predicate = list(accepted_predicates)

        # Process qnode types (convert to preferred format, make sure allowed)
        input_qnode.category = [eu.convert_string_to_pascal_case(node_category) for node_category in eu.convert_to_list(input_qnode.category)]
        output_qnode.category = [eu.convert_string_to_pascal_case(node_category) for node_category in eu.convert_to_list(output_qnode.category)]
        qnodes_missing_type = [qnode_key for qnode_key in [input_qnode_key, output_qnode_key] if not qg.nodes[qnode_key].category]
        if qnodes_missing_type:
            log.error(f"BTE requires every query node to have a category. QNode(s) missing a category: "
                      f"{', '.join(qnodes_missing_type)}", error_code="InvalidInput")
            return "", ""
        invalid_qnode_categories = [node_category for qnode in [input_qnode, output_qnode] for node_category in qnode.category
                                    if node_category not in valid_bte_inputs_dict['node_categories']]
        if invalid_qnode_categories:
            log.error(f"BTE does not accept QNode category(s): {', '.join(invalid_qnode_categories)}. Valid options are "
                      f"{valid_bte_inputs_dict['node_categories']}", error_code="InvalidInput")
            return "", ""

        # Sub in curie synonyms as appropriate
        if use_synonyms:
            qnodes_with_curies = [qnode for qnode in [input_qnode, output_qnode] if qnode.id]
            for qnode in qnodes_with_curies:
                synonymized_curies = eu.get_curie_synonyms(qnode.id, log)
                qnode.id = synonymized_curies

        # Make sure our input node curies are in list form and use prefixes BTE prefers
        input_curie_list = eu.convert_to_list(input_qnode.id)
        input_qnode.id = [eu.convert_curie_to_bte_format(curie) for curie in input_curie_list]

        return input_qnode_key, output_qnode_key

    @staticmethod
    def _prune_answers_to_achieve_curie_to_curie_query(kg: QGOrganizedKnowledgeGraph, output_qnode_key: str, qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This is a way of hacking around BTE's limitation where it can only do (node with curie)-->(non-specific node)
        kinds of queries. We do the non-specific query, and then use this function to remove all of the answer nodes
        that do not correspond to the curie we wanted for the 'output' node.
        """
        # Remove 'output' nodes in the KG that aren't actually the ones we were looking for
        output_qnode = qg.nodes[output_qnode_key]
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        desired_output_curies = set(eu.convert_to_list(output_qnode.id))
        all_output_node_keys = set(kg.nodes_by_qg_id[output_qnode_key])
        output_node_keys_to_remove = all_output_node_keys.difference(desired_output_curies)
        for node_key in output_node_keys_to_remove:
            kg.nodes_by_qg_id[output_qnode_key].pop(node_key)

        # And remove any edges that used them
        edge_keys_to_remove = set()
        for edge_key, edge in kg.edges_by_qg_id[qedge_key].items():
            if edge.object in output_node_keys_to_remove:  # Edge object always contains output node ID for BTE
                edge_keys_to_remove.add(edge_key)
        for edge_key in edge_keys_to_remove:
            kg.edges_by_qg_id[qedge_key].pop(edge_key)

        return kg

    @staticmethod
    def _create_edge_to_nodes_map(kg: QGOrganizedKnowledgeGraph, input_qnode_key: str, output_qnode_key: str) -> Dict[str, Dict[str, str]]:
        edge_to_nodes_map = dict()
        for qedge_key, edges in kg.edges_by_qg_id.items():
            for edge_key, edge in edges.items():
                # BTE single-edge queries are always directed (meaning, edge.subject == input qnode ID)
                edge_to_nodes_map[edge_key] = {input_qnode_key: edge.subject, output_qnode_key: edge.object}
        return edge_to_nodes_map

    @staticmethod
    def _get_valid_bte_inputs_dict() -> Dict[str, Set[str]]:
        # TODO: Load these using the soon to be built method in ARAX/KnowledgeSources (then will be regularly updated)
        node_categories = {'ChemicalSubstance', 'Transcript', 'AnatomicalEntity', 'Disease', 'GenomicEntity', 'Gene',
                           'BiologicalProcess', 'Cell', 'SequenceVariant', 'MolecularActivity', 'PhenotypicFeature',
                           'Protein', 'CellularComponent', 'Pathway'}
        curie_prefixes = {'ENSEMBL', 'CHEBI', 'HP', 'DRUGBANK', 'MOP', 'MONDO', 'GO', 'HGNC', 'CL', 'DOID', 'MESH',
                          'OMIM', 'SO', 'SYMBOL', 'Reactome', 'UBERON', 'UNIPROTKB', 'PR', 'NCBIGene', 'UMLS',
                          'CHEMBL.COMPOUND', 'MGI', 'DBSNP', 'WIKIPATHWAYS', 'MP'}
        predicates = {'disrupts', 'coexists_with', 'caused_by', 'subclass_of', 'affected_by', 'manifested_by',
                      'physically_interacts_with', 'prevented_by', 'has_part', 'negatively_regulates',
                      'functional_association', 'precedes', 'homologous_to', 'negatively_regulated_by',
                      'positively_regulated_by', 'has_subclass', 'contraindication', 'located_in', 'prevents',
                      'disrupted_by', 'preceded_by', 'treats', 'produces', 'treated_by', 'derives_from',
                      'gene_to_transcript_relationship', 'predisposes', 'affects', 'metabolize', 'has_gene_product',
                      'produced_by', 'derives_info', 'related_to', 'causes', 'contraindicated_by', 'part_of',
                      'metabolic_processing_affected_by', 'positively_regulates', 'manifestation_of'}
        return {'node_categories': node_categories, 'curie_prefixes': curie_prefixes, 'predicates': predicates}

    @staticmethod
    def _build_kg_to_qg_id_dict(results: Dict[str, any]) -> Dict[str, Dict[str, List[str]]]:
        kg_to_qg_ids = {'nodes': dict(), 'edges': dict()}
        for node_binding in results['node_bindings']:
            node_key = node_binding['kg_id']
            qnode_key = node_binding['qg_id']
            kg_to_qg_ids['nodes'][node_key] = qnode_key
        for edge_binding in results['edge_bindings']:
            edge_keys = eu.convert_to_list(edge_binding['kg_id'])
            qedge_keys = edge_binding['qg_id']
            for kg_id in edge_keys:
                kg_to_qg_ids['edges'][kg_id] = qedge_keys
        return kg_to_qg_ids

    @staticmethod
    def _get_best_equivalent_bte_curie(equivalent_curies: List[str], node_category: str) -> str:
        # Curie prefixes in order of preference for different node types (not all-inclusive)
        preferred_node_prefixes_dict = {'chemical_substance': ['CHEMBL.COMPOUND', 'CHEBI'],
                                        'protein': ['UNIPROTKB', 'PR'],
                                        'gene': ['NCBIGENE', 'ENSEMBL', 'HGNC', 'GO'],
                                        'disease': ['DOID', 'MONDO', 'OMIM', 'MESH'],
                                        'phenotypic_feature': ['HP', 'OMIM'],
                                        'anatomical_entity': ['UBERON', 'FMA', 'CL'],
                                        'pathway': ['REACTOME'],
                                        'biological_process': ['GO'],
                                        'cellular_component': ['GO']}
        prefixes_in_order_of_preference = preferred_node_prefixes_dict.get(eu.convert_string_to_snake_case(node_category), [])
        equivalent_curies.sort()

        # Pick the curie that uses the (relatively) most preferred prefix
        lowest_ranking = 10000
        best_curie = None
        for curie in equivalent_curies:
            uppercase_prefix = eu.get_curie_prefix(curie).upper()
            if uppercase_prefix in prefixes_in_order_of_preference:
                ranking = prefixes_in_order_of_preference.index(uppercase_prefix)
                if ranking < lowest_ranking:
                    lowest_ranking = ranking
                    best_curie = curie

        # Otherwise, just try to pick one that isn't 'NAME:___'
        if not best_curie:
            non_name_curies = [curie for curie in equivalent_curies if eu.get_curie_prefix(curie).upper() != 'NAME']
            best_curie = non_name_curies[0] if non_name_curies else equivalent_curies[0]

        return best_curie
