#!/bin/env python3
import ast
import os
import sqlite3
import sys
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

import ujson

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand/")
import expand_utilities as eu


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXDecorator:

    def __init__(self):
        self.core_node_properties = {"id", "name", "category"}  # These don't belong in TRAPI Attributes
        self.arax_infores_curie = eu.get_translator_infores_curie("ARAX")
        self.kg2_infores_curie = eu.get_translator_infores_curie("RTX-KG2")

    def decorate_nodes(self, response: ARAXResponse) -> ARAXResponse:
        message = response.envelope.message
        response.debug(f"Decorating nodes with metadata from KG2c")

        # Get connected to the local KG2c sqlite database
        connection, cursor = self._connect_to_kg2c_sqlite()

        # Extract the KG2c nodes from sqlite
        response.debug(f"Looking up corresponding KG2c nodes in sqlite")
        node_keys = set(node_key.replace("'", "''") for node_key in message.knowledge_graph.nodes)  # Escape quotes
        node_keys_str = "','".join(node_keys)  # SQL wants ('node1', 'node2') format for string lists
        sql_query = f"SELECT N.node " \
                    f"FROM nodes AS N " \
                    f"WHERE N.id IN ('{node_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decorate nodes in the KG with info in these KG2c nodes
        response.debug(f"Adding attributes to nodes in the KG")
        for row in rows:
            kg2c_node_as_dict = ujson.loads(row[0])
            node_id = kg2c_node_as_dict["id"]
            kg2c_node_attributes = self._create_trapi_node_attributes(kg2c_node_as_dict)
            trapi_node = message.knowledge_graph.nodes[node_id]
            existing_attribute_triples = {eu.get_attribute_triple(attribute) for attribute in trapi_node.attributes} if trapi_node.attributes else set()
            novel_attributes = [attribute for attribute in kg2c_node_attributes
                                if eu.get_attribute_triple(attribute) not in existing_attribute_triples]
            if trapi_node.attributes:
                trapi_node.attributes += novel_attributes
            else:
                trapi_node.attributes = novel_attributes

        return response

    def decorate_edges(self, response: ARAXResponse, target_kp: Optional[str] = None,
                       target_predicate: Optional[str] = None, epc_attribute: Optional[str] = None) -> ARAXResponse:
        """
        Decorates edges with publication sentences and any other available EPC info.
        target_kp: If specified, only edges from this KP will be decorated
        target_predicate: If specified, only edges with this predicate will be decorated (use this for NGD)
        epc_attribute: If specified, only this attribute will be added (e.g., "publications_info")
        """
        kg = response.envelope.message.knowledge_graph
        response.debug(f"Decorating edges with EPC info from KG2c")

        # Figure out which edges we need to decorate
        kp_edge_keys = set()
        predicate_edge_keys = set()
        if target_kp:
            kp_infores_curie = eu.get_translator_infores_curie(target_kp)
            kp_types = {"biolink:aggregator_knowledge_source", "biolink:knowledge_source"}  # TODO: add others
            kp_edge_keys = {edge_id for edge_id, edge in kg.edges.items()
                            if edge.attributes and any(attribute.value == kp_infores_curie and
                                                       attribute.attribute_type_id in kp_types
                                                       for attribute in edge.attributes)}
        if target_predicate:
            predicate_edge_keys = {edge_id for edge_id, edge in kg.edges.items()
                                   if edge.predicate == target_predicate}
        if target_kp and target_predicate:
            edge_keys_to_decorate = kp_edge_keys.intersection(predicate_edge_keys)
        elif target_kp:
            edge_keys_to_decorate = kp_edge_keys
        elif target_predicate:
            edge_keys_to_decorate = predicate_edge_keys
        else:
            # Default to decorating all edges if no restrictions were passed in
            edge_keys_to_decorate = set(kg.edges)
        if not edge_keys_to_decorate:
            response.debug(f"Could not identify any edges to decorate that matched the specified criteria")
        else:
            response.debug(f"Identified {len(edge_keys_to_decorate)} edges to decorate")

        # Determine the search keys for these edges that we need to look up in sqlite
        search_key_to_edge_keys_map = defaultdict(set)
        if target_predicate:  # For now only NGD/overlay will use this mode
            for edge_key in edge_keys_to_decorate:
                edge = kg.edges[edge_key]
                search_key = f"{edge.subject}--{edge.object}"
                search_key_to_edge_keys_map[search_key].add(edge_key)
            search_key_column = "node_pair"
        else:  # This is the mode used for decorating KG2 edges (or other KPs' edges)
            for edge_key in edge_keys_to_decorate:
                edge = kg.edges[edge_key]
                search_key = f"{edge.subject}--{edge.predicate}--{edge.object}"
                search_key_to_edge_keys_map[search_key].add(edge_key)
            search_key_column = "triple"

        # Extract the proper entries from sqlite
        connection, cursor = self._connect_to_kg2c_sqlite()
        response.debug(f"Looking up EPC edge info in KG2c sqlite")
        search_keys_set = set(search_key.replace("'", "''") for search_key in set(search_key_to_edge_keys_map))  # Escape quotes
        search_keys_str = "','".join(search_keys_set)  # SQL wants ('node1', 'node2') format for string lists
        sql_query = f"SELECT E.{search_key_column}, E.edge " \
                    f"FROM edges AS E " \
                    f"WHERE E.{search_key_column} IN ('{search_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decorate edges in the KG with info extracted from sqlite
        response.debug(f"Adding attributes to edges in the KG")
        search_key_to_kg2c_edges_map = defaultdict(list)
        for row in rows:
            search_key_to_kg2c_edges_map[row[0]].append(ujson.loads(row[1]))
        for search_key, kg2c_edges in search_key_to_kg2c_edges_map.items():
            joined_publications = set()
            joined_publications_info = dict()
            joined_kg2_ids = set()
            joined_knowledge_sources = set()
            for kg2c_edge in kg2c_edges:
                joined_publications.update(set(kg2c_edge.get("publications", [])))
                joined_publications_info.update(kg2c_edge.get("publications_info", dict()))
                joined_kg2_ids.update(set(kg2c_edge.get("kg2_ids", [])))
                joined_knowledge_sources.update(set(kg2c_edge.get("knowledge_source", [])))
            # Add the joined attributes to each of the edges with the given search key
            corresponding_bare_edge_keys = search_key_to_edge_keys_map[search_key]
            for edge_key in corresponding_bare_edge_keys:
                bare_edge = kg.edges[edge_key]
                if joined_publications and (epc_attribute in {None, "publications"}):
                    publications_attribute = Attribute(attribute_type_id="biolink:has_supporting_publications",
                                                       value_type_id="biolink:Publication",
                                                       value=list(joined_publications),
                                                       attribute_source=list(joined_knowledge_sources)[0] if len(joined_knowledge_sources) == 1 else None)
                    if not bare_edge.attributes:
                        bare_edge.attributes = []
                    bare_edge.attributes.append(publications_attribute)
                if joined_publications_info and (epc_attribute in {None, "publications_info"}):
                    publications_attribute = Attribute(attribute_type_id="biolink:supporting_publication_info",
                                                       value_type_id="biolink:Publication",
                                                       value=joined_publications_info,
                                                       attribute_source=list(joined_knowledge_sources)[0] if len(joined_knowledge_sources) == 1 else None)
                    if not bare_edge.attributes:
                        bare_edge.attributes = []
                    bare_edge.attributes.append(publications_attribute)
                if target_kp == "RTX-KG2" and (epc_attribute in {None, "kg2_ids"}):
                    kg2_ids_attribute = Attribute(attribute_type_id="biolink:original_edge_information",
                                                  value_type_id="biolink:Unknown",
                                                  value=list(joined_kg2_ids),
                                                  description="The original edges corresponding to this edge prior to "
                                                              "any synonymization or remapping. Listed in "
                                                              "(subject)--(relation)--(object)--(source) format.",
                                                  attribute_source=self.kg2_infores_curie)
                    if not bare_edge.attributes:
                        bare_edge.attributes = []
                    bare_edge.attributes.append(kg2_ids_attribute)

        return response

    def _create_trapi_node_attributes(self, kg2c_dict_node: Dict[str, any]) -> List[Attribute]:
        new_attributes = []
        for property_name in set(kg2c_dict_node).difference(self.core_node_properties):
            property_value = kg2c_dict_node.get(property_name)
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
    def _connect_to_kg2c_sqlite() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
        sqlite_name = rtxc.kg2c_sqlite_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()
        return connection, cursor



