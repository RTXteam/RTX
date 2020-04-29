#!/bin/env python3
import sys
import os
import traceback

from biothings_explorer.user_query_dispatcher import SingleEdgeQueryDispatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.edge_attribute import EdgeAttribute


class BTEQuerier:

    def __init__(self, response_object):
        self.response = response_object
        self.final_kg = {'nodes': dict(), 'edges': dict()}
        self.continue_if_no_results = self.response.data['parameters']['continue_if_no_results']
        self.allowed_input_curie_prefixes = ['zfin', 'umls', 'cl', 'efo', 'entrez', 'chebi', 'fbbt', 'hgnc', 'uniprot',
                                             'mgi', 'mesh', 'doid', 'mop', 'pombase', 'rgd', 'orphanet', 'omim',
                                             'wikipathways', 'tair', 'dictybase', 'mp', 'drugbank', 'reactome',
                                             'pathwayFigureID', 'uberon', 'symbol', 'sgd', 'so', 'mondo', 'go',
                                             'chembl', 'hp', 'pr', 'snomed', 'samd', 'ensembl', 'dbsnp', 'clo', 'flybase']

    def answer_one_hop_query(self, query_graph):
        edge = query_graph.edges[0]
        input_node = next(node for node in query_graph.nodes if node.curie)
        output_node = next(node for node in query_graph.nodes if node.id != input_node.id)
        input_node_curies = input_node.curie if type(input_node.curie) is list else [input_node.curie]  # Make sure these are in list form
        for input_node_curie in input_node_curies:
            if self.__get_curie_prefix_for_bte(input_node_curie) in self.allowed_input_curie_prefixes:
                try:
                    seqd = SingleEdgeQueryDispatcher(input_cls=self.__convert_snake_case_to_pascal_case(input_node.type),
                                                     output_cls=self.__convert_snake_case_to_pascal_case(output_node.type),
                                                     pred=self.__convert_snake_case_to_camel_case(edge.type),
                                                     input_id=self.__get_curie_prefix_for_bte(input_node_curie),
                                                     values=self.__get_curie_local_id(input_node_curie))
                    seqd.query()
                    reasoner_std_response = seqd.to_reasoner_std()
                except:
                    trace_back = traceback.format_exc()
                    error_type, error, _ = sys.exc_info()
                    self.response.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                        error_code=error_type.__name__)
                    return self.final_kg
                else:
                    self.__add_answers_to_kg(reasoner_std_response, input_node.id, output_node.id, edge.id)

        if self.final_kg['edges']:
            counts_by_qg_id = self.__get_counts_by_qg_id(self.final_kg)
            num_results_string = ", ".join([f"{qg_id}: {count}" for qg_id, count in sorted(counts_by_qg_id.items())])
            self.response.info(f"Query for edge {edge.id} returned results ({num_results_string})")
        else:
            if self.continue_if_no_results:
                self.response.warning(f"No paths were found in BTE satisfying this query graph")
            else:
                self.response.error(f"No paths were found in BTE satisfying this query graph", error_code="NoResults")
        return self.final_kg

    def __add_answers_to_kg(self, reasoner_std_response, input_qnode_id, output_qnode_id, qedge_id):
        if reasoner_std_response['knowledge_graph']['edges']:  # Note: BTE response currently includes some nodes even when no edges found
            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                swagger_node.id = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.type = node.get('type')
                # All nodes except our input node should have a qnode_id corresponding to the output node
                input_node_in_bte_qg = next(node for node in reasoner_std_response['query_graph']['nodes'] if node['id'] == "n0")
                if swagger_node.id == input_node_in_bte_qg['curie'][0].upper():  # Hack to get around different formats of same curie in QG vs. KG
                    swagger_node.qnode_id = input_qnode_id
                else:
                    swagger_node.qnode_id = output_qnode_id
                self.final_kg['nodes'][swagger_node.id] = swagger_node
            for edge in reasoner_std_response['knowledge_graph']['edges']:
                swagger_edge = Edge()
                swagger_edge.type = edge.get('type')
                swagger_edge.source_id = edge.get('source_id')
                swagger_edge.target_id = edge.get('target_id')
                swagger_edge.id = f"{swagger_edge.source_id}--{swagger_edge.type}--{swagger_edge.target_id}"
                swagger_edge.is_defined_by = "BTE"
                swagger_edge.provided_by = edge.get('edge_source')
                swagger_edge.qedge_id = qedge_id
                self.final_kg['edges'][swagger_edge.id] = swagger_edge

    def __get_counts_by_qg_id(self, knowledge_graph):
        counts_by_qg_id = dict()
        for node in knowledge_graph['nodes'].values():
            if node.qnode_id not in counts_by_qg_id:
                counts_by_qg_id[node.qnode_id] = 0
            counts_by_qg_id[node.qnode_id] += 1
        for edge in knowledge_graph['edges'].values():
            if edge.qedge_id not in counts_by_qg_id:
                counts_by_qg_id[edge.qedge_id] = 0
            counts_by_qg_id[edge.qedge_id] += 1
        return counts_by_qg_id

    def __convert_snake_case_to_pascal_case(self, snake_string):
        # Converts a string like 'chemical_substance' to 'ChemicalSubstance'
        if snake_string:
            words = snake_string.split('_')
            return "".join([word.capitalize() for word in words])
        else:
            return ""

    def __convert_snake_case_to_camel_case(self, snake_string):
        # Converts a string like 'chemical_substance' to 'chemicalSubstance'
        if snake_string:
            words = snake_string.split('_')
            return "".join([words[0]] + [word.capitalize() for word in words[1:]])
        else:
            return ""

    def __get_curie_prefix_for_bte(self, curie):
        prefix = curie.split(':')[0]
        # Note: Make some temporary prefix adjustments (until prefixes are standardized somehow?)
        if prefix.startswith("CHEMBL"):
            prefix = "CHEMBL"
        elif prefix == "NCBIGene":
            prefix = "ENTREZ"
        elif prefix.startswith("UniProtKB"):
            prefix = "UniProt"
        elif prefix == "CUI":
            prefix = "UMLS"
        elif prefix == "SNOMEDCT":
            prefix = "SNOMED"
        return prefix.lower()

    def __get_curie_local_id(self, curie):
        return curie.split(':')[-1]  # Note: Taking last item gets around "PR:PR:000001" situation
