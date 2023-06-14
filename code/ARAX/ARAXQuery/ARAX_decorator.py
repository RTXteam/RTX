#!/bin/env python3
import copy
import os
import sqlite3
import sys
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Union

import ujson

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute
from openapi_server.models.edge import Edge


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXDecorator:

    def __init__(self, use_kg2c_sqlite: bool = True):
        self.node_attributes = {"iri": str, "description": str, "all_categories": list, "all_names": list,
                                "equivalent_curies": list, "publications": list}
        self.edge_attributes = {"publications": list, "publications_info": dict, "kg2_ids": list}
        self.attribute_shells = {
            "iri": Attribute(attribute_type_id="biolink:IriType",
                             value_type_id="metatype:Uri"),
            "description": Attribute(attribute_type_id="biolink:description",
                                     value_type_id="metatype:String"),
            "all_categories": Attribute(attribute_type_id="biolink:category",
                                        value_type_id="metatype:Uriorcurie",
                                        description="Categories of all nodes in this synonym set in RTX-KG2."),
            "all_names": Attribute(attribute_type_id="biolink:synonym",
                                   value_type_id="metatype:String",
                                   description="Names of all nodes in this synonym set in RTX-KG2."),
            "equivalent_curies": Attribute(attribute_type_id="biolink:xref",
                                           value_type_id="metatype:Nodeidentifier",
                                           description="Identifiers of all nodes in this synonym set in RTX-KG2."),
            "publications": Attribute(attribute_type_id="biolink:publications",
                                      value_type_id="biolink:Uriorcurie"),
            "publications_info": Attribute(attribute_type_id="bts:sentence",
                                           value_type_id=None),
            "kg2_ids": Attribute(attribute_type_id="biolink:original_predicate",
                                 value_type_id="metatype:String",
                                 description="The IDs of the original RTX-KG2pre edge(s) corresponding to this edge "
                                             "prior to any synonymization or remapping.")
        }
        self.array_delimiter_char = "ǂ"
        self.kg2_infores_curie = "infores:rtx-kg2"  # Can't use expand_utilities.py here due to circular imports
        self.use_kg2c_sqlite = use_kg2c_sqlite  # False means Chunyu's special XDTD KG2 data is used

    def decorate_nodes(self, response: ARAXResponse) -> ARAXResponse:
        message = response.envelope.message
        response.debug(f"Decorating nodes with metadata from KG2c")

        # Get connected to the local KG2c sqlite database
        connection, cursor = self._connect_to_sqlite()

        # Extract the KG2c nodes from sqlite
        response.debug(f"Looking up corresponding KG2c nodes in sqlite")
        node_attributes_ordered = list(self.node_attributes)
        node_keys = set(node_key.replace("'", "''") for node_key in message.knowledge_graph.nodes)  # Escape quotes
        node_keys_str = "','".join(node_keys)  # SQL wants ('node1', 'node2') format for string lists
        if self.use_kg2c_sqlite:
            node_cols_str = ", ".join([f"N.{property_name}" for property_name in node_attributes_ordered])
            sql_query = f"SELECT N.id, {node_cols_str} " \
                        f"FROM nodes AS N " \
                        f"WHERE N.id IN ('{node_keys_str}')"
        else:
            node_cols_str = ", ".join([property_name for property_name in node_attributes_ordered])
            sql_query = f"SELECT id, {node_cols_str} " \
                        f"FROM NODE_MAPPING_TABLE AS N " \
                        f"WHERE N.id IN ('{node_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decorate nodes in the KG with info in these KG2c nodes
        response.debug(f"Adding attributes to nodes in the KG")
        for row in rows:
            # First create the attributes for this KG2c node
            node_id = row[0]
            trapi_node = message.knowledge_graph.nodes[node_id]
            kg2c_node_attributes = []
            for index, property_name in enumerate(node_attributes_ordered):
                value = self._load_property(property_name, row[index + 1])  # Add one to account for 'id' column
                if value:
                    kg2c_node_attributes.append(self.create_attribute(property_name, value))

            # Then decorate the TRAPI node with those attributes it doesn't already have
            existing_attribute_triples = {self._get_attribute_triple(attribute)
                                          for attribute in trapi_node.attributes} if trapi_node.attributes else set()
            novel_attributes = [attribute for attribute in kg2c_node_attributes
                                if self._get_attribute_triple(attribute) not in existing_attribute_triples]
            if trapi_node.attributes:
                trapi_node.attributes += novel_attributes
            else:
                trapi_node.attributes = novel_attributes

        return response

    def decorate_edges(self, response: ARAXResponse, kind: Optional[str] = "RTX-KG2") -> ARAXResponse:
        """
        Decorates edges with publication sentences and any other available EPC info.
        kind: The kind of edges to decorate, either: "NGD" or "RTX-KG2". For NGD edges, publications info attributes
        are added. For RTX-KG2 edges, attributes for all EPC properties are added.
        """
        kg = response.envelope.message.knowledge_graph
        response.debug(f"Decorating edges with EPC info from KG2c")
        supported_kinds = {"RTX-KG2", "NGD"}
        if kind not in supported_kinds:
            response.error(f"Supported values for ARAXDecorator.decorate_edges()'s 'kind' parameter are: "
                           f"{supported_kinds}")
            return response

        # Figure out which edges we need to decorate
        if kind == "RTX-KG2":
            edge_keys_to_decorate = {edge_id for edge_id, edge in kg.edges.items()
                                     if edge.sources and any(retrieval_source.resource_id == self.kg2_infores_curie and
                                                             retrieval_source.resource_role == "aggregator_knowledge_source"
                                                             for retrieval_source in edge.sources)}
        else:
            edge_keys_to_decorate = {edge_id for edge_id, edge in kg.edges.items()
                                     if edge.predicate == "biolink:occurs_together_in_literature_with"}
        if not edge_keys_to_decorate:
            response.debug(f"Could not identify any {kind} edges to decorate")
        else:
            response.debug(f"Identified {len(edge_keys_to_decorate)} edges to decorate")

        # Determine the search keys for these edges that we need to look up in sqlite
        search_key_to_edge_keys_map = defaultdict(set)
        if kind == "NGD":  # For now only NGD/overlay will use this mode
            for edge_key in edge_keys_to_decorate:
                edge = kg.edges[edge_key]
                search_key = f"{edge.subject}--{edge.object}"
                search_key_to_edge_keys_map[search_key].add(edge_key)
            search_key_column = "node_pair"
        else:  # This is the mode used for decorating KG2 edges (or other KPs' edges)
            for edge_key in edge_keys_to_decorate:
                edge = kg.edges[edge_key]
                search_key = self._get_kg2c_edge_key(edge)
                search_key_to_edge_keys_map[search_key].add(edge_key)
            search_key_column = "triple"

        # Extract the proper entries from sqlite
        connection, cursor = self._connect_to_sqlite()
        response.debug(f"Looking up EPC edge info in KG2c sqlite")
        response.debug(f"Looking up corresponding KG2c nodes in sqlite")
        edge_attributes_ordered = list(self.edge_attributes)
        search_keys_set = set(search_key.replace("'", "''") for search_key in set(search_key_to_edge_keys_map))  # Escape quotes
        search_keys_str = "','".join(search_keys_set)  # SQL wants ('edge1', 'edge2') format for string lists
        if self.use_kg2c_sqlite:
            edge_cols_str = ", ".join([f"E.{property_name}" for property_name in edge_attributes_ordered])
            sql_query = f"SELECT E.{search_key_column}, {edge_cols_str} " \
                        f"FROM edges AS E " \
                        f"WHERE E.{search_key_column} IN ('{search_keys_str}')"
        else:
            edge_cols_str = ", ".join([property_name for property_name in edge_attributes_ordered])
            sql_query = f"SELECT triple, {edge_cols_str} " \
                        f"FROM EDGE_MAPPING_TABLE AS E " \
                        f"WHERE E.triple IN ('{search_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
            
        response.debug(f"Got {len(rows)} rows back from KG2c sqlite")

        response.debug(f"Adding attributes to edges in the KG")
        # Create a helper lookup map for easy access to returned rows
        search_key_to_kg2c_edge_tuples_map = defaultdict(list)
        for row in rows:
            search_key = row[0]
            search_key_to_kg2c_edge_tuples_map[search_key].append(row)

        attribute_type_id_map = {property_name: self.create_attribute(property_name, "something").attribute_type_id
                                 for property_name in set(self.edge_attributes)}
        for search_key, kg2c_edge_tuples in search_key_to_kg2c_edge_tuples_map.items():
            # Join the property values found for all edges matching the given search key
            merged_kg2c_properties = {property_name: None for property_name in edge_attributes_ordered}
            for kg2c_edge_tuple in kg2c_edge_tuples:
                for index, property_name in enumerate(edge_attributes_ordered):
                    raw_value = kg2c_edge_tuple[index + 1]
                    if raw_value:  # Skip empty attributes
                        value = self._load_property(property_name, raw_value)
                        if not merged_kg2c_properties.get(property_name):
                            merged_kg2c_properties[property_name] = set() if isinstance(value, list) else dict()
                        if isinstance(value, list):
                            merged_kg2c_properties[property_name].update(set(value))
                        else:
                            merged_kg2c_properties[property_name].update(value)
            joined_kg2_ids = list(merged_kg2c_properties["kg2_ids"]) if merged_kg2c_properties.get("kg2_ids") else set()
            joined_publications = list(merged_kg2c_properties["publications"]) if merged_kg2c_properties.get("publications") else set()
            joined_publications_info = merged_kg2c_properties["publications_info"] if merged_kg2c_properties.get("publications_info") else dict()

            # Add the joined attributes to each of the edges with the given search key (as needed)
            corresponding_bare_edge_keys = search_key_to_edge_keys_map[search_key]
            for edge_key in corresponding_bare_edge_keys:
                bare_edge = kg.edges[edge_key]
                primary_knowledge_source = self._get_primary_knowledge_source(bare_edge)
                existing_attribute_type_ids = {attribute.attribute_type_id for attribute in bare_edge.attributes} if bare_edge.attributes else set()
                new_attributes = []
                # Create KG2 edge-specific attributes
                if kind == "RTX-KG2":
                    if attribute_type_id_map["kg2_ids"] not in existing_attribute_type_ids:
                        new_attributes.append(self.create_attribute("kg2_ids", list(joined_kg2_ids)))
                    if joined_publications and attribute_type_id_map["publications"] not in existing_attribute_type_ids:
                        new_attributes.append(self.create_attribute("publications", list(joined_publications),
                                                                    attribute_source=primary_knowledge_source if primary_knowledge_source else None))
                # Create attributes that belong on both KG2 and NGD edges
                if joined_publications_info and attribute_type_id_map["publications_info"] not in existing_attribute_type_ids:
                    new_attributes.append(self.create_attribute("publications_info", joined_publications_info,
                                                                attribute_source=primary_knowledge_source if primary_knowledge_source else None))
                # Actually tack the new attributes onto the edge
                if new_attributes:
                    if not bare_edge.attributes:
                        bare_edge.attributes = new_attributes
                    else:
                        bare_edge.attributes += new_attributes

        return response

    def create_attribute(self, attribute_short_name: str, value: any, attribute_source: Optional[str] = None,
                         log: Optional[ARAXResponse] = ARAXResponse()) -> Attribute:
        if attribute_short_name not in self.attribute_shells:
            log.error(f"{attribute_short_name} is not a recognized short name for an attribute. Options are: "
                      f"{set(self.attribute_shells)}", error_code="UnrecognizedInput")
        attribute = copy.deepcopy(self.attribute_shells[attribute_short_name])
        attribute.value = value
        if isinstance(value, str):
            if value.startswith("http"):
                attribute.value_url = value
        if attribute_source:
            attribute.attribute_source = attribute_source
        return attribute

    def _get_kg2c_edge_key(self, edge: Edge) -> str:
        if self.use_kg2c_sqlite:
            qualifiers_dict = {qualifier.qualifier_type_id: qualifier.qualifier_value for qualifier in edge.qualifiers} if edge.qualifiers else dict()
            qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate", "")
            qualified_object_direction = qualifiers_dict.get("biolink:object_direction_qualifier", "")
            qualified_object_aspect = qualifiers_dict.get("biolink:object_aspect_qualifier", "")
            primary_knowledge_source = self._get_primary_knowledge_source(edge)

            qualified_portion = f"{qualified_predicate}--{qualified_object_direction}--{qualified_object_aspect}"
            edge_key = f"{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--{primary_knowledge_source}"
        else:
            edge_key = f"{edge.subject}--{edge.predicate}--{edge.object}"
        return edge_key

    @staticmethod
    def _get_primary_knowledge_source(edge: Edge) -> str:
        primary_ks_sources = [source.resource_id for source in edge.sources
                              if source.resource_role == "primary_knowledge_source"] if edge.sources else []
        return primary_ks_sources[0] if primary_ks_sources else ""

    def _connect_to_sqlite(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        if self.use_kg2c_sqlite:
            sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
            sqlite_name = rtxc.kg2c_sqlite_path.split('/')[-1]
        else:
            sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
            sqlite_name = rtxc.explainable_dtd_db_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()
        return connection, cursor

    def _load_property(self, property_name: str, raw_value: str) -> Union[str, List[str], Dict[str, any], None]:
        attributes_info_lookup = self.node_attributes if property_name in self.node_attributes else self.edge_attributes
        ultimate_value_type = attributes_info_lookup[property_name]
        if ultimate_value_type is list:
            return [item for item in raw_value.split(self.array_delimiter_char) if item]
        elif ultimate_value_type is dict:
            if '"' not in raw_value:
                raw_value = raw_value.replace("'", '"')
            try:
                return ujson.loads(raw_value)
            except:
                return {}
        else:
            return raw_value

    @staticmethod
    def _get_attribute_triple(attribute: Attribute) -> str:
        return f"{attribute.attribute_type_id}--{attribute.value}--{attribute.attribute_source}"



