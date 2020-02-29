#!/bin/env python3
import sys
import os
import traceback

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
import ReasoningUtilities as RU
from QueryGraphReasoner import QueryGraphReasoner
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge


class KG2Querier:

    def __init__(self, response_object):
        self.response = response_object
        self.cypher_query_to_get_results = None
        self.cypher_query_to_get_kg = None
        self.answer_results = None
        self.answer_kg = None
        self.final_kg = {'nodes': dict(), 'edges': dict()}

    def answer_query(self, query_graph):
        """
        This function answers a query using KG2.
        :param query_graph: A query graph, in Translator API standard format.
        :return: A knowledge graph containing the answers to the queries.
        """
        self.__generate_cypher_to_run(query_graph)
        if not self.response.status == 'OK':
            return self.final_kg

        self.__run_cypher_in_neo4j()
        if not self.response.status == 'OK':
            return self.final_kg

        self.__build_final_kg_of_answers()
        if not self.response.status == 'OK':
            return self.final_kg

        return self.final_kg

    def __generate_cypher_to_run(self, query_graph):
        self.response.debug("Generating cypher based on query graph sent to KG2Querier")
        try:
            # First pre-process the query graph to get it ready to generate cypher from
            QGR = QueryGraphReasoner()
            processed_query_graph, sort_flags, res_limit, ascending_flag = QGR.preprocess_query_graph(query_graph.to_dict())

            # Then actually generate the corresponding cypher
            cypher_generator = RU.get_cypher_from_question_graph({'question_graph': processed_query_graph})
            self.cypher_query_to_get_results = cypher_generator.cypher_query_answer_map()
            self.cypher_query_to_get_kg = cypher_generator.cypher_query_knowledge_graph()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)

    def __run_cypher_in_neo4j(self):
        self.response.debug("Sending cypher query to KG2 neo4j")
        try:
            rtxConfig = RTXConfiguration()
            rtxConfig.live="KG2"
            driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
            with driver.session() as session:
                self.answer_results = session.run(self.cypher_query_to_get_results).data()
                self.answer_kg = session.run(self.cypher_query_to_get_kg).data()
            driver.close()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered an error interacting with KG2 neo4j. {tb}",
                                error_code=error_type.__name__)
        else:
            if len(self.answer_kg) == 0:
                self.response.warning("No paths were found in KG2 satisfying this query graph")
                self.answer_kg = {'nodes': dict(), 'edges': dict()}
            else:
                self.answer_kg = self.answer_kg[0]  # The answer knowledge graph is returned from neo4j in a list
                self.response.info(f"Query returned {len(self.answer_kg.get('nodes'))} nodes "
                                   f"and {len(self.answer_kg.get('edges'))} edges")

    def __build_final_kg_of_answers(self):
        # Create a map of each node/edge and its corresponding qnode/qedge ID
        query_id_map = self.__create_query_id_map()

        # Create swagger model nodes based on our results and add to final knowledge graph
        for node in self.answer_kg.get('nodes'):
            new_node = Node()
            new_node.id = node.get('id')
            new_node.type = node.get('category_label')
            new_node.description = node.get('description')
            new_node.uri = node.get('iri')

            # Handle different name properties in KG2 vs. KG1
            if new_node.id.startswith("UniProt"):
                new_node.name = node.get('full_name')
                new_node.symbol = node.get('name')
            else:
                new_node.name = node.get('name')

            new_node.qnode_id = query_id_map['nodes'].get(new_node.id)
            if not new_node.qnode_id:
                self.response.warning(f"Node {new_node.id} is missing a qnode_id")

            self.final_kg['nodes'][new_node.id] = new_node

        # Create swagger model edges based on our results and add to final knowledge graph
        for edge in self.answer_kg.get('edges'):
            new_edge = Edge()
            new_edge.id = edge.get('id')
            new_edge.type = edge.get('simplified_edge_label')
            new_edge.relation = edge.get('relation')
            new_edge.source_id = edge.get('subject')
            new_edge.target_id = edge.get('object')
            new_edge.publications = edge.get('publications')
            new_edge.provided_by = edge.get('provided_by')
            new_edge.is_defined_by = "ARAX/KG2"

            new_edge.qedge_id = query_id_map['edges'].get(new_edge.id)
            if not new_edge.qedge_id:
                self.response.warning(f"Edge {new_edge.id} is missing a qedge_id")

            self.final_kg['edges'][new_edge.id] = new_edge

    def __create_query_id_map(self):
        query_id_map = {'nodes': dict(), 'edges': dict()}
        for result in self.answer_results:
            # Map all of the nodes to their qnode IDs
            result_nodes = result.get('nodes')
            for qnode_id, node_curie in result_nodes.items():
                if node_curie not in query_id_map['nodes']:
                    query_id_map['nodes'][node_curie] = qnode_id

            # Map all of the edges to their qedge IDs
            result_edges = result.get('edges')
            for qedge_id, edge_ids in result_edges.items():
                for edge_id in edge_ids:
                    if edge_id not in query_id_map['edges']:
                        query_id_map['edges'][edge_id] = qedge_id

        # TODO: Later adjust for the possibility of the same node/edge having more than one qnode/qedge ID
        return query_id_map
