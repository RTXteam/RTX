#!/bin/env python3
import ast
import copy
import os
import sqlite3
import sys
from typing import List, Dict, Set, Optional

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
            "kg2_ids": Attribute(attribute_type_id="biolink:original_edge_information",
                                 value_type_id="metatype:String",
                                 description="The original RTX-KG2pre edges corresponding to this edge prior to any "
                                             "synonymization or remapping. Listed in "
                                             "(subject)--(relation)--(object)--(source) format.")
        }

    def apply(self, response: ARAXResponse) -> ARAXResponse:
        message = response.envelope.message
        response.debug(f"Decorating nodes with metadata from KG2c")

        # Get connected to the local KG2c sqlite database (look up its path using database manager-friendly method)
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
        sqlite_name = rtxc.kg2c_sqlite_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()

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
            kg2c_node_attributes = self._create_trapi_attributes(kg2c_node_as_dict, response)
            trapi_node = message.knowledge_graph.nodes[node_id]
            existing_attribute_triples = {eu.get_attribute_triple(attribute) for attribute in trapi_node.attributes} if trapi_node.attributes else set()
            novel_attributes = [attribute for attribute in kg2c_node_attributes
                                if eu.get_attribute_triple(attribute) not in existing_attribute_triples]
            if trapi_node.attributes:
                trapi_node.attributes += novel_attributes
            else:
                trapi_node.attributes = novel_attributes

        return response

    def create_attribute(self, attribute_short_name: str, value: any, attribute_source: Optional[str] = None,
                         log: Optional[ARAXResponse] = ARAXResponse()) -> Attribute:
        if attribute_short_name not in self.attribute_shells:
            log.error(f"{attribute_short_name} is not a recognized short name for an attribute. Options are: "
                      f"{set(self.attribute_shells)}", error_code="UnrecognizedInput")
        attribute = copy.deepcopy(self.attribute_shells[attribute_short_name])
        attribute.value = value
        if isinstance(value, str) and value.startswith("http"):
            attribute.value_url = value
        if attribute_source:
            attribute.attribute_source = attribute_source
        return attribute

    def _create_trapi_attributes(self, kg2c_dict_node: Dict[str, any], response: ARAXResponse) -> List[Attribute]:
        new_attributes = []
        for property_name in set(kg2c_dict_node).difference(self.core_node_properties).difference({"expanded_categories"}):
            property_value = kg2c_dict_node.get(property_name)
            if property_value:
                # Extract any booleans that are stored within strings
                if type(property_value) is str:
                    if property_value.lower() == "true" or property_value.lower() == "false":
                        property_value = ast.literal_eval(property_value)
                trapi_attribute = self.create_attribute(property_name, property_value, 'foo', response)
                # Also store this value in Attribute.value_url if it's a URL

                new_attributes.append(trapi_attribute)
        return new_attributes

