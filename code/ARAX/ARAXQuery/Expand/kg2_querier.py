#!/bin/env python3
import csv

import requests_cache
import ujson
import sqlite3
import sys
import os
import time
import traceback
import ast
import pathlib
from typing import List, Dict, Tuple, Set, Union
from datetime import datetime, timedelta

import requests
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

    def __init__(self, response_object: ARAXResponse):
        self.response = response_object
        self.enforce_directionality = self.response.data['parameters'].get('enforce_directionality')
        self.infores_curie_tsv_name = "kg2-provided-by-curie-to-infores-curie.tsv"
        self.infores_curie_tsv_path = f"{os.path.dirname(os.path.abspath(__file__))}/{self.infores_curie_tsv_name}"
        self.infores_curie_map = self._initiate_infores_curie_map(self.response)
        self.canonical_predicate_map = eu.load_canonical_predicates_map(self.response)

    def answer_one_hop_query(self, query_graph: QueryGraph) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a one-hop (single-edge) query using KG2c, via PloverDB.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.response
        final_kg = QGOrganizedKnowledgeGraph()

        # Verify this is a valid one-hop query graph
        if len(query_graph.edges) != 1:
            log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg
        if len(query_graph.nodes) != 2:
            log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                      f"{query_graph.to_dict()}", error_code="InvalidQuery")
            return final_kg

        # Get canonical versions of the input curies
        qnode_keys_with_curies = [qnode_key for qnode_key, qnode in query_graph.nodes.items() if qnode.ids]
        for qnode_key in qnode_keys_with_curies:
            qnode = query_graph.nodes[qnode_key]
            canonical_curies = eu.get_canonical_curies_list(qnode.ids, log)
            log.debug(f"Using {len(canonical_curies)} curies as canonical curies for qnode {qnode_key}")
            qnode.ids = canonical_curies
            qnode.categories = None  # Important to clear this, otherwise results are limited (#889)

        # Send request to Plover
        plover_answer, response_status = self._answer_query_using_plover(query_graph, log)
        if response_status == 200:
            final_kg = self._load_plover_answer_into_object_model(plover_answer, log)
        else:
            log.error(f"Plover returned response of {response_status}. Answer was: {plover_answer}", error_code="RequestFailed")

        return final_kg

    def answer_single_node_query(self, single_node_qg: QueryGraph) -> QGOrganizedKnowledgeGraph:
        log = self.response
        qnode_key = next(qnode_key for qnode_key in single_node_qg.nodes)
        qnode = single_node_qg.nodes[qnode_key]
        final_kg = QGOrganizedKnowledgeGraph()

        # Convert qnode curies as needed (either to synonyms or to canonical versions)
        if qnode.ids:
            qnode.ids = eu.get_canonical_curies_list(qnode.ids, log)
            qnode.categories = None  # Important to clear this to avoid discrepancies in types for particular concepts

        # Send request to plover
        plover_answer, response_status = self._answer_query_using_plover(single_node_qg, log)
        if response_status == 200:
            final_kg = self._load_plover_answer_into_object_model(plover_answer, log)
        else:
            log.error(f"Plover returned response of {response_status}. Answer was: {plover_answer}", error_code="RequestFailed")

        return final_kg

    @staticmethod
    def _answer_query_using_plover(qg: QueryGraph, log: ARAXResponse) -> Tuple[Dict[str, Dict[str, Union[set, dict]]], int]:
        rtxc = RTXConfiguration()
        rtxc.live = "Production"
        log.debug(f"Sending query to Plover")
        dict_qg = qg.to_dict()
        dict_qg["include_metadata"] = True  # Ask plover to return node/edge objects (not just IDs)
        response = requests.post(f"{rtxc.plover_url}/query", json=dict_qg, timeout=60,
                                 headers={'accept': 'application/json'})
        if response.status_code == 200:
            log.debug(f"Got response back from Plover")
            return response.json(), response.status_code
        else:
            log.warning(f"Plover returned a status code of {response.status_code}. Response was: {response.text}")
            return dict(), response.status_code

    def _load_plover_answer_into_object_model(self, plover_answer: Dict[str, Dict[str, Union[set, dict]]],
                                              log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        # Figure out whether this response returned only node/edge IDs or node/edge objects themselves
        nodes_entries = [nodes for nodes in plover_answer["nodes"].values()]
        first_nodes_entry = nodes_entries[0] if nodes_entries else dict()
        response_includes_metadata = True if isinstance(first_nodes_entry, dict) else False
        if response_includes_metadata:
            answer_kg = QGOrganizedKnowledgeGraph()

            # Load returned nodes into TRAPI object model
            for qnode_key, nodes in plover_answer["nodes"].items():
                num_nodes = len(nodes)
                log.debug(f"Loading {num_nodes} {qnode_key} nodes into TRAPI object model")
                start = time.time()
                for node_key, node_tuple in nodes.items():
                    node = self._convert_kg2c_plover_node_to_trapi_node(node_tuple)
                    answer_kg.add_node(node_key, node, qnode_key)
                log.debug(f"Loading {num_nodes} {qnode_key} nodes into TRAPI object model took "
                          f"{round(time.time() - start, 2)} seconds")

            # Load returned edges into TRAPI object model
            for qedge_key, edges in plover_answer["edges"].items():
                num_edges = len(edges)
                log.debug(f"Loading {num_edges} edges into TRAPI object model")
                start = time.time()
                for edge_key, edge_tuple in edges.items():
                    edge = self._convert_kg2c_plover_edge_to_trapi_edge(edge_tuple, log)
                    answer_kg.add_edge(edge_key, edge, qedge_key)
                log.debug(f"Loading {num_edges} {qedge_key} edges into TRAPI object model took "
                          f"{round(time.time() - start, 2)} seconds")

            return answer_kg
        else:
            return self._grab_nodes_and_edges_from_sqlite(plover_answer, log)

    def _grab_nodes_and_edges_from_sqlite(self, plover_answer: Dict[str, Dict[str, Set[Union[str, int]]]],
                                          log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        # Get connected to the local sqlite database (look up its path using database manager-friendly method)
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
        sqlite_name = rtxc.kg2c_sqlite_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()
        answer_kg = QGOrganizedKnowledgeGraph()

        # Grab the node objects from sqlite corresponding to the returned node IDs
        num_nodes = sum([len(nodes) for nodes in plover_answer["nodes"].values()])
        start = time.time()
        for qnode_key, node_keys in plover_answer["nodes"].items():
            node_keys_str = "','".join(node_keys)  # SQL wants ('node1', 'node2') format for string lists
            sql_query = f"SELECT N.node " \
                        f"FROM nodes AS N " \
                        f"WHERE N.id IN ('{node_keys_str}')"
            log.debug(
                f"Looking up {len(plover_answer['nodes'][qnode_key])} returned {qnode_key} node IDs in KG2c sqlite")
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            for row in rows:
                node_as_dict = ujson.loads(row[0])
                node_key, node = self._convert_kg2c_node_to_trapi_node(node_as_dict)
                answer_kg.add_node(node_key, node, qnode_key)
        log.debug(f"Grabbing {num_nodes} nodes from sqlite and loading into object model took "
                  f"{round(time.time() - start, 2)} seconds")

        # Grab the edge objects from sqlite corresponding to the returned edge IDs
        num_edges = sum([len(edges) for edges in plover_answer["edges"].values()])
        start = time.time()
        for qedge_key, edge_keys in plover_answer["edges"].items():
            edge_keys_str = ",".join(str(edge_key) for edge_key in edge_keys)  # SQL wants (1, 2) format int lists
            sql_query = f"SELECT E.edge " \
                        f"FROM edges AS E " \
                        f"WHERE E.id IN ({edge_keys_str})"
            log.debug(
                f"Looking up {len(plover_answer['edges'][qedge_key])} returned {qedge_key} edge IDs in KG2c sqlite")
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            for row in rows:
                edge_as_dict = ujson.loads(row[0])
                edge_key, edge = self._convert_kg2c_edge_to_trapi_edge(edge_as_dict)
                answer_kg.add_edge(edge_key, edge, qedge_key)
        log.debug(f"Grabbing {num_edges} edges from sqlite and loading into object model took "
                  f"{round(time.time() - start, 2)} seconds")

        cursor.close()
        connection.close()
        return answer_kg

    @staticmethod
    def _convert_kg2c_plover_node_to_trapi_node(node_tuple: list) -> Node:
        node = Node(name=node_tuple[0], categories=eu.convert_to_list(node_tuple[1]))
        return node

    def _convert_kg2c_plover_edge_to_trapi_edge(self, edge_tuple: list, log: ARAXResponse) -> Edge:
        edge = Edge(subject=edge_tuple[0], object=edge_tuple[1], predicate=edge_tuple[2], attributes=[])
        provided_bys = edge_tuple[3]
        publications = edge_tuple[4]
        # Add any provided_bys missing from the spreadsheet to our map
        missing_provided_bys = set(provided_bys).difference(set(self.infores_curie_map))
        for source in missing_provided_bys:
            self.infores_curie_map[source] = {"curie": self._get_infores_curie_from_provided_by(source, log),
                                              "type": "biolink:knowledge_source"}

        # Indicate that this edge came from the KG2 KP
        kg2_infores_curie = eu.get_translator_infores_curie("RTX-KG2")
        edge.attributes.append(Attribute(attribute_type_id="biolink:aggregator_knowledge_source",
                                         value=kg2_infores_curie,
                                         value_type_id="biolink:InformationResource",
                                         attribute_source=kg2_infores_curie))
        # Create knowledge source attributes for each of the provided_bys
        provided_by_attributes = [Attribute(attribute_type_id=self.infores_curie_map[source]["type"],
                                            value=self.infores_curie_map[source]["curie"],
                                            value_type_id="biolink:InformationResource",
                                            attribute_source=eu.get_translator_infores_curie("RTX-KG2"))
                                  for source in provided_bys]
        edge.attributes += provided_by_attributes
        # Create an attribute containing any publications
        if publications:
            infores_curies = {attribute.value for attribute in provided_by_attributes}
            edge.attributes.append(Attribute(attribute_type_id="biolink:has_supporting_publications",
                                             value_type_id="biolink:Publication",
                                             value=publications,
                                             attribute_source=infores_curies if len(infores_curies) == 1 else None))

        # Switch to canonical predicate as needed (temporary patch until KG2 uses only canonical predicates)
        if edge.predicate in self.canonical_predicate_map:
            edge.predicate = self.canonical_predicate_map[edge.predicate]
            original_subject = edge.subject
            edge.subject = edge.object
            edge.object = original_subject

        return edge

    def _get_infores_curie_from_provided_by(self, provided_by: str, log: ARAXResponse) -> str:
        # This is a backup method in case a provided_by is missing from the infores mappings
        log.warning(f"KG2 edge uses a provided_by not listed in {self.infores_curie_tsv_name}: {provided_by}")
        stripped = provided_by.strip(":")  # Handle SEMMEDDB: situation
        local_id = stripped.split(":")[-1]
        before_dot = local_id.split(".")[0]
        before_slash = before_dot.split("/")[0]
        infores_curie = f"infores:{before_slash.lower()}"
        return infores_curie

    def _initiate_infores_curie_map(self, log: ARAXResponse) -> Dict[str, Dict[str, str]]:
        # Grab (or refresh) the spreadsheet of mappings from the KG2 repo
        infores_map_file = pathlib.Path(self.infores_curie_tsv_path)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        if not infores_map_file.exists() or datetime.fromtimestamp(infores_map_file.stat().st_mtime) < twenty_four_hours_ago:
            log.debug(f"Grabbing provided-by-to-infores-curie TSV from RTX-KG2 repo")
            with requests_cache.disabled():
                response = requests.get(f"https://raw.githubusercontent.com/RTXteam/RTX-KG2/master/{self.infores_curie_tsv_name}", timeout=10)
                if response.status_code == 200:
                    # Save this as a tsv file locally
                    with open(self.infores_curie_tsv_path, "w+") as local_tsv_file:
                        local_tsv_file.write(response.text)
                else:
                    log.warning(f"Unable to grab provided-by-to-infores-curie TSV from RTX-KG2 repo; will proceed but "
                                f"infores curies may not be accurate")
        # Now that we have the TSV locally, load it into a dictionary
        log.debug(f"Loading provided-by-to-infores-curie info into a map")
        infores_curie_map = dict()
        try:
            with open(self.infores_curie_tsv_path) as tsv_file:
                reader = csv.reader(tsv_file, delimiter="\t")
                next(reader)  # Skip headers
                for row in reader:
                    source_type_raw = row[2] if row[2] else "biolink:knowledge_source"
                    source_type = f"biolink:{source_type_raw}" if not source_type_raw.startswith("biolink:") else source_type_raw
                    infores_curie_map[row[0]] = {"curie": row[1], "type": source_type}
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            log.warning(f"Ran into a problem parsing provided-by-to-infores-curie TSV; will proceed but infores curies"
                        f"may not be accurate. {tb}")
        return infores_curie_map

    # -------------- LEGACY FUNCTIONS (EXPAND NO LONGER USES THESE, BUT OTHER MODULES MAY) ------------------------ #

    def _answer_query_using_neo4j(self, qg: QueryGraph, kg_name: str, qedge_key: str, enforce_directionality: bool,
                                  log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        answer_kg = QGOrganizedKnowledgeGraph()
        cypher_query = self._convert_one_hop_query_graph_to_cypher_query(qg, enforce_directionality, log)
        if log.status != 'OK':
            return answer_kg
        neo4j_results = self._send_query_to_neo4j(cypher_query, qedge_key, kg_name, log)
        if log.status != 'OK':
            return answer_kg
        answer_kg = self._load_neo4j_answers_into_kg(neo4j_results, kg_name, qg, log)
        if log.status != 'OK':
            return answer_kg

        return answer_kg

    def _answer_single_node_query_using_neo4j(self, qnode_key: str, qg: QueryGraph, kg_name: str, log: ARAXResponse):
        qnode = qg.nodes[qnode_key]
        answer_kg = QGOrganizedKnowledgeGraph()

        # Build and run a cypher query to get this node/nodes
        where_clause = f"{qnode_key}.id='{qnode.ids}'" if len(qnode.ids) == 1 else f"{qnode_key}.id in {qnode.ids}"
        cypher_query = f"MATCH {self._get_cypher_for_query_node(qnode_key, qg)} WHERE {where_clause} RETURN {qnode_key}"
        log.info(f"Sending cypher query for node {qnode_key} to {kg_name} neo4j")
        results = self._run_cypher_query(cypher_query, kg_name, log)

        # Load the results into API object model and add to our answer knowledge graph
        for result in results:
            neo4j_node = result.get(qnode_key)
            node_key, node = self._convert_neo4j_node_to_trapi_node(neo4j_node, kg_name)
            answer_kg.add_node(node_key, node, qnode_key)

        return answer_kg

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
                if qnode.ids and len(qnode.ids) > 1:
                    where_fragments.append(f"{qnode_key}.id in {qnode.ids}")
                if qnode.categories and len(qnode.categories) > 1:
                    # Create where fragment that looks like 'n00:biolink:Disease OR n00:biolink:PhenotypicFeature..'
                    category_sub_fragments = [f"{qnode_key}:`{category}`" for category in qnode.categories]
                    categories_where_fragment = f"({' OR '.join(category_sub_fragments)})"
                    where_fragments.append(categories_where_fragment)
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

    def _send_query_to_neo4j(self, cypher_query: str, qedge_key: str, kg_name: str, log: ARAXResponse) -> List[Dict[str, List[Dict[str, any]]]]:
        log.info(f"Sending cypher query for edge {qedge_key} to {kg_name} neo4j")
        results_from_neo4j = self._run_cypher_query(cypher_query, kg_name, log)
        if log.status == 'OK':
            columns_with_lengths = dict()
            for column in results_from_neo4j[0]:
                columns_with_lengths[column] = len(results_from_neo4j[0].get(column))
        return results_from_neo4j

    def _load_neo4j_answers_into_kg(self, neo4j_results: List[Dict[str, List[Dict[str, any]]]], kg_name: str,
                                    qg: QueryGraph, log: ARAXResponse) -> QGOrganizedKnowledgeGraph:
        log.debug(f"Processing query results for edge {next(qedge_key for qedge_key in qg.edges)}")
        final_kg = QGOrganizedKnowledgeGraph()

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
                    edge_key, edge = self._convert_neo4j_edge_to_trapi_edge(neo4j_edge, kg_name)
                    final_kg.add_edge(edge_key, edge, column_qedge_key)

        return final_kg

    def _convert_neo4j_node_to_trapi_node(self, neo4j_node: Dict[str, any], kp: str) -> Tuple[str, Node]:
        if kp == "KG2":
            return self._convert_kg2_node_to_trapi_node(neo4j_node)
        else:
            return self._convert_kg2c_node_to_trapi_node(neo4j_node)

    def _convert_kg2_node_to_trapi_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        node = Node()
        node_key = neo4j_node.get('id')
        node.name = neo4j_node.get('name')
        node.categories = eu.convert_to_list(neo4j_node.get('category'))
        # Add all additional properties on KG2 nodes as TRAPI Attribute objects
        other_properties = ["iri", "full_name", "description", "publications", "synonym", "provided_by",
                            "deprecated", "update_date"]
        node.attributes = self._create_trapi_attributes(other_properties, neo4j_node)
        return node_key, node

    def _convert_kg2c_node_to_trapi_node(self, neo4j_node: Dict[str, any]) -> Tuple[str, Node]:
        node = Node()
        node_key = neo4j_node.get('id')
        node.name = neo4j_node.get('name')
        node.categories = eu.convert_to_list(neo4j_node.get('category'))
        # Add all additional properties on KG2c nodes as TRAPI Attribute objects
        other_properties = ["iri", "description", "all_names", "all_categories", "expanded_categories",
                            "equivalent_curies", "publications"]
        node.attributes = self._create_trapi_attributes(other_properties, neo4j_node)
        return node_key, node

    def _convert_neo4j_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any],
                                          kg_name: str) -> Tuple[str, Edge]:
        if kg_name == "KG2":
            return self._convert_kg2_edge_to_trapi_edge(neo4j_edge)
        else:
            return self._convert_kg2c_edge_to_trapi_edge(neo4j_edge)

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
        return edge_key, edge

    def _convert_kg2c_edge_to_trapi_edge(self, neo4j_edge: Dict[str, any]) -> Tuple[str, Edge]:
        edge = Edge()
        edge.predicate = neo4j_edge.get("predicate")
        edge.subject = neo4j_edge.get("subject")
        edge.object = neo4j_edge.get("object")
        edge_key = f"KG2c:{edge.subject}-{edge.predicate}-{edge.object}"
        other_properties = ["provided_by", "publications"]
        edge.attributes = self._create_trapi_attributes(other_properties, neo4j_edge)
        return edge_key, edge

    @staticmethod
    def _create_trapi_attributes(property_names: List[str], neo4j_object: Dict[str, any]) -> List[Attribute]:
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            if property_value:
                # Extract any booleans that are stored within strings
                if type(property_value) is str:
                    if property_value.lower() == "true" or property_value.lower() == "false":
                        property_value = ast.literal_eval(property_value)
                # Create the actual Attribute object
                trapi_attribute = Attribute(original_attribute_name=property_name,
                                            attribute_type_id=eu.get_attribute_type(property_name),
                                            value=property_value)
                # Also store this value in Attribute.url if it's a URL
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    trapi_attribute.value_url = property_value

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
    def _get_cypher_for_query_node(qnode_key: str, qg: QueryGraph) -> str:
        qnode = qg.nodes[qnode_key]
        # Add in node label if there's only one category
        category_cypher = f":`{qnode.categories[0]}`" if qnode.categories and len(qnode.categories) == 1 else ""
        if qnode.ids and len(qnode.ids) == 1:
            curie_cypher = f" {{id:'{qnode.ids[0]}'}}"
        else:
            curie_cypher = ""
        qnode_cypher = f"({qnode_key}{category_cypher}{curie_cypher})"
        return qnode_cypher

    @staticmethod
    def _get_cypher_for_query_edge(qedge_key: str, qg: QueryGraph, enforce_directionality: bool) -> str:
        qedge = qg.edges[qedge_key]
        predicate_cypher = "|".join([f":`{predicate}`" for predicate in qedge.predicates]) if qedge.predicates else ""
        full_qedge_cypher = f"-[{qedge_key}{predicate_cypher}]-"
        if enforce_directionality:
            full_qedge_cypher += ">"
        return full_qedge_cypher
