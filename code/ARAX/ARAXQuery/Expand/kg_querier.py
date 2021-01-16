#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import DictKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge


class KGQuerier:

    def __init__(self, response_object: ARAXResponse, input_kp: str):
        self.response = response_object
        self.enforce_directionality = self.response.data['parameters'].get('enforce_directionality')
        self.use_synonyms = self.response.data['parameters'].get('use_synonyms')
        if input_kp == "ARAX/KG2":
            if self.use_synonyms:
                self.kg_name = "KG2c"
            else:
                self.kg_name = "KG2"
        else:
            self.kg_name = "KG1"

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using either KG1 or KG2.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_keys for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.response
        enforce_directionality = self.enforce_directionality
        use_synonyms = self.use_synonyms
        kg_name = self.kg_name
        final_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Verify this is a valid one-hop query graph
        if len(query_graph.edges) != 1:
            log.error(f"KGQuerier.answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg, edge_to_nodes_map
        if len(query_graph.nodes) != 2:
            log.error(f"KGQuerier.answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg, edge_to_nodes_map
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)
        qedge = query_graph.edges[qedge_key]

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        qnodes_with_curies = [qnode for qnode in query_graph.nodes.values() if qnode.id]
        for qnode in qnodes_with_curies:
            if use_synonyms and kg_name == "KG1":
                qnode.id = eu.get_curie_synonyms(qnode.id, log)
            elif kg_name == "KG2c":
                qnode.id = eu.get_canonical_curies_list(qnode.id, log)
            qnode.category = None  # Important to clear this, otherwise results are limited (#889)

        # Run the actual query and process results
        cypher_query = self._convert_one_hop_query_graph_to_cypher_query(query_graph, enforce_directionality, kg_name, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        neo4j_results = self._answer_query_using_neo4j(cypher_query, qedge_key, kg_name, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        final_kg, edge_to_nodes_map = self._load_answers_into_kg(neo4j_results, kg_name, query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        return final_kg, edge_to_nodes_map

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> DictKnowledgeGraph:
        kg_name = self.kg_name
        use_synonyms = self.use_synonyms
        log = self.response
        final_kg = DictKnowledgeGraph()
        qnode_key = next(qnode_key for qnode_key in single_node_qg.nodes)
        qnode = single_node_qg[qnode_key]

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        if qnode.id:
            if use_synonyms and kg_name == "KG1":
                qnode.id = eu.get_curie_synonyms(qnode.id, log)
                qnode.category = None  # Important to clear this, otherwise results are limited (#889)
            elif kg_name == "KG2c":
                qnode.id = eu.get_canonical_curies_list(qnode.id, log)
                qnode.category = None  # Important to clear this to avoid discrepancies in types for particular concepts

        # Build and run a cypher query to get this node/nodes
        where_clause = f"{qnode_key}.id='{qnode.id}'" if type(qnode.id) is str else f"{qnode_key}.id in {qnode.id}"
        cypher_query = f"MATCH {self._get_cypher_for_query_node(qnode, single_node_qg, kg_name)} WHERE {where_clause} RETURN {qnode_key}"
        log.info(f"Sending cypher query for node {qnode_key} to {kg_name} neo4j")
        results = self._run_cypher_query(cypher_query, kg_name, log)

        # Load the results into swagger object model and add to our answer knowledge graph
        for result in results:
            neo4j_node = result.get(qnode_key)
            swagger_node_key, swagger_node = self._convert_neo4j_node_to_swagger_node(neo4j_node, kg_name)
            final_kg.add_node(swagger_node_key, swagger_node, qnode_key)

        return final_kg

    def _convert_one_hop_query_graph_to_cypher_query(self, qg: QueryGraph, enforce_directionality: bool,
                                                     kg_name: str, log: ARAXResponse) -> str:
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        log.debug(f"Generating cypher for edge {qedge_key} query graph")
        try:
            # Build the match clause
            source_qnode_key = qedge.subject
            target_qnode_key = qedge.object
            qedge_cypher = self._get_cypher_for_query_edge(qedge_key, qg, enforce_directionality)
            source_qnode_cypher = self._get_cypher_for_query_node(source_qnode_key, qg, kg_name)
            target_qnode_cypher = self._get_cypher_for_query_node(target_qnode_key, qg, kg_name)
            match_clause = f"MATCH {source_qnode_cypher}{qedge_cypher}{target_qnode_cypher}"

            # Build the where clause
            where_fragments = []
            for qnode_key in [source_qnode_key, target_qnode_key]:
                qnode = qg.nodes[qnode_key]
                if qnode.id and isinstance(qnode.id, list) and len(qnode.id) > 1:
                    where_fragments.append(f"{qnode_key}.id in {qnode.id}")
                if qnode.category:
                    if kg_name == "KG2c":
                        qnode_categories = eu.convert_string_or_list_to_list(qnode.category)
                        category_fragments = [f"'{qnode_category}' in {qnode_key}.types" for qnode_category in qnode_categories]
                        joined_category_fragments = " OR ".join(category_fragments)
                        category_where_clause = joined_category_fragments if len(category_fragments) < 2 else f"({joined_category_fragments})"
                        where_fragments.append(category_where_clause)
                    elif isinstance(qnode.category, list):
                        if kg_name == "KG2":
                            node_category_property = "category_label"
                        else:
                            node_category_property = "category"
                        where_fragments.append(f"{qnode_key}.{node_category_property} in {qnode.category}")

            if where_fragments:
                where_clause = f"WHERE {' AND '.join(where_fragments)}"
            else:
                where_clause = ""

            # Build the with clause
            source_qnode_col_name = f"nodes_{source_qnode_key}"
            target_qnode_col_name = f"nodes_{target_qnode_key}"
            qedge_col_name = f"edges_{qedge_key}"
            # This line grabs the edge's ID and a record of which of its nodes correspond to which qnode ID
            extra_edge_properties = "{.*, " + f"id:ID({qedge_key}), {source_qnode_key}:{source_qnode_key}.id, {target_qnode_key}:{target_qnode_key}.id" + "}"
            with_clause = f"WITH collect(distinct {source_qnode_key}) as {source_qnode_col_name}, " \
                          f"collect(distinct {target_qnode_key}) as {target_qnode_col_name}, " \
                          f"collect(distinct {qedge_key}{extra_edge_properties}) as {qedge_col_name}"

            # Build the return clause
            return_clause = f"RETURN {source_qnode_col_name}, {target_qnode_col_name}, {qedge_col_name}"

            cypher_query = f"{match_clause} {where_clause} {with_clause} {return_clause}"
            return cypher_query
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)
            return ""

    def _answer_query_using_neo4j(self, cypher_query: str, qedge_key: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, List[Dict[str, any]]]]:
        log.info(f"Sending cypher query for edge {qedge_key} to {kg_name} neo4j")
        results_from_neo4j = self._run_cypher_query(cypher_query, kg_name, log)
        if log.status == 'OK':
            columns_with_lengths = dict()
            for column in results_from_neo4j[0]:
                columns_with_lengths[column] = len(results_from_neo4j[0].get(column))
        return results_from_neo4j

    def _load_answers_into_kg(self, neo4j_results: List[Dict[str, List[Dict[str, any]]]], kg_name: str,
                              qg: QueryGraph, log: ARAXResponse) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        log.debug(f"Processing query results for edge {next(qedge_key for qedge_key in qg.edges)}")
        final_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()
        node_uuid_to_curie_dict = self._build_node_uuid_to_curie_dict(neo4j_results[0]) if kg_name == "KG1" else dict()

        results_table = neo4j_results[0]
        column_names = [column_name for column_name in results_table]
        for column_name in column_names:
            # Load answer nodes into our knowledge graph
            if column_name.startswith('nodes'):  # Example column name: 'nodes_n00'
                column_qnode_key = column_name.replace("nodes_", "", 1)
                for neo4j_node in results_table.get(column_name):
                    swagger_node_key, swagger_node = self._convert_neo4j_node_to_swagger_node(neo4j_node, kg_name)
                    final_kg.add_node(swagger_node_key, swagger_node, column_qnode_key)
            # Load answer edges into our knowledge graph
            elif column_name.startswith('edges'):  # Example column name: 'edges_e01'
                column_qedge_key = column_name.replace("edges_", "", 1)
                for neo4j_edge in results_table.get(column_name):
                    swagger_edge = self._convert_neo4j_edge_to_swagger_edge(neo4j_edge, node_uuid_to_curie_dict, kg_name)

                    # Record which of this edge's nodes correspond to which qnode_key
                    if swagger_edge.id not in edge_to_nodes_map:
                        edge_to_nodes_map[swagger_edge.id] = dict()
                    for qnode_key in qg.nodes:
                        edge_to_nodes_map[swagger_edge.id][qnode_key] = neo4j_edge.get(qnode_key)

                    # Finally add the current edge to our answer knowledge graph
                    final_kg.add_edge(swagger_edge, column_qedge_key)

        return final_kg, edge_to_nodes_map

    def _convert_neo4j_node_to_swagger_node(self, neo4j_node: Dict[str, any], kp: str) -> Tuple[str, Node]:
        if kp == "KG2":
            return self._convert_kg2_node_to_swagger_node(neo4j_node)
        elif kp == "KG2c":
            return self._convert_kg2c_node_to_swagger_node(neo4j_node)
        else:
            return self._convert_kg1_node_to_swagger_node(neo4j_node)

    def _convert_kg2_node_to_swagger_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.attributes = []
        node_category = neo4j_node.get('category_label')
        swagger_node.category = eu.convert_string_or_list_to_list(node_category)
        # Fill out the 'symbol' property (only really relevant for nodes from UniProtKB)
        if swagger_node.symbol is None and swagger_node_key.lower().startswith("uniprot"):
            swagger_node.symbol = neo4j_node.get('name')
            swagger_node.name = neo4j_node.get('full_name')
        # Add all additional properties on KG2 nodes as swagger Attribute objects
        additional_kg2_node_properties = ['publications', 'synonym', 'category', 'provided_by', 'deprecated',
                                          'update_date']
        node_attributes = self._create_swagger_attributes("node", additional_kg2_node_properties, neo4j_node)
        swagger_node.attributes += node_attributes
        return swagger_node_key, swagger_node

    def _convert_kg2c_node_to_swagger_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.category = neo4j_node.get('types')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.description = neo4j_node.get('description')
        # Add all additional properties on KG2c nodes as swagger Attribute objects
        swagger_node.attributes = []
        additional_kg2c_node_properties = ['equivalent_curies', 'publications', 'all_names']
        node_attributes = self._create_swagger_attributes("node", additional_kg2c_node_properties, neo4j_node)
        swagger_node.attributes += node_attributes
        return swagger_node_key, swagger_node

    @staticmethod
    def _convert_kg1_node_to_swagger_node(neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        swagger_node = Node()
        swagger_node_key = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.symbol = neo4j_node.get('symbol')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('uri')
        swagger_node.attributes = []
        node_category = neo4j_node.get('category')
        swagger_node.category = eu.convert_string_or_list_to_list(node_category)
        return swagger_node_key, swagger_node

    def _convert_neo4j_edge_to_swagger_edge(self, neo4j_edge: Dict[str, any], node_uuid_to_curie_dict: Dict[str, str],
                                            kg_name: str) -> Edge:
        if kg_name == "KG2":
            return self._convert_kg2_edge_to_swagger_edge(neo4j_edge)
        elif kg_name == "KG2c":
            return self._convert_kg2c_edge_to_swagger_edge(neo4j_edge)
        else:
            return self._convert_kg1_edge_to_swagger_edge(neo4j_edge, node_uuid_to_curie_dict)

    def _convert_kg2_edge_to_swagger_edge(self, neo4j_edge: Dict[str, any]) -> Edge:
        swagger_edge = Edge()
        swagger_edge.id = f"KG2:{neo4j_edge.get('id')}"
        swagger_edge.predicate = neo4j_edge.get("simplified_edge_label")
        swagger_edge.subject = neo4j_edge.get("subject")
        swagger_edge.object = neo4j_edge.get("object")
        swagger_edge.relation = neo4j_edge.get("relation")
        swagger_edge.publications = neo4j_edge.get("publications")
        swagger_edge.provided_by = neo4j_edge.get("provided_by")
        swagger_edge.negated = ast.literal_eval(neo4j_edge.get("negated"))
        swagger_edge.is_defined_by = "ARAX/KG2"
        # Add additional properties on KG2 edges as swagger Attribute objects
        # TODO: fix issues coming from strange characters in 'publications_info'! (EOF error)
        additional_kg2_edge_properties = ["relation_curie", "simplified_relation_curie", "simplified_relation",
                                          "edge_label"]
        swagger_edge.attributes = self._create_swagger_attributes("edge", additional_kg2_edge_properties, neo4j_edge)
        return swagger_edge

    @staticmethod
    def _convert_kg2c_edge_to_swagger_edge(neo4j_edge: Dict[str, any]) -> Edge:
        swagger_edge = Edge()
        swagger_edge.predicate = neo4j_edge.get("simplified_edge_label")
        swagger_edge.subject = neo4j_edge.get("subject")
        swagger_edge.object = neo4j_edge.get("object")
        swagger_edge.id = f"KG2c:{neo4j_edge.get('id')}"
        swagger_edge.provided_by = neo4j_edge.get("provided_by")
        swagger_edge.is_defined_by = "ARAX/KG2c"
        swagger_edge.publications = neo4j_edge.get("publications")
        return swagger_edge

    def _convert_kg1_edge_to_swagger_edge(self, neo4j_edge: Dict[str, any], node_uuid_to_curie_dict: Dict[str, str]) -> Edge:
        swagger_edge = Edge()
        swagger_edge.predicate = neo4j_edge.get("predicate")
        swagger_edge.subject = node_uuid_to_curie_dict[neo4j_edge.get("source_node_uuid")]
        swagger_edge.object = node_uuid_to_curie_dict[neo4j_edge.get("target_node_uuid")]
        swagger_edge.id = f"KG1:{neo4j_edge.get('id')}"
        swagger_edge.relation = neo4j_edge.get("relation")
        swagger_edge.provided_by = neo4j_edge.get("provided_by")
        swagger_edge.is_defined_by = "ARAX/KG1"
        if neo4j_edge.get("probability"):
            swagger_edge.attributes = self._create_swagger_attributes("edge", ["probability"], neo4j_edge)
        return swagger_edge

    @staticmethod
    def _create_swagger_attributes(object_type: str, property_names: List[str], neo4j_object: Dict[str, any]):
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            # Extract any lists, dicts, and booleans that are stored within strings
            if type(property_value) is str:
                if (property_value.startswith('[') and property_value.endswith(']')) or \
                        (property_value.startswith('{') and property_value.endswith('}')) or \
                        property_value.lower() == "true" or property_value.lower() == "false":
                    property_value = ast.literal_eval(property_value)

            # Create an Attribute for all non-empty values
            if property_value is not None and property_value != {} and property_value != []:
                swagger_attribute = Attribute()
                swagger_attribute.name = property_name
                # Figure out whether this is a url and store it appropriately
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    swagger_attribute.url = property_value
                else:
                    swagger_attribute.value = property_value
                new_attributes.append(swagger_attribute)
        return new_attributes

    @staticmethod
    def _run_cypher_query(cypher_query: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, any]]:
        rtxc = RTXConfiguration()
        if "KG2" in kg_name:  # Flip into KG2 mode if that's our KP (rtx config is set to KG1 info by default)
            rtxc.live = kg_name.upper()  # TODO: Eventually change config file to "KG2c" vs. "KG2C" (then won't need to convert case here)
        try:
            driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
            with driver.session() as session:
                query_results = session.run(cypher_query).data()
            driver.close()
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Encountered an error interacting with {kg_name} neo4j. {tb}", error_code=error_type.__name__)
            return []
        else:
            return query_results

    @staticmethod
    def _build_node_uuid_to_curie_dict(results_table: Dict[str, List[Dict[str, any]]]) -> Dict[str, str]:
        node_uuid_to_curie_dict = dict()
        nodes_columns = [column_name for column_name in results_table if column_name.startswith('nodes')]
        for column in nodes_columns:
            for node in results_table.get(column):
                node_uuid_to_curie_dict[node.get('UUID')] = node.get('id')
        return node_uuid_to_curie_dict

    @staticmethod
    def _remap_edge(edge: Edge, new_curie: str, old_curie: str) -> Edge:
        if edge.subject == new_curie:
            edge.subject = old_curie
        if edge.object == new_curie:
            edge.object = old_curie
        return edge

    @staticmethod
    def _get_cypher_for_query_node(qnode_key: str, qg: QueryGraph, kg_name: str) -> str:
        qnode = qg.nodes[qnode_key]
        type_cypher = f":{qnode.category}" if qnode.category and isinstance(qnode.category, str) and kg_name != "KG2c" else ""
        if qnode.id and (isinstance(qnode.id, str) or len(qnode.id) == 1):
            curie = qnode.id if isinstance(qnode.id, str) else qnode.id[0]
            curie_cypher = f" {{id:'{curie}'}}"
        else:
            curie_cypher = ""
        qnode_cypher = f"({qnode_key}{type_cypher}{curie_cypher})"
        return qnode_cypher

    @staticmethod
    def _get_cypher_for_query_edge(qedge_key: str, qg: QueryGraph, enforce_directionality: bool) -> str:
        qedge = qg.edges[qedge_key]
        qedge_type_cypher = f":{qedge.predicate}" if qedge.predicate else ""
        full_qedge_cypher = f"-[{qedge_key}{qedge_type_cypher}]-"
        if enforce_directionality:
            full_qedge_cypher += ">"
        return full_qedge_cypher
