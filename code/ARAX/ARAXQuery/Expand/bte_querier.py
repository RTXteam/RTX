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
from expand_utilities import DictKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from response import Response
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.query_graph import QueryGraph


class BTEQuerier:

    def __init__(self, response_object: Response):
        self.response = response_object

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using BTE.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_ids for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        enforce_directionality = self.response.data['parameters'].get('enforce_directionality')
        continue_if_no_results = self.response.data['parameters'].get('continue_if_no_results')
        use_synonyms = self.response.data['parameters'].get('use_synonyms')
        log = self.response
        answer_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()
        valid_bte_inputs_dict = self._get_valid_bte_inputs_dict()

        # Validate our input to make sure it will work with BTE
        qedge, input_qnode, output_qnode = self._validate_and_pre_process_input(query_graph=query_graph,
                                                                                valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                                enforce_directionality=enforce_directionality,
                                                                                use_synonyms=use_synonyms,
                                                                                log=log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Use BTE to answer the query
        answer_kg, accepted_curies = self._answer_query_using_bte(input_qnode=input_qnode,
                                                                  output_qnode=output_qnode,
                                                                  qedge=qedge,
                                                                  answer_kg=answer_kg,
                                                                  valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                  log=log)
        if log.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Hack to achieve a curie-to-curie query, if necessary
        if eu.qg_is_fulfilled(query_graph, answer_kg) and input_qnode.curie and output_qnode.curie:
            answer_kg = self._prune_answers_to_achieve_curie_to_curie_query(answer_kg, output_qnode, qedge)

        # Report our findings
        if eu.qg_is_fulfilled(query_graph, answer_kg):
            answer_kg = eu.switch_kg_to_arax_curie_format(answer_kg)
            edge_to_nodes_map = self._create_edge_to_nodes_map(answer_kg, input_qnode.id, output_qnode.id)
        else:
            self._log_proper_no_results_message(accepted_curies, continue_if_no_results, valid_bte_inputs_dict['curie_prefixes'], log)

        return answer_kg, edge_to_nodes_map

    def _answer_query_using_bte(self, input_qnode: QNode, output_qnode: QNode, qedge: QEdge,
                                answer_kg: DictKnowledgeGraph, valid_bte_inputs_dict: Dict[str, Set[str]],
                                log: Response) -> Tuple[DictKnowledgeGraph, Set[str]]:
        accepted_curies = set()
        # Send this single-edge query to BTE, input curie by input curie (adding findings to our answer KG as we go)
        for curie in input_qnode.curie:
            # Consider all different combinations of qnode types (can be multiple if gene/protein)
            for input_qnode_type, output_qnode_type in itertools.product(input_qnode.type, output_qnode.type):
                if eu.get_curie_prefix(curie) in valid_bte_inputs_dict['curie_prefixes']:
                    accepted_curies.add(curie)
                    try:
                        loop = asyncio.new_event_loop()
                        seqd = SingleEdgeQueryDispatcher(input_cls=input_qnode_type,
                                                         output_cls=output_qnode_type,
                                                         pred=qedge.type,
                                                         input_id=eu.get_curie_prefix(curie),
                                                         values=eu.get_curie_local_id(curie),
                                                         loop=loop)
                        log.debug(f"Sending query to BTE: {curie}-{qedge.type if qedge.type else ''}->{output_qnode_type}")
                        seqd.query()
                        reasoner_std_response = seqd.to_reasoner_std()
                    except Exception:
                        trace_back = traceback.format_exc()
                        error_type, error, _ = sys.exc_info()
                        log.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                  error_code=error_type.__name__)
                        return answer_kg, accepted_curies
                    else:
                        answer_kg = self._add_answers_to_kg(answer_kg, reasoner_std_response, input_qnode.id, output_qnode.id, qedge.id, log)
        return answer_kg, accepted_curies

    def _add_answers_to_kg(self, answer_kg: DictKnowledgeGraph, reasoner_std_response: Dict[str, any],
                           input_qnode_id: str, output_qnode_id: str, qedge_id: str, log: Response) -> DictKnowledgeGraph:
        kg_to_qg_ids_dict = self._build_kg_to_qg_id_dict(reasoner_std_response['results'])
        if reasoner_std_response['knowledge_graph']['edges']:
            remapped_node_ids = dict()
            log.debug(f"Got results back from BTE for this query "
                      f"({len(reasoner_std_response['knowledge_graph']['edges'])} edges)")

            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                bte_node_id = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.type = eu.convert_string_or_list_to_list(eu.convert_string_to_snake_case(node.get('type')))

                # Map the returned BTE qg_ids back to the original qnode_ids in our query graph
                bte_qg_id = kg_to_qg_ids_dict['nodes'].get(bte_node_id)
                if bte_qg_id == "n0":
                    qnode_id = input_qnode_id
                elif bte_qg_id == "n1":
                    qnode_id = output_qnode_id
                else:
                    log.error("Could not map BTE qg_id to ARAX qnode_id", error_code="UnknownQGID")
                    return answer_kg

                # Find and use the preferred equivalent identifier for this node (if it's an output node)
                if qnode_id == output_qnode_id:
                    if bte_node_id in remapped_node_ids:
                        swagger_node.id = remapped_node_ids.get(bte_node_id)
                    else:
                        equivalent_curies = [f"{prefix}:{eu.get_curie_local_id(local_id)}" for prefix, local_ids in
                                             node.get('equivalent_identifiers').items() for local_id in local_ids]
                        swagger_node.id = self._get_best_equivalent_bte_curie(equivalent_curies, swagger_node.type[0])
                        remapped_node_ids[bte_node_id] = swagger_node.id
                else:
                    swagger_node.id = bte_node_id

                answer_kg.add_node(swagger_node, qnode_id)

            for edge in reasoner_std_response['knowledge_graph']['edges']:
                swagger_edge = Edge()
                swagger_edge.id = edge.get("id")
                swagger_edge.type = edge.get('type')
                swagger_edge.source_id = remapped_node_ids.get(edge.get('source_id'), edge.get('source_id'))
                swagger_edge.target_id = remapped_node_ids.get(edge.get('target_id'), edge.get('target_id'))
                swagger_edge.is_defined_by = "BTE"
                swagger_edge.provided_by = edge.get('edge_source')
                # Map the returned BTE qg_id back to the original qedge_id in our query graph
                bte_qg_id = kg_to_qg_ids_dict['edges'].get(swagger_edge.id)
                if bte_qg_id != "e1":
                    log.error("Could not map BTE qg_id to ARAX qedge_id", error_code="UnknownQGID")
                    return answer_kg
                answer_kg.add_edge(swagger_edge, qedge_id)

        return answer_kg

    @staticmethod
    def _validate_and_pre_process_input(query_graph: QueryGraph, valid_bte_inputs_dict: Dict[str, Set[str]],
                                        enforce_directionality: bool, use_synonyms: bool, log: Response) -> Tuple[QEdge, QNode, QNode]:
        # Make sure we have a valid one-hop query graph
        if len(query_graph.edges) != 1 or len(query_graph.nodes) != 2:
            log.error(f"BTE can only accept one-hop query graphs (your QG has {len(query_graph.nodes)} nodes and "
                      f"{len(query_graph.edges)} edges)", error_code="InvalidQueryGraph")
            return None, None, None
        qedge = query_graph.edges[0]

        # Make sure at least one of our qnodes has a curie
        qnodes_with_curies = [qnode for qnode in query_graph.nodes if qnode.curie]
        if not qnodes_with_curies:
            log.error(f"Neither qnode for qedge {qedge.id} has a curie specified. BTE requires that at least one of "
                      f"them has a curie. Your query graph is: {query_graph.to_dict()}", error_code="UnsupportedQueryForKP")
            return None, None, None

        # Figure out which query node is input vs. output
        if enforce_directionality:
            input_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.source_id)
            output_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.target_id)
        else:
            input_qnode = next(qnode for qnode in query_graph.nodes if qnode.curie)
            output_qnode = next(qnode for qnode in query_graph.nodes if qnode.id != input_qnode.id)
            log.warning(f"BTE cannot do bidirectional queries; the query for this edge will be directed, going: "
                        f"{input_qnode.id}-->{output_qnode.id}")

        # Make sure predicate is allowed
        if qedge.type not in valid_bte_inputs_dict['predicates'] and qedge.type is not None:
            log.error(f"BTE does not accept predicate '{qedge.type}'. Valid options are "
                      f"{valid_bte_inputs_dict['predicates']}", error_code="InvalidInput")
            return None, None, None

        # Process qnode types (convert to preferred format, make sure allowed)
        input_qnode.type = [eu.convert_string_to_pascal_case(node_type) for node_type in eu.convert_string_or_list_to_list(input_qnode.type)]
        output_qnode.type = [eu.convert_string_to_pascal_case(node_type) for node_type in eu.convert_string_or_list_to_list(output_qnode.type)]
        qnodes_missing_type = [qnode.id for qnode in [input_qnode, output_qnode] if not qnode.type]
        if qnodes_missing_type:
            log.error(f"BTE requires every query node to have a type. QNode(s) missing a type: "
                      f"{', '.join(qnodes_missing_type)}", error_code="InvalidInput")
            return None, None, None
        invalid_qnode_types = [node_type for qnode in [input_qnode, output_qnode] for node_type in qnode.type
                               if node_type not in valid_bte_inputs_dict['node_types']]
        if invalid_qnode_types:
            log.error(f"BTE does not accept QNode type(s): {', '.join(invalid_qnode_types)}. Valid options are "
                      f"{valid_bte_inputs_dict['node_types']}", error_code="InvalidInput")
            return None, None, None

        # Sub in curie synonyms as appropriate
        if use_synonyms:
            qnodes_with_curies = [qnode for qnode in [input_qnode, output_qnode] if qnode.curie]
            for qnode in qnodes_with_curies:
                synonymized_curies = eu.get_curie_synonyms(qnode.curie, log)
                qnode.curie = synonymized_curies

        # Make sure our input node curies are in list form and use prefixes BTE prefers
        input_curie_list = eu.convert_string_or_list_to_list(input_qnode.curie)
        input_qnode.curie = [eu.convert_curie_to_bte_format(curie) for curie in input_curie_list]

        return qedge, input_qnode, output_qnode

    @staticmethod
    def _log_proper_no_results_message(accepted_curies: Set[str], continue_if_no_results: bool,
                                       valid_prefixes: Set[str], log: Response):
        if continue_if_no_results:
            if not accepted_curies:
                log.warning(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are: "
                            f"{valid_prefixes}")
            log.warning(f"No paths were found in BTE satisfying this query graph")
        else:
            if not accepted_curies:
                log.error(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are: "
                          f"{valid_prefixes}", error_code="InvalidPrefix")
            log.error(f"No paths were found in BTE satisfying this query graph", error_code="NoResults")

    @staticmethod
    def _prune_answers_to_achieve_curie_to_curie_query(kg: DictKnowledgeGraph, output_qnode: QNode, qedge: QEdge) -> DictKnowledgeGraph:
        """
        This is a way of hacking around BTE's limitation where it can only do (node with curie)-->(non-specific node)
        kinds of queries. We do the non-specific query, and then use this function to remove all of the answer nodes
        that do not correspond to the curie we wanted for the 'output' node.
        """
        # Remove 'output' nodes in the KG that aren't actually the ones we were looking for
        desired_output_curies = set(eu.convert_string_or_list_to_list(output_qnode.curie))
        all_output_node_ids = set(kg.nodes_by_qg_id[output_qnode.id])
        output_node_ids_to_remove = all_output_node_ids.difference(desired_output_curies)
        for node_id in output_node_ids_to_remove:
            kg.nodes_by_qg_id[output_qnode.id].pop(node_id)

        # And remove any edges that used them
        edge_ids_to_remove = set()
        for edge_id, edge in kg.edges_by_qg_id[qedge.id].items():
            if edge.target_id in output_node_ids_to_remove:  # Edge target_id always contains output node ID for BTE
                edge_ids_to_remove.add(edge_id)
        for edge_id in edge_ids_to_remove:
            kg.edges_by_qg_id[qedge.id].pop(edge_id)

        return kg

    @staticmethod
    def _create_edge_to_nodes_map(kg: DictKnowledgeGraph, input_qnode_id: str, output_qnode_id: str) -> Dict[str, Dict[str, str]]:
        edge_to_nodes_map = dict()
        for qedge_id, edges in kg.edges_by_qg_id.items():
            for edge_key, edge in edges.items():
                # BTE single-edge queries are always directed (meaning, edge.source_id == input qnode ID)
                edge_to_nodes_map[edge.id] = {input_qnode_id: edge.source_id, output_qnode_id: edge.target_id}
        return edge_to_nodes_map

    @staticmethod
    def _get_valid_bte_inputs_dict() -> Dict[str, Set[str]]:
        # TODO: Load these using the soon to be built method in ARAX/KnowledgeSources (then will be regularly updated)
        node_types = {'ChemicalSubstance', 'Transcript', 'AnatomicalEntity', 'Disease', 'GenomicEntity', 'Gene',
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
        return {'node_types': node_types, 'curie_prefixes': curie_prefixes, 'predicates': predicates}

    @staticmethod
    def _build_kg_to_qg_id_dict(results: Dict[str, any]) -> Dict[str, Dict[str, List[str]]]:
        kg_to_qg_ids = {'nodes': dict(), 'edges': dict()}
        for node_binding in results['node_bindings']:
            node_id = node_binding['kg_id']
            qnode_id = node_binding['qg_id']
            kg_to_qg_ids['nodes'][node_id] = qnode_id
        for edge_binding in results['edge_bindings']:
            edge_ids = eu.convert_string_or_list_to_list(edge_binding['kg_id'])
            qedge_ids = edge_binding['qg_id']
            for kg_id in edge_ids:
                kg_to_qg_ids['edges'][kg_id] = qedge_ids
        return kg_to_qg_ids

    @staticmethod
    def _get_best_equivalent_bte_curie(equivalent_curies: List[str], node_type: str) -> str:
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
        prefixes_in_order_of_preference = preferred_node_prefixes_dict.get(eu.convert_string_to_snake_case(node_type), [])
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
