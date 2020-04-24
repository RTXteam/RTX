#!/bin/env python3
import sys
import traceback

from biothings_explorer.user_query_dispatcher import SingleEdgeQueryDispatcher


class BTEQuerier:

    def __init__(self, response_object):
        self.response = response_object

    def answer_one_hop_query(self, query_graph):
        final_kg = {'nodes': dict(), 'edges': dict()}
        edge = query_graph.edges[0]
        source_node = next(node for node in query_graph.nodes if node.id == edge.source_id)
        target_node = next(node for node in query_graph.nodes if node.id == edge.target_id)
        try:
            seqd = SingleEdgeQueryDispatcher(input_cls=self.__convert_snake_case_to_pascal_case(source_node.type),
                                             output_cls=self.__convert_snake_case_to_pascal_case(target_node.type),
                                             pred=self.__convert_snake_case_to_camel_case(edge.type),
                                             input_id=self.__get_curie_prefix(source_node.curie).lower(),
                                             values=self.__get_curie_local_id(source_node.curie))
            seqd.query()
            reasoner_std_response = seqd.to_reasoner_std()
        except:
            trace_back = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                error_code=error_type.__name__)
        else:
            final_kg = self.__convert_answers_to_kg(reasoner_std_response)
        return final_kg

    def __convert_answers_to_kg(self, reasoner_std_response):
        final_kg = {'nodes': dict(), 'edges': dict()}
        # TODO: Create swagger model objects for nodes/edges and annotate with their QG IDs
        return final_kg

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

    def __get_curie_prefix(self, curie):
        prefix = curie.split(':')[0]
        if prefix == "CHEMBL.COMPOUND":
            prefix = "CHEMBL"
        return prefix

    def __get_curie_local_id(self, curie):
        return curie.split(':')[1]
