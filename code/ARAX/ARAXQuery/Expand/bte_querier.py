#!/bin/env python3
import sys
import os
import traceback
import asyncio

from biothings_explorer.user_query_dispatcher import SingleEdgeQueryDispatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge

import Expand.expand_utilities as eu


class BTEQuerier:

    def __init__(self, response_object):
        self.response = response_object
        self.use_synonyms = response_object.data['parameters'].get('use_synonyms')
        self.synonym_handling = response_object.data['parameters'].get('synonym_handling')
        self.enforce_directionality = response_object.data['parameters'].get('enforce_directionality')
        self.continue_if_no_results = response_object.data['parameters'].get('continue_if_no_results')

    def answer_one_hop_query(self, query_graph, qnodes_using_curies_from_prior_step):
        answer_kg = {'nodes': dict(), 'edges': dict()}
        edge_to_nodes_map = dict()
        synonym_usages_dict = dict()
        valid_bte_inputs_dict = self.__get_valid_bte_inputs_dict()
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Validate our input to make sure it will work with BTE
        qedge, input_qnode, output_qnode = self.__validate_and_pre_process_input(query_graph=query_graph,
                                                                                 valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                                 enforce_directionality=self.enforce_directionality)
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Add synonyms to our input query node, if desired
        if self.use_synonyms:
            synonym_usages_dict = eu.add_curie_synonyms_to_query_nodes(qnodes=[input_qnode, output_qnode],
                                                                       log=self.response,
                                                                       override_node_type=False,
                                                                       format_for_bte=True,
                                                                       qnodes_using_curies_from_prior_step=qnodes_using_curies_from_prior_step)
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Use BTE to answer the query
        answer_kg, accepted_curies = self.__answer_query_using_bte(input_qnode=input_qnode,
                                                                   output_qnode=output_qnode,
                                                                   qedge=qedge,
                                                                   answer_kg=answer_kg,
                                                                   valid_bte_inputs_dict=valid_bte_inputs_dict)
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Do any post-processing after ALL curies in the input qnode have been queried
        if eu.qg_is_fulfilled(query_graph, answer_kg) and input_qnode.curie and output_qnode.curie:
            answer_kg = self.__prune_answers_to_achieve_curie_to_curie_query(answer_kg, output_qnode, qedge)
        if eu.qg_is_fulfilled(query_graph, answer_kg) and self.use_synonyms and self.synonym_handling == 'map_back':
            answer_kg = self.__remove_synonym_nodes(answer_kg, input_qnode, output_qnode, qedge, synonym_usages_dict)
            answer_kg = self.__remove_redundant_edges(answer_kg, qedge.id)

        # Report our findings
        if eu.qg_is_fulfilled(query_graph, answer_kg):
            edge_to_nodes_map = self.__create_edge_to_nodes_map(answer_kg, input_qnode.id, output_qnode.id)
            num_results_string = ", ".join([f"{qg_id}: {count}" for qg_id, count in sorted(eu.get_counts_by_qg_id(answer_kg).items())])
            self.response.info(f"Query for edge {qedge.id} returned results ({num_results_string})")
        else:
            self.__log_proper_no_results_message(accepted_curies, self.continue_if_no_results, valid_bte_inputs_dict['curie_prefixes'])

        return answer_kg, edge_to_nodes_map

    def __validate_and_pre_process_input(self, query_graph, valid_bte_inputs_dict, enforce_directionality):
        # Make sure we have a valid one-hop query graph
        if len(query_graph.edges) != 1 or len(query_graph.nodes) != 2:
            self.response.error(f"BTE can only accept one-hop query graphs (your QG has {len(query_graph.nodes)} "
                                f"nodes and {len(query_graph.edges)} edges)", error_code="InvalidQueryGraph")
            return None, None, None
        qedge = query_graph.edges[0]

        # Figure out which query node is input vs. output and validate which qnodes have curies
        if enforce_directionality:
            input_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.source_id)
            output_qnode = next(qnode for qnode in query_graph.nodes if qnode.id == qedge.target_id)
        else:
            qnodes_with_curies = [qnode for qnode in query_graph.nodes if qnode.curie]
            input_qnode = qnodes_with_curies[0] if qnodes_with_curies else None
            output_qnode = next(qnode for qnode in query_graph.nodes if qnode.id != input_qnode.id)

        if not input_qnode.curie:
            self.response.error(f"BTE cannot expand edges with a non-specific (curie-less) source node (source node is:"
                                f" {input_qnode.to_dict()})", error_code="InvalidInput")
        elif not enforce_directionality:
            self.response.warning(f"BTE cannot do bidirectional queries; the query for this edge will be directed, "
                                  f"going: {input_qnode.id}-->{output_qnode.id}")
        if self.response.status != 'OK':
            return None, None, None

        # Make sure predicate is allowed
        if qedge.type not in valid_bte_inputs_dict['predicates'] and qedge.type is not None:
            self.response.error(f"BTE does not accept predicate '{qedge.type}'. Valid options are "
                                f"{valid_bte_inputs_dict['predicates']}", error_code="InvalidInput")
            return None, None, None

        # Convert node types to preferred format and check if they're allowed
        input_qnode.type = eu.convert_string_to_pascal_case(input_qnode.type)
        output_qnode.type = eu.convert_string_to_pascal_case(output_qnode.type)
        qnodes_missing_type = [qnode.id for qnode in [input_qnode, output_qnode] if not qnode.type]
        if qnodes_missing_type:
            self.response.error(f"BTE requires every query node to have a type. QNode(s) missing a type: "
                                f"{', '.join(qnodes_missing_type)}", error_code="InvalidInput")
            return None, None, None
        invalid_qnode_types = [qnode.type for qnode in [input_qnode, output_qnode] if qnode.type not in valid_bte_inputs_dict['node_types']]
        if invalid_qnode_types:
            self.response.error(f"BTE does not accept QNode type(s): {', '.join(invalid_qnode_types)}. Valid options are"
                                f" {valid_bte_inputs_dict['node_types']}", error_code="InvalidInput")
            return None, None, None

        # Make sure our input node curies are in list form and use prefixes BTE prefers
        input_qnode.curie = eu.convert_string_or_list_to_list(input_qnode.curie)
        input_qnode.curie = [eu.convert_curie_to_bte_format(curie) for curie in input_qnode.curie]

        return qedge, input_qnode, output_qnode

    def __answer_query_using_bte(self, input_qnode, output_qnode, qedge, answer_kg, valid_bte_inputs_dict):
        accepted_curies = set()
        # Send this single-edge query to BTE, once per input curie (adding findings to our answer KG as we go)
        for curie in input_qnode.curie:
            if eu.get_curie_prefix(curie) in valid_bte_inputs_dict['curie_prefixes']:
                accepted_curies.add(curie)
                try:
                    loop = asyncio.new_event_loop()
                    seqd = SingleEdgeQueryDispatcher(input_cls=input_qnode.type,
                                                     output_cls=output_qnode.type,
                                                     pred=qedge.type,
                                                     input_id=eu.get_curie_prefix(curie),
                                                     values=eu.get_curie_local_id(curie),
                                                     loop=loop)
                    self.response.debug(f"Sending query to BTE: {curie}-{qedge.type if qedge.type else ''}->{output_qnode.type}")
                    seqd.query()
                    reasoner_std_response = seqd.to_reasoner_std()
                except:
                    trace_back = traceback.format_exc()
                    error_type, error, _ = sys.exc_info()
                    self.response.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                        error_code=error_type.__name__)
                    return answer_kg, accepted_curies
                else:
                    answer_kg = self.__add_answers_to_kg(answer_kg, reasoner_std_response, input_qnode.id, output_qnode.id, qedge.id)

        return answer_kg, accepted_curies

    def __add_answers_to_kg(self, answer_kg, reasoner_std_response, input_qnode_id, output_qnode_id, qedge_id):
        kg_to_qg_ids_dict = self.__build_kg_to_qg_id_dict(reasoner_std_response['results'])
        if reasoner_std_response['knowledge_graph']['edges']:
            remapped_node_ids = dict()
            self.response.debug(f"Got results back from BTE for this query "
                                f"({len(reasoner_std_response['knowledge_graph']['edges'])} edges)")
            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                bte_node_id = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.type = eu.convert_string_to_snake_case(node.get('type'))

                # Map the returned BTE qg_ids back to the original qnode_ids in our query graph
                bte_qg_id = kg_to_qg_ids_dict['nodes'].get(bte_node_id)
                if bte_qg_id == "n0":
                    qnode_id = input_qnode_id
                elif bte_qg_id == "n1":
                    qnode_id = output_qnode_id
                else:
                    self.response.error("Could not map BTE qg_id to ARAX qnode_id", error_code="UnknownQGID")
                    return answer_kg

                # Find and use the preferred equivalent identifier for this node (if it's an 'output' node)
                if qnode_id == output_qnode_id:
                    if bte_node_id in remapped_node_ids:
                        swagger_node.id = remapped_node_ids.get(bte_node_id)
                    else:
                        equivalent_curies = [f"{prefix}:{eu.get_curie_local_id(local_id)}" for prefix, local_ids in
                                             node.get('equivalent_identifiers').items() for local_id in local_ids]
                        swagger_node.id = eu.get_best_equivalent_curie(equivalent_curies, swagger_node.type)
                        remapped_node_ids[bte_node_id] = swagger_node.id
                else:
                    swagger_node.id = bte_node_id

                eu.add_node_to_kg(answer_kg, swagger_node, qnode_id)

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
                    self.response.error("Could not map BTE qg_id to ARAX qedge_id", error_code="UnknownQGID")
                    return answer_kg
                eu.add_edge_to_kg(answer_kg, swagger_edge, qedge_id)
        return answer_kg

    def __log_proper_no_results_message(self, accepted_curies, continue_if_no_results, valid_prefixes):
        if continue_if_no_results:
            if not accepted_curies:
                self.response.warning(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are:"
                                      f" {valid_prefixes}")
            self.response.warning(f"No paths were found in BTE satisfying this query graph")
        else:
            if not accepted_curies:
                self.response.error(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are: "
                                    f"{valid_prefixes}", error_code="InvalidPrefix")
            self.response.error(f"No paths were found in BTE satisfying this query graph", error_code="NoResults")

    @staticmethod
    def __remove_synonym_nodes(kg, input_qnode, output_qnode, qedge, synonym_usages_dict):
        for qnode_id, synonym_usage_info in synonym_usages_dict.items():
            ids_of_nodes_in_kg = set(list(kg['nodes'][qnode_id].keys()))

            for original_curie, synonyms_used in synonym_usage_info.items():
                synonyms_used_set = set(synonyms_used).difference({original_curie})
                ids_of_synonym_nodes = synonyms_used_set.intersection(ids_of_nodes_in_kg)

                # Use the original curie if it's present, otherwise pick the best synonym node
                if original_curie in ids_of_nodes_in_kg:
                    node_id_to_keep = original_curie
                    node_ids_to_remove = ids_of_synonym_nodes
                else:
                    qnode_type = input_qnode.type if qnode_id == input_qnode.id else output_qnode.type
                    node_id_to_keep = eu.get_best_equivalent_curie(list(ids_of_synonym_nodes), qnode_type)
                    node_ids_to_remove = ids_of_synonym_nodes.difference({node_id_to_keep})

                # Remove the nodes don't want
                for node_id in node_ids_to_remove:
                    kg['nodes'][qnode_id].pop(node_id)

                # And remap their edges to point to the node we kept
                for edge in kg['edges'][qedge.id].values():
                    if edge.source_id in node_ids_to_remove:
                        edge.source_id = node_id_to_keep
                    if edge.target_id in node_ids_to_remove:
                        edge.target_id = node_id_to_keep
        return kg

    @staticmethod
    def __remove_redundant_edges(kg, qedge_id):
        # Figure out which edges are redundant (can happen due to synonym remapping)
        edges_already_seen = set()
        edge_ids_to_remove = set()
        for edge_id, edge in kg['edges'][qedge_id].items():
            identifier_tuple_for_edge = (edge.source_id, edge.type, edge.target_id, edge.provided_by)
            if identifier_tuple_for_edge in edges_already_seen:
                edge_ids_to_remove.add(edge_id)
            else:
                edges_already_seen.add(identifier_tuple_for_edge)

        # Then remove them
        for edge_id in edge_ids_to_remove:
            kg['edges'][qedge_id].pop(edge_id)

        return kg

    @staticmethod
    def __prune_answers_to_achieve_curie_to_curie_query(kg, output_qnode, qedge):
        """
        This is a way of hacking around BTE's limitation where it can only do (node with curie)-->(non-specific node)
        kinds of queries. We do the non-specific query, and then use this function to remove all of the answer nodes
        that do not correspond to the curie we wanted for the 'output' node.
        """
        # Remove 'output' nodes in the KG that aren't actually the ones we were looking for
        desired_output_curies = set(eu.convert_string_or_list_to_list(output_qnode.curie))
        all_output_node_ids = set(list(kg['nodes'][output_qnode.id].keys()))
        output_node_ids_to_remove = all_output_node_ids.difference(desired_output_curies)
        for node_id in output_node_ids_to_remove:
            kg['nodes'][output_qnode.id].pop(node_id)

        # And remove any edges that used them
        edge_ids_to_remove = set()
        for edge_id, edge in kg['edges'][qedge.id].items():
            if edge.target_id in output_node_ids_to_remove:  # Edge target_id always contains output node ID for BTE
                edge_ids_to_remove.add(edge_id)
        for edge_id in edge_ids_to_remove:
            kg['edges'][qedge.id].pop(edge_id)

        return kg

    @staticmethod
    def __create_edge_to_nodes_map(answer_kg, input_qnode_id, output_qnode_id):
        edge_to_nodes_map = dict()
        for qedge_id, edges in answer_kg['edges'].items():
            for edge_key, edge in edges.items():
                # BTE single-edge queries are always directed (meaning, edge.source_id == input qnode ID)
                edge_to_nodes_map[edge.id] = {input_qnode_id: edge.source_id, output_qnode_id: edge.target_id}
        return edge_to_nodes_map

    @staticmethod
    def __get_valid_bte_inputs_dict():
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
    def __build_kg_to_qg_id_dict(results):
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
