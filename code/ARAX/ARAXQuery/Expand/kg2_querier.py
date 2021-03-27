#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple

import requests
import yaml
from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from expand_utilities import QGOrganizedKnowledgeGraph
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.query_graph import QueryGraph


class KG2Querier:

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

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
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
        if kg_name == "KG1":
            query_graph = eu.make_qg_use_old_snake_case_types(query_graph)
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()

        # Verify this is a valid one-hop query graph
        if len(query_graph.edges) != 1:
            log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg, edge_to_nodes_map
        if len(query_graph.nodes) != 2:
            log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg, edge_to_nodes_map
        qedge_key = next(qedge_key for qedge_key in query_graph.edges)

        # Consider any inverses of our predicate(s) as well
        query_graph = self._add_inverted_predicates(query_graph, log)

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        qnode_keys_with_curies = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.id]
        for qnode_key in qnode_keys_with_curies:
            qnode = query_graph.nodes[qnode_key]
            if use_synonyms and kg_name == "KG1":
                qnode.id = eu.get_curie_synonyms(qnode.id, log)
            elif kg_name == "KG2c":
                canonical_curies = eu.get_canonical_curies_list(qnode.id, log)
                log.debug(f"Using {len(canonical_curies)} curies as canonical curies for qnode {qnode_key}")
                qnode.id = canonical_curies
            qnode.category = []  # Important to clear this, otherwise results are limited (#889)

        # Run the actual query and process results
        cypher_query = self._convert_one_hop_query_graph_to_cypher_query(query_graph, enforce_directionality, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        neo4j_results = self._answer_query_using_neo4j(cypher_query, qedge_key, kg_name, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        final_kg, edge_to_nodes_map = self._load_answers_into_kg(neo4j_results, kg_name, query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        return final_kg, edge_to_nodes_map

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        kg_name = self.kg_name
        use_synonyms = self.use_synonyms
        log = self.response
        if kg_name == "KG1":
            single_node_qg = eu.make_qg_use_old_snake_case_types(single_node_qg)
        final_kg = QGOrganizedKnowledgeGraph()
        qnode_key = next(qnode_key for qnode_key in single_node_qg.nodes)
        qnode = single_node_qg.nodes[qnode_key]

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        if qnode.id:
            if use_synonyms and kg_name == "KG1":
                qnode.id = eu.get_curie_synonyms(qnode.id, log)
                qnode.category = []  # Important to clear this, otherwise results are limited (#889)
            elif kg_name == "KG2c":
                qnode.id = eu.get_canonical_curies_list(qnode.id, log)
                qnode.category = []  # Important to clear this to avoid discrepancies in types for particular concepts

        # Build and run a cypher query to get this node/nodes
        where_clause = f"{qnode_key}.id='{qnode.id}'" if type(qnode.id) is str else f"{qnode_key}.id in {qnode.id}"
        cypher_query = f"MATCH {self._get_cypher_for_query_node(qnode_key, single_node_qg)} WHERE {where_clause} RETURN {qnode_key}"
        log.info(f"Sending cypher query for node {qnode_key} to {kg_name} neo4j")
        results = self._run_cypher_query(cypher_query, kg_name, log)

        # Load the results into API object model and add to our answer knowledge graph
        for result in results:
            neo4j_node = result.get(qnode_key)
            node_key, node = self._convert_neo4j_node_to_trapi_node(neo4j_node, kg_name)
            final_kg.add_node(node_key, node, qnode_key)

        return final_kg

    def _convert_one_hop_query_graph_to_cypher_query(self, qg: QueryGraph, enforce_directionality: bool,
                                                     log: ARAXResponse) -> str:
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        log.debug(f"Generating cypher for edge {qedge_key} query graph")
        try:
            # Build the match clause
            subject_qnode_key = qedge.subject
            object_qnode_key = qedge.object
            qedge_cypher = self._get_cypher_for_query_edge(qedge_key, qg, enforce_directionality)
            source_qnode_cypher = self._get_cypher_for_query_node(subject_qnode_key, qg)
            target_qnode_cypher = self._get_cypher_for_query_node(object_qnode_key, qg)
            match_clause = f"MATCH {source_qnode_cypher}{qedge_cypher}{target_qnode_cypher}"

            # Build the where clause
            where_fragments = []
            for qnode_key in [subject_qnode_key, object_qnode_key]:
                qnode = qg.nodes[qnode_key]
                if qnode.id and isinstance(qnode.id, list) and len(qnode.id) > 1:
                    where_fragments.append(f"{qnode_key}.id in {qnode.id}")
                if qnode.category:
                    qnode.category = eu.convert_to_list(qnode.category)
                    if len(qnode.category) > 1:
                        # Create where fragment that looks like 'n00:biolink:Disease OR n00:biolink:PhenotypicFeature..'
                        category_sub_fragments = [f"{qnode_key}:`{category}`" for category in qnode.category]
                        category_where_fragment = f"({' OR '.join(category_sub_fragments)})"
                        where_fragments.append(category_where_fragment)
            where_clause = f"WHERE {' AND '.join(where_fragments)}" if where_fragments else ""

            # Build the with clause
            source_qnode_col_name = f"nodes_{subject_qnode_key}"
            target_qnode_col_name = f"nodes_{object_qnode_key}"
            qedge_col_name = f"edges_{qedge_key}"
            # This line grabs the edge's ID and a record of which of its nodes correspond to which qnode ID
            extra_edge_properties = "{.*, " + f"id:ID({qedge_key}), {subject_qnode_key}:{subject_qnode_key}.id, {object_qnode_key}:{object_qnode_key}.id" + "}"
            with_clause = f"WITH collect(distinct {subject_qnode_key}) as {source_qnode_col_name}, " \
                          f"collect(distinct {object_qnode_key}) as {target_qnode_col_name}, " \
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
                              qg: QueryGraph, log: ARAXResponse) -> Tuple[QGOrganizedKnowledgeGraph, Dict[str, Dict[str, str]]]:
        log.debug(f"Processing query results for edge {next(qedge_key for qedge_key in qg.edges)}")
        final_kg = QGOrganizedKnowledgeGraph()
        edge_to_nodes_map = dict()
        node_uuid_to_curie_dict = self._build_node_uuid_to_curie_dict(neo4j_results[0]) if kg_name == "KG1" else dict()

        results_table = neo4j_results[0]
        column_names = [column_name for column_name in results_table]
        for column_name in column_names:
            # Load answer nodes into our knowledge graph
            if column_name.startswith('nodes'):  # Example column name: 'nodes_n00'
                column_qnode_key = column_name.replace("nodes_", "", 1)
                for neo4j_node in results_table.get(column_name):
                    node_key, node = self._convert_neo4j_node_to_trapi_node(neo4j_node, kg_name)
                    final_kg.add_node(node_key, node, column_qnode_key)
            # Load answer edges into our knowledge graph
            elif column_name.startswith('edges'):  # Example column name: 'edges_e01'
                column_qedge_key = column_name.replace("edges_", "", 1)
                for neo4j_edge in results_table.get(column_name):
                    edge_key, edge = self._convert_neo4j_edge_to_trapi_edge(neo4j_edge, node_uuid_to_curie_dict, kg_name)

                    # Record which of this edge's nodes correspond to which qnode_key
                    if edge_key not in edge_to_nodes_map:
                        edge_to_nodes_map[edge_key] = dict()
                    for qnode_key in qg.nodes:
                        edge_to_nodes_map[edge_key][qnode_key] = neo4j_edge.get(qnode_key)

                    # Finally add the current edge to our answer knowledge graph
                    final_kg.add_edge(edge_key, edge, column_qedge_key)

        return final_kg, edge_to_nodes_map

    def _convert_neo4j_node_to_trapi_node(self, neo4j_node: Dict[str, any], kp: str) -> Tuple[str, Node]:
        if kp == "KG2":
            return self._convert_kg2_node_to_trapi_node(neo4j_node)
        elif kp == "KG2c":
            return self._convert_kg2c_node_to_trapi_node(neo4j_node)
        else:
            return self._convert_kg1_node_to_trapi_node(neo4j_node)

    def _convert_kg2_node_to_trapi_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        node = Node()
        node_key = neo4j_node.get('id')
        node.name = neo4j_node.get('name')
        node.category = eu.convert_to_list(neo4j_node.get('category'))
        # Add all additional properties on KG2 nodes as TRAPI Attribute objects
        other_properties = ["iri", "full_name", "description", "publications", "synonym", "provided_by",
                            "deprecated", "update_date"]
        node.attributes = self._create_trapi_attributes(other_properties, neo4j_node)
        return node_key, node

    def _convert_kg2c_node_to_trapi_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        node = Node()
        node_key = neo4j_node.get('id')
        node.name = neo4j_node.get('name')
        node.category = eu.convert_to_list(neo4j_node.get('category'))
        # Add all additional properties on KG2c nodes as TRAPI Attribute objects
        other_properties = ["iri", "description", "all_names", "all_categories", "expanded_categories",
                            "equivalent_curies", "publications"]
        node.attributes = self._create_trapi_attributes(other_properties, neo4j_node)
        return node_key, node

    def _convert_kg1_node_to_trapi_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        node = Node()
        node_key = neo4j_node.get('id')
        node.name = neo4j_node.get('name')
        node_category = neo4j_node.get('category')
        node.category = eu.convert_to_list(node_category)
        other_properties = ["symbol", "description", "uri"]
        node.attributes = self._create_trapi_attributes(other_properties, neo4j_node)
        return node_key, node

    def _convert_neo4j_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any], node_uuid_to_curie_dict: Dict[str, str],
                                          kg_name: str) -> Tuple[str, Edge]:
        if kg_name == "KG2":
            return self._convert_kg2_edge_to_trapi_edge(neo4j_edge)
        elif kg_name == "KG2c":
            return self._convert_kg2c_edge_to_trapi_edge(neo4j_edge)
        else:
            return self._convert_kg1_edge_to_trapi_edge(neo4j_edge, node_uuid_to_curie_dict)

    def _convert_kg2_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any]) -> Edge:
        edge = Edge()
        edge_key = f"KG2:{neo4j_edge.get('id')}"
        edge.predicate = neo4j_edge.get("predicate")
        edge.subject = neo4j_edge.get("subject")
        edge.object = neo4j_edge.get("object")
        edge.relation = neo4j_edge.get("relation")
        # Add additional properties on KG2 edges as TRAPI Attribute objects
        other_properties = ["provided_by", "negated", "relation_curie", "simplified_relation_curie",
                            "simplified_relation", "edge_label", "publications"]
        edge.attributes = self._create_trapi_attributes(other_properties, neo4j_edge)
        is_defined_by_attribute = Attribute(name="is_defined_by", value="ARAX/KG2", type=eu.get_attribute_type("is_defined_by"))
        edge.attributes.append(is_defined_by_attribute)
        return edge_key, edge

    def _convert_kg2c_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any]) -> Tuple[str, Edge]:
        edge = Edge()
        edge_key = f"KG2c:{neo4j_edge.get('id')}"
        edge.predicate = neo4j_edge.get("predicate")
        edge.subject = neo4j_edge.get("subject")
        edge.object = neo4j_edge.get("object")
        other_properties = ["provided_by", "publications"]
        edge.attributes = self._create_trapi_attributes(other_properties, neo4j_edge)
        is_defined_by_attribute = Attribute(name="is_defined_by", value="ARAX/KG2c", type=eu.get_attribute_type("is_defined_by"))
        edge.attributes.append(is_defined_by_attribute)
        return edge_key, edge

    def _convert_kg1_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any], node_uuid_to_curie_dict: Dict[str, str]) -> Tuple[str, Edge]:
        edge = Edge()
        edge_key = f"KG1:{neo4j_edge.get('id')}"
        edge.predicate = neo4j_edge.get("predicate")
        edge.subject = node_uuid_to_curie_dict[neo4j_edge.get("source_node_uuid")]
        edge.object = node_uuid_to_curie_dict[neo4j_edge.get("target_node_uuid")]
        edge.relation = neo4j_edge.get("relation")
        other_properties = ["provided_by", "probability"]
        edge.attributes = self._create_trapi_attributes(other_properties, neo4j_edge)
        is_defined_by_attribute = Attribute(name="is_defined_by", value="ARAX/KG1", type=eu.get_attribute_type("is_defined_by"))
        edge.attributes.append(is_defined_by_attribute)
        return edge_key, edge

    @staticmethod
    def _create_trapi_attributes(property_names: List[str], neo4j_object: Dict[str, any]) -> List[Attribute]:
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            if property_value:
                # Extract any lists, dicts, and booleans that are stored within strings
                if type(property_value) is str:
                    if (property_value.startswith('[') and property_value.endswith(']')) or \
                            (property_value.startswith('{') and property_value.endswith('}')) or \
                            property_value.lower() == "true" or property_value.lower() == "false":
                        property_value = ast.literal_eval(property_value)

                # Create the actual Attribute object
                trapi_attribute = Attribute(name=property_name,
                                            type=eu.get_attribute_type(property_name),
                                            value=property_value)
                # Also store this value in Attribute.url if it's a URL
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    trapi_attribute.url = property_value

                new_attributes.append(trapi_attribute)
        return new_attributes

    @staticmethod
    def _run_cypher_query(cypher_query: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, any]]:
        rtxc = RTXConfiguration()
        if "KG2" in kg_name:  # Flip into KG2 mode if that's our KP (rtx config is set to KG1 info by default)
            rtxc.live = kg_name
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
    def _get_cypher_for_query_node(qnode_key: str, qg: QueryGraph) -> str:
        qnode = qg.nodes[qnode_key]
        # Add in node label if there's only one category
        category_cypher = f":`{qnode.category[0]}`" if len(qnode.category) == 1 else ""
        if qnode.id and (isinstance(qnode.id, str) or len(qnode.id) == 1):
            curie = qnode.id if isinstance(qnode.id, str) else qnode.id[0]
            curie_cypher = f" {{id:'{curie}'}}"
        else:
            curie_cypher = ""
        qnode_cypher = f"({qnode_key}{category_cypher}{curie_cypher})"
        return qnode_cypher

    @staticmethod
    def _get_cypher_for_query_edge(qedge_key: str, qg: QueryGraph, enforce_directionality: bool) -> str:
        qedge = qg.edges[qedge_key]
        predicate_cypher = "|".join([f":`{predicate}`" for predicate in qedge.predicate])
        full_qedge_cypher = f"-[{qedge_key}{predicate_cypher}]-"
        if enforce_directionality:
            full_qedge_cypher += ">"
        return full_qedge_cypher

    @staticmethod
    def _add_inverted_predicates(qg: QueryGraph, log: ARAXResponse) -> QueryGraph:
        # For now, we'll consider BOTH predicates in an inverse pair (TODO: later tailor to what we know is in KG2)
        qedge = next(qedge for qedge in qg.edges.values())
        response = requests.get("https://raw.githubusercontent.com/biolink/biolink-model/master/biolink-model.yaml")
        if response.status_code == 200:
            qedge.predicate = eu.convert_to_list(qedge.predicate)
            biolink_model = yaml.safe_load(response.text)
            inverse_predicates = set()
            for predicate in qedge.predicate:
                english_predicate = predicate.split(":")[-1].replace("_", " ")  # Converts to 'subclass of' format
                biolink_predicate_info = biolink_model["slots"].get(english_predicate)
                if biolink_predicate_info and "inverse" in biolink_predicate_info:
                    english_inverse_predicate = biolink_predicate_info["inverse"]
                    machine_inverse_predicate = f"biolink:{english_inverse_predicate.replace(' ', '_')}"
                    inverse_predicates.add(machine_inverse_predicate)
                    log.debug(f"Found inverse predicate for {predicate}: {machine_inverse_predicate}")
            qedge.predicate = list(set(qedge.predicate).union(inverse_predicates))
        else:
            log.warning(f"Cannot check for inverse predicates: Failed to load Biolink Model yaml file. "
                        f"(Page gave status {response.status_code}.)")
        return qg
