#!/bin/env python3
import sys
import os
import traceback

from biothings_explorer.user_query_dispatcher import SingleEdgeQueryDispatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge


class BTEQuerier:

    def __init__(self, response_object):
        self.response = response_object
        self.final_kg = {'nodes': dict(), 'edges': dict()}

    def answer_one_hop_query(self, query_graph):
        edge = query_graph.edges[0]
        input_node = next(node for node in query_graph.nodes if node.curie)
        output_node = next(node for node in query_graph.nodes if node.id != input_node.id)
        input_node_curies = input_node.curie if type(input_node.curie) is list else [input_node.curie]  # Make sure these are in list form
        for input_node_curie in input_node_curies:
            try:
                seqd = SingleEdgeQueryDispatcher(input_cls=self.__convert_snake_case_to_pascal_case(input_node.type),
                                                 output_cls=self.__convert_snake_case_to_pascal_case(output_node.type),
                                                 pred=self.__convert_snake_case_to_camel_case(edge.type),
                                                 input_id=self.__get_curie_prefix(input_node_curie).lower(),
                                                 values=self.__get_curie_local_id(input_node_curie))
                seqd.query()
                reasoner_std_response = seqd.to_reasoner_std()
            except:
                trace_back = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(f"Encountered a problem while using BioThings Explorer. {trace_back}",
                                    error_code=error_type.__name__)
                break
            else:
                print(reasoner_std_response['knowledge_graph'])
                query_graph_ids_map = self.__build_query_graph_ids_map(reasoner_std_response, input_node, output_node, edge)
                self.__add_answers_to_kg(reasoner_std_response, query_graph_ids_map)

        return self.final_kg

    def __add_answers_to_kg(self, reasoner_std_response, query_graph_ids_map):
        for node in reasoner_std_response['knowledge_graph']['nodes']:
            swagger_node = Node(id=node['id'], name=node['name'])
            swagger_node.qnode_id = query_graph_ids_map['nodes'].get(swagger_node.id)
            self.final_kg['nodes'][swagger_node.id] = swagger_node
        for edge in reasoner_std_response['knowledge_graph']['edges']:
            swagger_edge = Edge(id=edge['id'], type=edge['type'], source_id=edge['source_id'], target_id=edge['target_id'])
            swagger_edge.qedge_id = query_graph_ids_map['edges'].get(swagger_edge.id)
            self.final_kg['edges'][swagger_edge.id] = swagger_edge
        self.response.info(f"Found results using BTE (nodes: {len(self.final_kg['nodes'])}, edges: {len(self.final_kg['edges'])})")

    def __build_query_graph_ids_map(self, reasoner_std_response, input_node, output_node, edge):
        query_graph_ids_map = {'nodes': dict(), 'edges': dict()}
        for node_binding in reasoner_std_response['results']['node_bindings']:
            node_id = node_binding['kg_id']
            qnode_id = output_node.id
            if node_id in query_graph_ids_map['nodes'] and query_graph_ids_map['nodes'].get(node_id) != qnode_id:
                self.response.error(f"Node {node_id} has been returned as an answer for multiple query graph nodes"
                                    f" ({query_graph_ids_map['nodes'].get(node_id)} and {qnode_id})",
                                    error_code="MultipleQGIDs")
            else:
                query_graph_ids_map['nodes'][node_id] = qnode_id
        for edge_binding in reasoner_std_response['results']['edge_bindings']:
            edge_id = edge_binding['kg_id'][0]  # TODO: loop through all...
            qedge_id = edge.id
            if edge_id in query_graph_ids_map['edges'] and query_graph_ids_map['edges'].get(edge_id) != qedge_id:
                self.response.error(f"Edge {edge_id} has been returned as an answer for multiple query graph edges"
                                    f" ({query_graph_ids_map['edges'].get(edge_id)} and {qedge_id})", error_code="MultipleQGIDs")
            else:
                query_graph_ids_map['edges'][edge_id] = qedge_id

        # Attach query graph ID to input node (doesn't currently appear in BTE's node bindings)
        for node in reasoner_std_response['knowledge_graph']['nodes']:
            if node['id'] not in query_graph_ids_map['nodes']:
                query_graph_ids_map['nodes'][node['id']] = input_node.id

        return query_graph_ids_map

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
