#!/bin/env python3
import sys
import os
import traceback
import ast
from typing import List, Dict, Tuple

from neo4j import GraphDatabase
import Expand.expand_utilities as eu
from Expand.expand_utilities import DictKnowledgeGraph
from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge


class KGQuerier:

    def __init__(self, response_object: Response, kp_to_use: str):
        self.response = response_object
        self.kp = "KG2" if kp_to_use == "ARAX/KG2" else "KG1"

    def answer_one_hop_query(self, query_graph: QueryGraph) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        """
        This function answers a one-hop (single-edge) query using either KG1 or KG2.
        :param query_graph: A Reasoner API standard query graph.
        :return: A tuple containing:
            1. an (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
           results for the query. (Dictionary version, organized by QG IDs.)
            2. a map of which nodes fulfilled which qnode_ids for each edge. Example:
              {'KG1:111221': {'n00': 'DOID:111', 'n01': 'HP:124'}, 'KG1:111223': {'n00': 'DOID:111', 'n01': 'HP:126'}}
        """
        log = self.response
        enforce_directionality = self.response.data['parameters']['enforce_directionality']
        continue_if_no_results = self.response.data['parameters']['continue_if_no_results']
        kp = self.kp
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
        qedge_id = query_graph.edges[0].id

        # Run the actual query and process results
        cypher_query = self._convert_one_hop_query_graph_to_cypher_query(query_graph, enforce_directionality, kp, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        neo4j_results = self._answer_one_hop_query_using_neo4j(cypher_query, qedge_id, kp, continue_if_no_results, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map
        final_kg, edge_to_nodes_map = self._load_answers_into_kg(neo4j_results, kp, query_graph, log)
        if log.status != 'OK':
            return final_kg, edge_to_nodes_map

        return final_kg, edge_to_nodes_map

    def answer_single_node_query(self, qnode: QNode) -> DictKnowledgeGraph:
        continue_if_no_results = self.response.data['parameters']['continue_if_no_results']
        kp = self.kp
        log = self.response
        final_kg = DictKnowledgeGraph()

        # Build and run a cypher query to get this node/nodes
        where_clause = f"{qnode.id}.id='{qnode.curie}'" if type(qnode.curie) is str else f"{qnode.id}.id in {qnode.curie}"
        cypher_query = f"MATCH {self._get_cypher_for_query_node(qnode)} WHERE {where_clause} RETURN {qnode.id}"
        log.info(f"Sending cypher query for node {qnode.id} to {kp} neo4j")
        results = self._run_cypher_query(cypher_query, kp, log)

        # Load the results into swagger object model and add to our answer knowledge graph
        if not results:
            if continue_if_no_results:
                log.warning(f"No paths were found in {kp} satisfying this query graph")
            else:
                log.error(f"No paths were found in {kp} satisfying this query graph", error_code="NoResults")
        for result in results:
            neo4j_node = result.get(qnode.id)
            swagger_node = self._convert_neo4j_node_to_swagger_node(neo4j_node, kp)
            final_kg.add_node(swagger_node, qnode.id)

        return final_kg

    def _convert_one_hop_query_graph_to_cypher_query(self, query_graph: QueryGraph, enforce_directionality: bool,
                                                     kp: str, log: Response) -> str:
        log.debug(f"Generating cypher for edge {query_graph.edges[0].id} query graph")
        try:
            # Build the match clause
            qedge = query_graph.edges[0]
            source_qnode = eu.get_query_node(query_graph, qedge.source_id)
            target_qnode = eu.get_query_node(query_graph, qedge.target_id)
            qedge_cypher = self._get_cypher_for_query_edge(qedge, enforce_directionality)
            source_qnode_cypher = self._get_cypher_for_query_node(source_qnode)
            target_qnode_cypher = self._get_cypher_for_query_node(target_qnode)
            match_clause = f"MATCH {source_qnode_cypher}{qedge_cypher}{target_qnode_cypher}"

            # Build the where clause
            where_fragments = []
            for qnode in [source_qnode, target_qnode]:
                if qnode.curie:
                    if type(qnode.curie) is str:
                        node_id_where_fragment = f"{qnode.id}.id='{qnode.curie}'"
                    else:
                        node_id_where_fragment = f"{qnode.id}.id in {qnode.curie}"
                    where_fragments.append(node_id_where_fragment)
                if qnode.type and isinstance(qnode.type, list):
                    if "KG2" in kp:
                        node_type_property = "category_label"
                    else:
                        node_type_property = "category"
                    where_fragments.append(f"{qnode.id}.{node_type_property} in {qnode.type}")
            if where_fragments:
                where_clause = f"WHERE {' AND '.join(where_fragments)}"
            else:
                where_clause = ""

            # Build the with clause
            source_qnode_col_name = f"nodes_{source_qnode.id}"
            target_qnode_col_name = f"nodes_{target_qnode.id}"
            qedge_col_name = f"edges_{qedge.id}"
            # This line grabs the edge's ID and a record of which of its nodes correspond to which qnode ID
            extra_edge_properties = "{.*, " + f"id:ID({qedge.id}), {source_qnode.id}:{source_qnode.id}.id, {target_qnode.id}:{target_qnode.id}.id" + "}"
            with_clause = f"WITH collect(distinct {source_qnode.id}) as {source_qnode_col_name}, " \
                          f"collect(distinct {target_qnode.id}) as {target_qnode_col_name}, " \
                          f"collect(distinct {qedge.id}{extra_edge_properties}) as {qedge_col_name}"

            # Build the return clause
            return_clause = f"RETURN {source_qnode_col_name}, {target_qnode_col_name}, {qedge_col_name}"

            cypher_query = f"{match_clause} {where_clause} {with_clause} {return_clause}"
            return cypher_query
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)
            return ""

    def _answer_one_hop_query_using_neo4j(self, cypher_query: str, qedge_id: str, kp: str, continue_if_no_results: bool,
                                          log: Response) -> List[Dict[str, List[Dict[str, any]]]]:
        log.info(f"Sending cypher query for edge {qedge_id} to {kp} neo4j")
        results_from_neo4j = self._run_cypher_query(cypher_query, kp, log)
        if log.status == 'OK':
            columns_with_lengths = dict()
            for column in results_from_neo4j[0]:
                columns_with_lengths[column] = len(results_from_neo4j[0].get(column))
            if any(length == 0 for length in columns_with_lengths.values()):
                if continue_if_no_results:
                    log.warning(f"No paths were found in {kp} satisfying this query graph")
                else:
                    log.error(f"No paths were found in {kp} satisfying this query graph", error_code="NoResults")
        return results_from_neo4j

    def _load_answers_into_kg(self, neo4j_results: List[Dict[str, List[Dict[str, any]]]], kp: str,  query_graph: QueryGraph,
                              log: Response) -> Tuple[DictKnowledgeGraph, Dict[str, Dict[str, str]]]:
        log.debug(f"Processing query results for edge {query_graph.edges[0].id}")
        final_kg = DictKnowledgeGraph()
        edge_to_nodes_map = dict()
        node_uuid_to_curie_dict = self._build_node_uuid_to_curie_dict(neo4j_results[0]) if kp == "KG1" else dict()

        results_table = neo4j_results[0]
        column_names = [column_name for column_name in results_table]
        for column_name in column_names:
            # Load answer nodes into our knowledge graph
            if column_name.startswith('nodes'):  # Example column name: 'nodes_n00'
                column_qnode_id = column_name.replace("nodes_", "", 1)
                for neo4j_node in results_table.get(column_name):
                    swagger_node = self._convert_neo4j_node_to_swagger_node(neo4j_node, kp)
                    final_kg.add_node(swagger_node, column_qnode_id)
            # Load answer edges into our knowledge graph
            elif column_name.startswith('edges'):  # Example column name: 'edges_e01'
                column_qedge_id = column_name.replace("edges_", "", 1)
                for neo4j_edge in results_table.get(column_name):
                    if kp == "KG2":
                        swagger_edge = self._convert_kg2_edge_to_swagger_edge(neo4j_edge)
                    else:
                        swagger_edge = self._convert_kg1_edge_to_swagger_edge(neo4j_edge, node_uuid_to_curie_dict)

                    # Record which of this edge's nodes correspond to which qnode_id
                    if swagger_edge.id not in edge_to_nodes_map:
                        edge_to_nodes_map[swagger_edge.id] = dict()
                    for qnode in query_graph.nodes:
                        edge_to_nodes_map[swagger_edge.id][qnode.id] = neo4j_edge.get(qnode.id)

                    # Finally add the current edge to our answer knowledge graph
                    final_kg.add_edge(swagger_edge, column_qedge_id)

        return final_kg, edge_to_nodes_map

    def _convert_neo4j_node_to_swagger_node(self, neo4j_node: Dict[str, any], kp: str) -> Node:
        if kp == "KG2":
            return self._convert_kg2_node_to_swagger_node(neo4j_node)
        else:
            return self._convert_kg1_node_to_swagger_node(neo4j_node)

    def _convert_kg2_node_to_swagger_node(self, neo4j_node: Dict[str, any]) -> Node:
        swagger_node = Node()
        swagger_node.id = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.node_attributes = []

        node_category = neo4j_node.get('category_label')
        swagger_node.type = eu.convert_string_or_list_to_list(node_category)

        # Fill out the 'symbol' property (only really relevant for nodes from UniProtKB)
        if swagger_node.symbol is None and swagger_node.id.lower().startswith("uniprot"):
            swagger_node.symbol = neo4j_node.get('name')
            swagger_node.name = neo4j_node.get('full_name')

        # Add all additional properties on KG2 nodes as swagger NodeAttribute objects
        additional_kg2_node_properties = ['publications', 'synonym', 'category', 'provided_by', 'deprecated',
                                          'update_date']
        node_attributes = self._create_swagger_attributes("node", additional_kg2_node_properties, neo4j_node)
        swagger_node.node_attributes += node_attributes

        return swagger_node

    @staticmethod
    def _convert_kg1_node_to_swagger_node(neo4j_node: Dict[str, any]) -> Node:
        swagger_node = Node()
        swagger_node.id = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.symbol = neo4j_node.get('symbol')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('uri')
        swagger_node.node_attributes = []

        node_category = neo4j_node.get('category')
        swagger_node.type = eu.convert_string_or_list_to_list(node_category)

        return swagger_node

    def _convert_kg2_edge_to_swagger_edge(self, neo4j_edge: Dict[str, any]) -> Edge:
        swagger_edge = Edge()
        swagger_edge.id = f"KG2:{neo4j_edge.get('id')}"
        swagger_edge.type = neo4j_edge.get("simplified_edge_label")
        swagger_edge.source_id = neo4j_edge.get("subject")
        swagger_edge.target_id = neo4j_edge.get("object")
        swagger_edge.relation = neo4j_edge.get("relation")
        swagger_edge.publications = neo4j_edge.get("publications")
        swagger_edge.provided_by = neo4j_edge.get("provided_by")
        swagger_edge.negated = ast.literal_eval(neo4j_edge.get("negated"))
        swagger_edge.is_defined_by = "ARAX/KG2"
        swagger_edge.edge_attributes = []

        # Add additional properties on KG2 edges as swagger EdgeAttribute objects
        # TODO: fix issues coming from strange characters in 'publications_info'! (EOF error)
        additional_kg2_edge_properties = ["relation_curie", "simplified_relation_curie", "simplified_relation",
                                          "edge_label"]
        edge_attributes = self._create_swagger_attributes("edge", additional_kg2_edge_properties, neo4j_edge)
        swagger_edge.edge_attributes += edge_attributes

        return swagger_edge

    def _convert_kg1_edge_to_swagger_edge(self, neo4j_edge: Dict[str, any], node_uuid_to_curie_dict: Dict[str, str]) -> Edge:
        swagger_edge = Edge()
        swagger_edge.type = neo4j_edge.get("predicate")
        swagger_edge.source_id = node_uuid_to_curie_dict[neo4j_edge.get("source_node_uuid")]
        swagger_edge.target_id = node_uuid_to_curie_dict[neo4j_edge.get("target_node_uuid")]
        swagger_edge.id = f"KG1:{neo4j_edge.get('id')}"
        swagger_edge.relation = neo4j_edge.get("relation")
        swagger_edge.provided_by = neo4j_edge.get("provided_by")
        swagger_edge.is_defined_by = "ARAX/KG1"

        if neo4j_edge.get("probability"):
            swagger_edge.edge_attributes = self._create_swagger_attributes("edge", ["probability"], neo4j_edge)
        return swagger_edge

    @staticmethod
    def _create_swagger_attributes(object_type: str, property_names: List[str], neo4j_object: Dict[str, any]):
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            if type(property_value) is str:
                # Extract any lists, dicts, and booleans that are stored within strings
                if (property_value.startswith('[') and property_value.endswith(']')) or \
                        (property_value.startswith('{') and property_value.endswith('}')) or \
                        property_value.lower() == "true" or property_value.lower() == "false":
                    property_value = ast.literal_eval(property_value)

            if property_value is not None and property_value != {} and property_value != []:
                swagger_attribute = NodeAttribute() if object_type == "node" else EdgeAttribute()
                swagger_attribute.name = property_name

                # Figure out whether this is a url and store it appropriately
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    swagger_attribute.url = property_value
                else:
                    swagger_attribute.value = property_value
                new_attributes.append(swagger_attribute)

        return new_attributes

    @staticmethod
    def _run_cypher_query(cypher_query: str, kp: str, log: Response) -> List[Dict[str, any]]:
        rtxc = RTXConfiguration()
        if kp == "KG2":  # Flip into KG2 mode if that's our KP (rtx config is set to KG1 info by default)
            rtxc.live = "KG2"
        try:
            driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
            with driver.session() as session:
                query_results = session.run(cypher_query).data()
            driver.close()
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.error(f"Encountered an error interacting with {kp} neo4j. {tb}", error_code=error_type.__name__)
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
        if edge.source_id == new_curie:
            edge.source_id = old_curie
        if edge.target_id == new_curie:
            edge.target_id = old_curie
        return edge

    @staticmethod
    def _get_cypher_for_query_node(qnode: QNode) -> str:
        qnode_type_cypher = f":{qnode.type}" if qnode.type and isinstance(qnode.type, str) else ""
        full_qnode_cypher = f"({qnode.id}{qnode_type_cypher})"
        return full_qnode_cypher

    @staticmethod
    def _get_cypher_for_query_edge(qedge: QEdge, enforce_directionality: bool) -> str:
        qedge_type_cypher = f":{qedge.type}" if qedge.type else ""
        full_qedge_cypher = f"-[{qedge.id}{qedge_type_cypher}]-"
        if enforce_directionality:
            full_qedge_cypher += ">"
        return full_qedge_cypher
