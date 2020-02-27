#!/bin/env python3
import sys
import os
import traceback

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
import ReasoningUtilities as RU
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


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

        self.response.info(f"KG2Querier found {len(self.final_kg.get('nodes'))} nodes "
                           f"and {len(self.final_kg.get('edges'))} edges for this query")

        return self.final_kg

    def __generate_cypher_to_run(self, query_graph):
        self.response.debug("Generating cypher based on query graph sent to KG2Querier")
        try:
            cypher_generator = RU.get_cypher_from_question_graph({'question_graph': query_graph.to_dict()})
            self.cypher_query_to_get_results = cypher_generator.cypher_query_answer_map()
            self.cypher_query_to_get_kg = cypher_generator.cypher_query_knowledge_graph()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)

    def __run_cypher_in_neo4j(self):
        self.response.debug("Sending cypher query to KG2 neo4j")
        try:
            # TODO: Update config file and use rtxConfig.live="KG2" so that we actually use KG2!
            rtxConfig = RTXConfiguration()
            driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
            with driver.session() as session:
                self.answer_results = session.run(self.cypher_query_to_get_results).data()
                self.answer_kg = session.run(self.cypher_query_to_get_kg).data()[0]
            driver.close()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered an error interacting with KG2 neo4j. {tb}",
                                error_code=error_type.__name__)

    def __build_final_kg_of_answers(self):
        pass
        # TODO: Build a dictionary of node/edge IDs to qnode/qedge IDs
        # TODO: Create answer node/edges and build knowledge graph with all in it
