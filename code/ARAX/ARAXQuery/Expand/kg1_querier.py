#!/bin/env python3
import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from QueryGraphReasoner import QueryGraphReasoner


class KG1Querier:

    def __init__(self, response_object):
        self.response = response_object

    def answer_query(self, query_graph):
        """
        This function answers a query using KG1 (currently via the QueryGraphReasoner).
        :param query_graph: A query graph, in Translator API format.
        :return: A knowledge graph containing the answers to the queries.
        """
        answer_message = None

        try:
            QGR = QueryGraphReasoner()
            answer_message = QGR.answer(query_graph.to_dict(), TxltrApiFormat=True)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"QueryGraphReasoner encountered an error. {tb}", error_code=error_type.__name__)
        else:
            # Convert our answer knowledge graph into dictionary format (for faster processing)
            dict_answer_kg = self.__convert_standard_kg_to_dict_kg(answer_message.knowledge_graph)
            answer_message.knowledge_graph = dict_answer_kg

            if not answer_message.results:
                self.response.warning(f"No paths were found in KG1 satisfying this query graph")
            else:
                answer_kg = answer_message.knowledge_graph
                self.response.info(
                    f"QueryGraphReasoner returned {len(answer_message.results)} results "
                    f"({len(answer_kg['nodes'])} nodes, {len(answer_kg['edges'])} edges)")

                # Add corresponding query graph IDs to our answer KG based on info given in the 'results'
                self.__add_query_ids_to_answer_kg(answer_message)

        return answer_message.knowledge_graph

    def __add_query_ids_to_answer_kg(self, answer_message):
        """
        This function attaches corresponding query edge/node IDs to each edge/node in an answer knowledge graph. These
        IDs indicate which node/edge in the query graph the given node/edge maps to.
        :param answer_message: An answer 'message', in Translator API format.
        :return: None
        """
        answer_nodes = answer_message.knowledge_graph.get('nodes')
        answer_edges = answer_message.knowledge_graph.get('edges')
        query_id_map = self.__build_query_id_map(answer_message.results)

        for node_key, node in answer_nodes.items():
            # Tack this node's corresponding query node ID onto it
            node.qnode_id = query_id_map['nodes'].get(node_key)
            if node.qnode_id is None:
                self.response.warning(f"Node {node_key} is missing a qnode_id")

        for edge_key, edge in answer_edges.items():
            # Tack this edge's corresponding query edge ID onto it (needed for later processing)
            edge.qedge_id = query_id_map['edges'].get(edge_key)
            if edge.qedge_id is None:
                self.response.warning(f"Edge {edge_key} is missing a qedge_id")

    def __build_query_id_map(self, results):
        """
        This is a helper function that creates a dictionary mapping each edge/node in a query's results to the
        qedge/qnode it corresponds to in the query graph that produced those results.
        :param results: The 'results' of a query, in Translator API format.
        :return: A dictionary
        """
        query_id_map = {'edges': dict(), 'nodes': dict()}

        for result in results:
            for edge_binding in result.edge_bindings:
                for edge_id in edge_binding['kg_id']:
                    qedge_id = edge_binding['qg_id']
                    query_id_map['edges'][edge_id] = qedge_id

            for node_binding in result.node_bindings:
                node_id = node_binding['kg_id']
                qnode_id = node_binding['qg_id']
                query_id_map['nodes'][node_id] = qnode_id

        # TODO: Allow multiple query graph IDs per node/edge?
        return query_id_map

    def __convert_standard_kg_to_dict_kg(self, knowledge_graph):
        dict_kg = dict()
        dict_kg['nodes'] = dict()
        dict_kg['edges'] = dict()
        for node in knowledge_graph.nodes:
            dict_kg['nodes'][node.id] = node
        for edge in knowledge_graph.edges:
            dict_kg['edges'][edge.id] = edge
        return dict_kg