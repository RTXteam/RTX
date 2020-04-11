#!/bin/env python3
import sys
import os
import traceback
import json
import ast

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
import ReasoningUtilities as RU
from KGNodeIndex import KGNodeIndex
from QueryGraphReasoner import QueryGraphReasoner
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.edge_attribute import EdgeAttribute


class KG2Querier:

    def __init__(self, response_object):
        self.response = response_object
        self.query_graph = None
        self.cypher_query = None
        self.query_results = None
        self.final_kg = {'nodes': dict(), 'edges': dict()}

    def answer_query(self, query_graph):
        """
        This function answers a query using KG2.
        :param query_graph: A Translator API standard query graph.
        :return: An (almost) Translator API standard knowledge graph containing all of the nodes and edges returned from
        KG2 as results for that query. ('Almost' standard in that kg.edges and kg.nodes are dictionaries rather than
        lists.)
        """
        self.query_graph = query_graph

        self.__add_curie_synonyms_to_query_graph()
        if not self.response.status == 'OK':
            return self.final_kg

        self.__generate_cypher_to_run()
        if not self.response.status == 'OK':
            return self.final_kg

        self.__run_cypher_in_neo4j()
        if not self.response.status == 'OK':
            return self.final_kg

        self.__add_answers_to_kg()
        if not self.response.status == 'OK':
            return self.final_kg

        return self.final_kg

    def __add_curie_synonyms_to_query_graph(self):
        self.response.debug("Looking for curie synonyms to use")
        KGNI = KGNodeIndex()
        for node in self.query_graph.nodes:
            original_curie = node.curie
            if original_curie and type(original_curie) is str:  # Important because sometimes lists of curies are passed behind the scenes (when expanding one edge at a time)
                node.curie = KGNI.get_equivalent_curies(original_curie)
                node.type = None  # Equivalent curie types may be different than the original, so we clear this
                self.response.info(f"Using equivalent curies for node {original_curie}: {node.curie}")

    def __generate_cypher_to_run(self):
        self.response.debug(f"Generating cypher for edge {self.query_graph.edges[0].id} query graph")
        try:
            # Build the match clause
            edge = self.query_graph.edges[0]  # Currently only single-edge query graphs are sent to KG2Querier
            source_node = self.__get_query_node(edge.source_id)
            target_node = self.__get_query_node(edge.target_id)
            edge_cypher = self.__get_cypher_for_query_edge(edge)
            source_node_cypher = self.__get_cypher_for_query_node(source_node)
            target_node_cypher = self.__get_cypher_for_query_node(target_node)
            match_clause = f"MATCH {source_node_cypher}{edge_cypher}{target_node_cypher}"

            # Build the where clause
            where_fragments = []
            for node in [source_node, target_node]:
                if node.curie:
                    if type(node.curie) is str:
                        where_fragment = f"{node.id}.id={node.curie}"
                    else:
                        where_fragment = f"{node.id}.id in {node.curie}"
                    where_fragments.append(where_fragment)
            if len(where_fragments):
                where_clause = "WHERE "
                where_clause += " AND ".join(where_fragments)
            else:
                where_clause = ""

            # Build the with clause
            source_node_col_name = f"nodes_{source_node.id}"
            target_node_col_name = f"nodes_{target_node.id}"
            edge_col_name = f"edges_{edge.id}"
            with_clause = f"WITH collect(distinct {source_node.id}) as {source_node_col_name}, " \
                          f"collect(distinct {target_node.id}) as {target_node_col_name}, " \
                          f"collect(distinct {edge.id}) as {edge_col_name}"

            # Build the return clause
            return_clause = f"RETURN {source_node_col_name}, {target_node_col_name}, {edge_col_name}"

            self.cypher_query = f"{match_clause} {where_clause} {with_clause} {return_clause}"
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)

    def __run_cypher_in_neo4j(self):
        self.response.info(f"Sending cypher query for edge {self.query_graph.edges[0].id} to KG2 neo4j")
        try:
            rtx_config = RTXConfiguration()
            rtx_config.live = "KG2"
            driver = GraphDatabase.driver(rtx_config.neo4j_bolt, auth=(rtx_config.neo4j_username, rtx_config.neo4j_password))
            with driver.session() as session:
                self.query_results = session.run(self.cypher_query).data()
            driver.close()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered an error interacting with KG2 neo4j. {tb}",
                                error_code=error_type.__name__)
        else:
            columns_with_lengths = dict()
            for column in self.query_results[0]:
                columns_with_lengths[column] = len(self.query_results[0].get(column))
            if any(length == 0 for length in columns_with_lengths.values()):
                self.response.warning("No paths were found in KG2 satisfying this query graph")
            else:
                num_results_string = ", ".join([f"{column}: {value}" for column, value in columns_with_lengths.items()])
                self.response.info(f"Query for edge {self.query_graph.edges[0].id} returned results ({num_results_string})")

    def __add_answers_to_kg(self):
        self.response.debug(f"Processing query results for edge {self.query_graph.edges[0].id}")

        # Create swagger model nodes/edges based on our results and add to answer knowledge graph
        results_table = self.query_results[0]
        column_names = [column_name for column_name in results_table]
        for column_name in column_names:
            if column_name.startswith('nodes'):  # Example column name: 'nodes_n00'
                qnode_id = column_name.replace("nodes_", "", 1)
                for node in results_table.get(column_name):
                    swagger_node = self.__create_swagger_node_from_neo4j_node(node, qnode_id)
                    self.final_kg['nodes'][swagger_node.id] = swagger_node
            elif column_name.startswith('edges'):  # Example column name: 'edges_e01'
                qedge_id = column_name.replace("edges_", "", 1)
                for edge in results_table.get(column_name):
                    swagger_edge = self.__create_swagger_edge_from_neo4j_edge(edge, qedge_id)
                    self.final_kg['edges'][swagger_edge.id] = swagger_edge

    def __create_swagger_node_from_neo4j_node(self, neo4j_node, qnode_id):
        swagger_node = Node()

        swagger_node.qnode_id = qnode_id
        swagger_node.id = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.node_attributes = []

        node_category = neo4j_node.get('category_label')
        swagger_node.type = node_category if type(node_category) is list else [node_category]

        # Fill out the 'symbol' property (only really relevant for nodes from UniProtKB)
        if swagger_node.symbol is None and swagger_node.id.lower().startswith("uniprot"):
            swagger_node.symbol = neo4j_node.get('name')
            swagger_node.name = neo4j_node.get('full_name')

        # Add all additional properties on KG2 nodes as swagger NodeAttribute objects
        additional_kg2_node_properties = ['publications', 'synonym', 'category', 'provided_by', 'deprecated',
                                          'update_date']
        node_attributes = self.__create_swagger_attributes("node", additional_kg2_node_properties, neo4j_node)
        swagger_node.node_attributes += node_attributes

        return swagger_node

    def __create_swagger_edge_from_neo4j_edge(self, neo4j_edge, qedge_id):
        swagger_edge = Edge()

        swagger_edge.qedge_id = qedge_id
        swagger_edge.type = neo4j_edge.get('simplified_edge_label')
        swagger_edge.source_id = neo4j_edge.get('subject')
        swagger_edge.target_id = neo4j_edge.get('object')
        swagger_edge.id = f"{swagger_edge.source_id}--{swagger_edge.type}--{swagger_edge.target_id}"
        swagger_edge.relation = neo4j_edge.get('relation')
        swagger_edge.publications = ast.literal_eval(neo4j_edge.get('publications'))
        swagger_edge.provided_by = ast.literal_eval(neo4j_edge.get('provided_by'))
        swagger_edge.negated = ast.literal_eval(neo4j_edge.get('negated'))
        swagger_edge.is_defined_by = "ARAX/KG2"
        swagger_edge.edge_attributes = []

        # Add additional properties on KG2 edges as swagger EdgeAttribute objects
        # TODO: fix issues coming from strange characters in 'publications_info'! (EOF error)
        additional_kg2_edge_properties = ['relation_curie', 'simplified_relation_curie', 'simplified_relation',
                                          'edge_label']
        edge_attributes = self.__create_swagger_attributes("edge", additional_kg2_edge_properties, neo4j_edge)
        swagger_edge.edge_attributes += edge_attributes

        return swagger_edge

    def __create_swagger_attributes(self, object_type, property_names, neo4j_object):
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            if type(property_value) is str:
                if (property_value.startswith('[') and property_value.endswith(']')) or \
                        (property_value.startswith('{') and property_value.endswith('}')) or \
                        property_value.lower() == "true" or property_value.lower() == "false":
                    property_value = ast.literal_eval(property_value)

            if property_value is not None and property_value != {} and property_value != []:
                swagger_attribute = NodeAttribute() if object_type == "node" else EdgeAttribute()
                swagger_attribute.name = property_name
                swagger_attribute.value = property_value
                new_attributes.append(swagger_attribute)

        return new_attributes

    def __get_query_node(self, qnode_id):
        for node in self.query_graph.nodes:
            if node.id == qnode_id:
                return node
        return None

    def __get_cypher_for_query_node(self, node):
        node_type_string = f":{node.type}" if node.type else ""
        final_node_string = f"({node.id}{node_type_string})"
        return final_node_string

    def __get_cypher_for_query_edge(self, edge):
        edge_type_string = f":{edge.type}" if edge.type else ""
        final_edge_string = f"-[{edge.id}{edge_type_string}]-"
        return final_edge_string