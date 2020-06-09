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

    def answer_one_hop_query(self, query_graph, qnodes_using_curies_from_prior_step):
        answer_kg = {'nodes': dict(), 'edges': dict()}
        edge_to_nodes_map = dict()
        enforce_directionality = self.response.data['parameters'].get('enforce_directionality')

        # Format and validate input for BTE
        valid_bte_inputs_dict = self.__get_valid_bte_inputs_dict()
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map
        qedge, input_qnode, output_qnode = self.__validate_and_pre_process_input(query_graph=query_graph,
                                                                                 valid_bte_inputs_dict=valid_bte_inputs_dict,
                                                                                 enforce_directionality=enforce_directionality)
        if self.response.status != 'OK':
            return answer_kg, edge_to_nodes_map

        # Send this single-edge query to BTE, once per input curie (adding findings to our answer KG as we go)
        accepted_curies = set()
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
                    return answer_kg, edge_to_nodes_map
                else:
                    self.__add_answers_to_kg(answer_kg, reasoner_std_response, input_qnode.id, output_qnode.id, qedge.id)

        # Report our findings
        if answer_kg['edges']:
            edge_to_nodes_map = self.__create_edge_to_nodes_map(answer_kg, input_qnode.id, output_qnode.id)
            counts_by_qg_id = eu.get_counts_by_qg_id(answer_kg)
            num_results_string = ", ".join([f"{qg_id}: {count}" for qg_id, count in sorted(counts_by_qg_id.items())])
            self.response.info(f"Query for edge {qedge.id} returned results ({num_results_string})")
        elif self.response.data['parameters']['continue_if_no_results']:
            if not accepted_curies:
                self.response.warning(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE "
                                      f"are: {valid_bte_inputs_dict['curie_prefixes']}")
            self.response.warning(f"No paths were found in BTE satisfying this query graph")
        else:
            if not accepted_curies:
                self.response.error(f"BTE could not accept any of the input curies. Valid curie prefixes for BTE are: "
                                    f"{valid_bte_inputs_dict['curie_prefixes']}", error_code="InvalidPrefix")
            self.response.error(f"No paths were found in BTE satisfying this query graph", error_code="NoResults")

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
        elif input_qnode.curie and output_qnode.curie:
            self.response.error(f"BTE cannot expand edges for which both nodes have a curie specified (for now)",
                                error_code="InvalidInput")
            # TODO: Hack around this limitation to allow curie--curie queries
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
        pre_processed_curies = [self.__convert_curie_to_bte_format(curie) for curie in input_qnode.curie]
        input_qnode.curie = pre_processed_curies

        return qedge, input_qnode, output_qnode

    def __add_answers_to_kg(self, answer_kg, reasoner_std_response, input_qnode_id, output_qnode_id, qedge_id):
        kg_to_qg_ids_dict = self.__build_kg_to_qg_id_dict(reasoner_std_response['results'])
        remapped_node_ids = dict()
        if reasoner_std_response['knowledge_graph']['edges']:
            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                original_node_id = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.type = eu.convert_string_to_snake_case(node.get('type'))

                # Map the returned BTE qg_ids back to the original qnode_ids in our query graph
                bte_qg_id = kg_to_qg_ids_dict['nodes'].get(original_node_id)
                if bte_qg_id == "n0":
                    qnode_id = input_qnode_id
                elif bte_qg_id == "n1":
                    qnode_id = output_qnode_id
                else:
                    self.response.error("Could not map BTE qg_id to ARAX qnode_id", error_code="UnknownQGID")
                    return answer_kg

                # Find and use the preferred equivalent identifier for this node
                if original_node_id in remapped_node_ids:
                    swagger_node.id = remapped_node_ids.get(original_node_id)
                else:
                    swagger_node.id = self.__get_preferred_equivalent_identifier(node)
                    remapped_node_ids[original_node_id] = swagger_node.id

                eu.add_node_to_kg(answer_kg, swagger_node, qnode_id)

            for edge in reasoner_std_response['knowledge_graph']['edges']:
                swagger_edge = Edge()
                swagger_edge.id = edge.get("id")
                swagger_edge.type = edge.get('type')
                swagger_edge.source_id = remapped_node_ids.get(edge.get('source_id'))
                swagger_edge.target_id = remapped_node_ids.get(edge.get('target_id'))
                swagger_edge.is_defined_by = "BTE"
                swagger_edge.provided_by = edge.get('edge_source')
                # Map the returned BTE qg_id back to the original qedge_id in our query graph
                bte_qg_id = kg_to_qg_ids_dict['edges'].get(swagger_edge.id)
                if bte_qg_id != "e1":
                    self.response.error("Could not map BTE qg_id to ARAX qedge_id", error_code="UnknownQGID")
                    return answer_kg
                eu.add_edge_to_kg(answer_kg, swagger_edge, qedge_id)
        return answer_kg

    def __get_preferred_equivalent_identifier(self, bte_node):
        preferred_prefixes_for_this_node_type = eu.get_preferred_prefix_for_node_type(bte_node.get('type'))
        equivalent_prefixes = {prefix.upper(): local_ids for prefix, local_ids in bte_node.get('equivalent_identifiers').items()}
        prefix_case_map = {prefix.upper(): prefix for prefix in bte_node.get('equivalent_identifiers')}

        # Use the equivalent identifier with a prefix earliest in our list of preferred prefixes if possible
        for prefix in preferred_prefixes_for_this_node_type:
            if prefix in equivalent_prefixes:
                return prefix_case_map.get(prefix) + ':' + equivalent_prefixes[prefix][0]

        # Otherwise, just try to use one with a prefix other than 'name' (a sort of pseudo prefix BTE uses internally)
        non_name_prefixes = [prefix for prefix in equivalent_prefixes if prefix != 'NAME']
        if non_name_prefixes:
            prefix = non_name_prefixes[0]
            return prefix_case_map.get(prefix) + ':' + equivalent_prefixes[prefix][0]
        else:
            self.response.warning(f"BTE returned a node with no identifier other than {bte_node.get('id')}")
            return bte_node.get('id')

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

    @staticmethod
    def __convert_curie_to_bte_format(curie):
        prefix = eu.get_curie_prefix(curie)
        local_id = eu.get_curie_local_id(curie)
        if prefix == "CUI":
            prefix = "UMLS"
        return prefix + ':' + local_id
