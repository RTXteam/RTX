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
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.edge_attribute import EdgeAttribute


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
        :param query_graph: A Translator API standard query graph.
        :return: An (almost) Translator API standard knowledge graph containing all of the nodes and edges returned from
        KG2 as results for that query. ('Almost' standard in that kg.edges and kg.nodes are dictionaries rather than
        lists.)
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
            rtx_config = RTXConfiguration()
            rtx_config.live = "KG2"
            driver = GraphDatabase.driver(rtx_config.neo4j_bolt, auth=(rtx_config.neo4j_username, rtx_config.neo4j_password))
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
                self.response.info(f"Query returned {len(self.answer_results)} results "
                                   f"({len(self.answer_kg.get('nodes'))} nodes, "
                                   f"{len(self.answer_kg.get('edges'))} edges)")

    def __build_final_kg_of_answers(self):
        self.response.info("Processing query results")
        # Create a map of each node/edge and its corresponding qnode/qedge ID
        query_id_map = self.__create_query_id_map()

        # Create swagger model nodes based on our results and add to final knowledge graph
        for node in self.answer_kg.get('nodes'):
            swagger_node = self.__create_swagger_node_from_neo4j_node(node, query_id_map)
            self.final_kg['nodes'][swagger_node.id] = swagger_node

        # Create swagger model edges based on our results and add to final knowledge graph
        for edge in self.answer_kg.get('edges'):
            swagger_edge = self.__create_swagger_edge_from_neo4j_edge(edge, query_id_map)
            self.final_kg['edges'][swagger_edge.id] = swagger_edge

    def __create_query_id_map(self):
        query_id_map = {'nodes': dict(), 'edges': dict()}
        for result in self.answer_results:
            # Map all of the nodes to their corresponding query node IDs
            result_nodes = result.get('nodes')
            for qnode_id, node_curie in result_nodes.items():
                if node_curie not in query_id_map['nodes']:
                    query_id_map['nodes'][node_curie] = qnode_id

            # Map all of the edges to their corresponding query edge IDs
            result_edges = result.get('edges')
            for qedge_id, edge_ids in result_edges.items():
                for edge_id in edge_ids:
                    if edge_id not in query_id_map['edges']:
                        query_id_map['edges'][edge_id] = qedge_id

        # TODO: Later adjust for the possibility of the same node/edge having more than one qnode/qedge ID
        return query_id_map

    def __create_swagger_node_from_neo4j_node(self, neo4j_node, query_id_map):
        swagger_node = Node()

        swagger_node.id = neo4j_node.get('id')
        swagger_node.type = neo4j_node.get('type')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.node_attributes = []

        # Fill out the 'symbol' property (only really relevant for nodes from UniProtKB)
        if swagger_node.symbol is None and swagger_node.id.lower().startswith("uniprot"):
            swagger_node.symbol = neo4j_node.get('name')
            swagger_node.name = neo4j_node.get('full_name')

        # Tack the query node ID that this node corresponds to onto it (needed for processing down the line)
        swagger_node.qnode_id = query_id_map['nodes'].get(swagger_node.id)
        if not swagger_node.qnode_id:
            self.response.warning(f"Node {swagger_node.id} is missing a qnode_id")

        # Add all additional properties on KG2 nodes as swagger NodeAttribute objects
        additional_kg2_properties = ['publications', 'provided_by', 'deprecated', 'synonym', 'category', 'update_date']
        for property_name in additional_kg2_properties:
            property_value = neo4j_node.get(property_name)
            if property_value is not None and property_value != [] and property_value != "[]":
                new_node_attribute = NodeAttribute()
                new_node_attribute.name = property_name
                new_node_attribute.value = property_value
                swagger_node.node_attributes.append(new_node_attribute)

        return swagger_node

    def __create_swagger_edge_from_neo4j_edge(self, neo4j_edge, query_id_map):
        swagger_edge = Edge()

        # Loop through all properties on our swagger model edge and attempt to fill them out using neo4j edge
        for edge_property in swagger_edge.to_dict():
            value = neo4j_edge.get(edge_property)
            setattr(swagger_edge, edge_property, value)

        # Convert the 'negated' property from string to boolean
        if type(swagger_edge.negated) is str:
            swagger_edge.negated = True if neo4j_edge.get('negated').lower() == "true" else False

        # Indicate what knowledge source this edge comes from
        if swagger_edge.is_defined_by is None:
            swagger_edge.is_defined_by = "ARAX/KG2"

        # Tack the query edge ID that this edge corresponds to onto it (needed for processing down the line)
        swagger_edge.qedge_id = query_id_map['edges'].get(swagger_edge.id)
        if not swagger_edge.qedge_id:
            self.response.warning(f"Edge {swagger_edge.id} is missing a qedge_id")

        return swagger_edge
