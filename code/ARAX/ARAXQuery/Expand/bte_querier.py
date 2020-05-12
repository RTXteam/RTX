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

    def answer_one_hop_query(self, query_graph):
        qedge = query_graph.edges[0]
        input_qnode = next(node for node in query_graph.nodes if node.curie)
        output_qnode = next(node for node in query_graph.nodes if node.id != input_qnode.id)
        input_node_curies = input_qnode.curie if type(input_qnode.curie) is list else [input_qnode.curie]
        for input_node_curie in input_node_curies:
            try:
                seqd = SingleEdgeQueryDispatcher(input_cls=self.__convert_snake_case_to_pascal_case(input_qnode.type),
                                                 output_cls=self.__convert_snake_case_to_pascal_case(output_qnode.type),
                                                 pred=qedge.type,
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
                self.__add_answers_to_kg(reasoner_std_response, input_qnode.id, output_qnode.id, qedge.id)

        if self.final_kg['edges']:
            counts_by_qg_id = self.__get_counts_by_qg_id(self.final_kg)
            num_results_string = ", ".join([f"{qg_id}: {count}" for qg_id, count in sorted(counts_by_qg_id.items())])
            self.response.info(f"Query for edge {qedge.id} returned results ({num_results_string})")
        else:
            if self.continue_if_no_results:
                self.response.warning(f"No paths were found in BTE satisfying this query graph")
            else:
                self.response.error(f"No paths were found in BTE satisfying this query graph. BTE log: {''.join(seqd.log)}", error_code="NoResults")
        return self.final_kg

    def __add_answers_to_kg(self, reasoner_std_response, input_qnode_id, output_qnode_id, qedge_id):
        kg_to_qg_ids_dict = self.__build_kg_to_qg_id_dict(reasoner_std_response['results'])
        if reasoner_std_response['knowledge_graph']['edges']:  # Note: BTE response currently includes some nodes even when no edges found
            for node in reasoner_std_response['knowledge_graph']['nodes']:
                swagger_node = Node()
                swagger_node.id = node.get('id')
                swagger_node.name = node.get('name')
                swagger_node.type = node.get('type')
                # Map the returned BTE qg_ids back to the original qnode_ids in our query graph
                bte_qg_id = kg_to_qg_ids_dict['nodes'].get(swagger_node.id)
                if bte_qg_id == "n0":
                    swagger_node.qnode_id = input_qnode_id
                elif bte_qg_id == "n1":
                    swagger_node.qnode_id = output_qnode_id
                else:
                    self.response.error("Could not map BTE qg_id to ARAX qnode_id", error_code="UnknownQGID")
                self.final_kg['nodes'][swagger_node.id] = swagger_node
            for edge in reasoner_std_response['knowledge_graph']['edges']:
                swagger_edge = Edge()
                swagger_edge.id = edge.get("id")
                swagger_edge.type = edge.get('type')
                swagger_edge.source_id = edge.get('source_id')
                swagger_edge.target_id = edge.get('target_id')
                swagger_edge.is_defined_by = "BTE"
                swagger_edge.provided_by = edge.get('edge_source')
                # Map the returned BTE qg_id back to the original qedge_id in our query graph
                bte_qg_id = kg_to_qg_ids_dict['edges'].get(swagger_edge.id)
                if bte_qg_id == "e1":
                    swagger_edge.qedge_id = qedge_id
                else:
                    self.response.error("Could not map BTE qg_id to ARAX qedge_id", error_code="UnknownQGID")
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

    def __build_kg_to_qg_id_dict(self, results):
        kg_to_qg_ids = {'nodes': dict(), 'edges': dict()}
        for node_binding in results['node_bindings']:
            node_id = node_binding['kg_id']
            qnode_id = node_binding['qg_id']
            if node_id in kg_to_qg_ids['nodes'] and kg_to_qg_ids['nodes'][node_id] != qnode_id:
                self.response.error(f"Node {node_id} has been returned as an answer for multiple query graph nodes"
                                    f" ({kg_to_qg_ids['nodes'][node_id]} and {qnode_id})", error_code="MultipleQGIDs")
            kg_to_qg_ids['nodes'][node_id] = qnode_id
        for edge_binding in results['edge_bindings']:
            edge_ids = edge_binding['kg_id'] if type(edge_binding['kg_id']) is list else [edge_binding['kg_id']]
            qedge_ids = edge_binding['qg_id']
            for kg_id in edge_ids:
                kg_to_qg_ids['edges'][kg_id] = qedge_ids
        return kg_to_qg_ids

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
        if prefix == "CUI":
            prefix = "UMLS"
        elif prefix == "SNOMEDCT":
            prefix = "SNOMED"
        return prefix

    def __get_curie_local_id(self, curie):
        return curie.split(':')[-1]  # Note: Taking last item gets around "PR:PR:000001" situation
