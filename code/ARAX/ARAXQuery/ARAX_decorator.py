#!/bin/env python3
import copy
import os
import sqlite3
import sys
from collections import defaultdict
from typing import Optional, Union, Any, DefaultDict

import ujson

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
from util import get_arax_edge_key
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute
from openapi_server.models.edge import Edge


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXDecorator:

    def __init__(self):
        self.node_attributes = {
            "description": str,
            "synonym": list,
            "equivalent_identifiers": list,
            "information_content": str,
            "xref": list,
            "symbol": str,
            "full_name": str,
            "in_taxon_label": str,
            "inheritance": str,
            "chembl_availability_type": str,
            "chembl_black_box_warning": str,
            "chembl_natural_product": str,
            "chembl_prodrug": str,
        }
        self.edge_attributes = {
            "publications": list,
            "knowledge_level": str,
            "agent_type": str,
            "description": str,
            "supporting_text": str,
            "p_value": str,
            "adjusted_p_value": str,
            "evidence_count": str,
            "clinical_approval_status": str,
            "FDA_regulatory_approvals": list,
            "negated": str,
            "update_date": str,
            "original_subject": str,
            "original_predicate": str,
            "original_object": str,
            "qualifier": str,
            "anatomical_context_qualifier": str,
            "causal_mechanism_qualifier": str,
            "disease_context_qualifier": str,
            "frequency_qualifier": str,
            "onset_qualifier": str,
            "object_form_or_variant_qualifier": str,
            "sex_qualifier": str,
            "species_context_qualifier": str,
            "stage_qualifier": str,
            "subject_aspect_qualifier": str,
            "subject_direction_qualifier": str,
            "subject_form_or_variant_qualifier": str,
        }
        self.attribute_shells = {
            # Node-side
            "description": Attribute(attribute_type_id="biolink:description",
                                     value_type_id="metatype:String"),
            "synonym": Attribute(attribute_type_id="biolink:synonym",
                                 value_type_id="metatype:String",
                                 description="Synonyms / alternate names for this node from the tier0 synonym cluster."),
            "equivalent_identifiers": Attribute(attribute_type_id="biolink:same_as",
                                                value_type_id="metatype:Nodeidentifier",
                                                description="Identifiers of all nodes in this synonym cluster in the tier0 graph."),
            "information_content": Attribute(attribute_type_id="biolink:has_information_content",
                                             value_type_id="metatype:Float"),
            "xref": Attribute(attribute_type_id="biolink:xref",
                              value_type_id="metatype:Nodeidentifier"),
            "symbol": Attribute(attribute_type_id="biolink:symbol",
                                value_type_id="metatype:String"),
            "full_name": Attribute(attribute_type_id="biolink:full_name",
                                   value_type_id="metatype:String"),
            "in_taxon_label": Attribute(attribute_type_id="biolink:in_taxon_label",
                                        value_type_id="metatype:String"),
            "inheritance": Attribute(attribute_type_id="biolink:inheritance",
                                     value_type_id="metatype:String"),
            "chembl_availability_type": Attribute(attribute_type_id="biolink:chembl_availability_type",
                                                  value_type_id="metatype:String"),
            "chembl_black_box_warning": Attribute(attribute_type_id="biolink:chembl_black_box_warning",
                                                  value_type_id="metatype:Boolean"),
            "chembl_natural_product": Attribute(attribute_type_id="biolink:chembl_natural_product",
                                                value_type_id="metatype:Boolean"),
            "chembl_prodrug": Attribute(attribute_type_id="biolink:chembl_prodrug",
                                        value_type_id="metatype:Boolean"),
            # Edge-side
            "knowledge_level": Attribute(attribute_type_id="biolink:knowledge_level",
                                         value_type_id="biolink:KnowledgeLevelEnum"),
            "agent_type": Attribute(attribute_type_id="biolink:agent_type",
                                    value_type_id="biolink:AgentTypeEnum"),
            "publications": Attribute(attribute_type_id="biolink:publications",
                                      value_type_id="biolink:Uriorcurie"),
            "supporting_text": Attribute(attribute_type_id="biolink:supporting_text",
                                         value_type_id="metatype:String"),
            "p_value": Attribute(attribute_type_id="biolink:p_value",
                                 value_type_id="metatype:Float"),
            "adjusted_p_value": Attribute(attribute_type_id="biolink:adjusted_p_value",
                                          value_type_id="metatype:Float"),
            "evidence_count": Attribute(attribute_type_id="biolink:evidence_count",
                                        value_type_id="metatype:Integer"),
            "clinical_approval_status": Attribute(attribute_type_id="biolink:clinical_approval_status",
                                                  value_type_id="metatype:String"),
            "FDA_regulatory_approvals": Attribute(attribute_type_id="biolink:FDA_regulatory_approvals",
                                                  value_type_id="metatype:String"),
            "negated": Attribute(attribute_type_id="biolink:negated",
                                 value_type_id="metatype:Boolean"),
            "update_date": Attribute(attribute_type_id="biolink:update_date",
                                     value_type_id="metatype:Date"),
            "original_subject": Attribute(attribute_type_id="biolink:original_subject",
                                          value_type_id="metatype:String"),
            "original_predicate": Attribute(attribute_type_id="biolink:original_predicate",
                                            value_type_id="metatype:String"),
            "original_object": Attribute(attribute_type_id="biolink:original_object",
                                         value_type_id="metatype:String"),
            "qualifier": Attribute(attribute_type_id="biolink:qualifier",
                                   value_type_id="metatype:String"),
            "anatomical_context_qualifier": Attribute(attribute_type_id="biolink:anatomical_context_qualifier",
                                                      value_type_id="metatype:String"),
            "causal_mechanism_qualifier": Attribute(attribute_type_id="biolink:causal_mechanism_qualifier",
                                                    value_type_id="metatype:String"),
            "disease_context_qualifier": Attribute(attribute_type_id="biolink:disease_context_qualifier",
                                                   value_type_id="metatype:String"),
            "frequency_qualifier": Attribute(attribute_type_id="biolink:frequency_qualifier",
                                             value_type_id="metatype:String"),
            "onset_qualifier": Attribute(attribute_type_id="biolink:onset_qualifier",
                                         value_type_id="metatype:String"),
            "object_form_or_variant_qualifier": Attribute(attribute_type_id="biolink:object_form_or_variant_qualifier",
                                                          value_type_id="metatype:String"),
            "sex_qualifier": Attribute(attribute_type_id="biolink:sex_qualifier",
                                       value_type_id="metatype:String"),
            "species_context_qualifier": Attribute(attribute_type_id="biolink:species_context_qualifier",
                                                   value_type_id="metatype:String"),
            "stage_qualifier": Attribute(attribute_type_id="biolink:stage_qualifier",
                                         value_type_id="metatype:String"),
            "subject_aspect_qualifier": Attribute(attribute_type_id="biolink:subject_aspect_qualifier",
                                                  value_type_id="metatype:String"),
            "subject_direction_qualifier": Attribute(attribute_type_id="biolink:subject_direction_qualifier",
                                                     value_type_id="metatype:String"),
            "subject_form_or_variant_qualifier": Attribute(attribute_type_id="biolink:subject_form_or_variant_qualifier",
                                                           value_type_id="metatype:String"),
        }
        self.array_delimiter_char = "ǂ"
        self.tier0_infores_curie = "infores:dogpark-tier0"  # Can't use expand_utilities.py here due to circular imports

    def decorate_nodes(self, response: ARAXResponse, only_decorate_bare: bool = False) -> ARAXResponse:
        message = response.envelope.message
        response.debug("Decorating nodes with metadata from tier0")

        # Get connected to the local tier0 sqlite database
        connection, cursor = self._connect_to_sqlite()

        # Extract the tier0 nodes from sqlite
        response.debug("Looking up corresponding tier0 nodes in sqlite")
        node_attributes_ordered = list(self.node_attributes)
        node_keys = set(node_key.replace("'", "''") for node_key, node in message.knowledge_graph.nodes.items()  # Escape quotes
                        if not only_decorate_bare or not (node.attributes and any(attribute for attribute in node.attributes
                                                             if attribute.attribute_type_id == "biolink:description")))
        response.debug(f"Identified {len(node_keys)} nodes to decorate (only_decorate_bare={only_decorate_bare})")
        node_keys_str = "','".join(node_keys)  # SQL wants ('node1', 'node2') format for string lists
        node_cols_str = ", ".join([f"N.{property_name}" for property_name in node_attributes_ordered])
        sql_query = f"SELECT N.id, {node_cols_str} " \
                    f"FROM nodes AS N " \
                    f"WHERE N.id IN ('{node_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decorate nodes in the KG with info in these tier0 nodes
        response.debug("Adding attributes to nodes in the KG")
        for row in rows:
            # First create the attributes for this tier0 node
            node_id = row[0]
            trapi_node = message.knowledge_graph.nodes[node_id]
            tier0_node_attributes = []
            for index, property_name in enumerate(node_attributes_ordered):
                value = self._load_property(property_name, row[index + 1])  # Add one to account for 'id' column
                if value:
                    tier0_node_attributes.append(self.create_attribute(property_name, value))

            # Then decorate the TRAPI node with those attributes it doesn't already have
            existing_attribute_triples = {self._get_attribute_triple(attribute)
                                          for attribute in trapi_node.attributes} if trapi_node.attributes else set()
            novel_attributes = [attribute for attribute in tier0_node_attributes
                                if self._get_attribute_triple(attribute) not in existing_attribute_triples]
            if trapi_node.attributes:
                trapi_node.attributes += novel_attributes
            else:
                trapi_node.attributes = novel_attributes

        return response

    def decorate_edges(self, response: ARAXResponse, kind: Optional[str] = "TIER0") -> ARAXResponse:
        """
        Decorates edges with supporting_text and any other available EPC info.
        kind: The kind of edges to decorate, either: "NGD", "TIER0", or "SEMMEDDB". For NGD edges, only
        supporting_text attributes are added. For TIER0 and SEMMEDDB, all available attributes are added.
        """
        kg = response.envelope.message.knowledge_graph
        response.debug("Decorating edges with EPC info from tier0")
        supported_kinds = {"TIER0", "NGD", "SEMMEDDB"}
        if kind not in supported_kinds:
            response.error(f"Supported values for ARAXDecorator.decorate_edges()'s 'kind' parameter are: "
                           f"{supported_kinds}")
            return response

        # Figure out which edges we need to decorate
        if kind == "TIER0":
            edge_keys_to_decorate = {edge_id for edge_id, edge in kg.edges.items()
                                     if edge.sources and any(retrieval_source.resource_id == self.tier0_infores_curie and
                                                             retrieval_source.resource_role == "aggregator_knowledge_source"
                                                             for retrieval_source in edge.sources)}
        elif kind == "SEMMEDDB":
            edge_keys_to_decorate = {edge_id for edge_id, edge in kg.edges.items()
                                     if edge.sources and any(retrieval_source.resource_id == "infores:semmeddb" and
                                                             retrieval_source.resource_role == "primary_knowledge_source"
                                                             for retrieval_source in edge.sources)}
        else:
            edge_keys_to_decorate = {edge_id for edge_id, edge in kg.edges.items()
                                     if edge.predicate == "biolink:occurs_together_in_literature_with"}
        if not edge_keys_to_decorate:
            response.debug(f"Could not identify any {kind} edges to decorate")
        else:
            response.debug(f"Identified {len(edge_keys_to_decorate)} edges to decorate")

        if kind == "NGD":
            # Decorating NGD edges is a little different, so we handle this in a separate function
            self._decorate_ngd_edges(edge_keys_to_decorate, kg, response)
        else:
            # NOTE: 'tier0_edge_id' refers to edge IDs in the tier0 graph; 'kg_edge_key' refers to the key of
            #        an edge in the TRAPI kg.edges; these are not necessarily the same
            # Map tier0 edge IDs to the edges they correspond to in the given KG
            tier0_edge_ids_to_kg_keys_map: DefaultDict = defaultdict(set)
            for edge_key in edge_keys_to_decorate:
                edge = kg.edges[edge_key]
                tier0_edge_id = get_arax_edge_key(edge)
                if tier0_edge_id in tier0_edge_ids_to_kg_keys_map:
                    response.error(f"Encountered more than one edge in the KG that corresponds to the same "
                                   f"tier0 edge ({tier0_edge_id}); duplicate edges are: {edge_key} and "
                                   f"{tier0_edge_ids_to_kg_keys_map[tier0_edge_id]}")
                tier0_edge_ids_to_kg_keys_map[tier0_edge_id] = edge_key

            # Extract the proper entries from sqlite
            edge_id_col = "triple"
            connection, cursor = self._connect_to_sqlite()
            response.debug("Looking up EPC edge info in tier0 sqlite")
            edge_attributes_ordered = list(self.edge_attributes)
            tier0_edge_ids_set = set(search_key.replace("'", "''") for search_key in set(tier0_edge_ids_to_kg_keys_map))  # Escape quotes
            tier0_edge_ids_str = "','".join(tier0_edge_ids_set)  # SQL wants ('edge1', 'edge2') format for string lists
            edge_cols_str = ", ".join([f"E.{property_name}" for property_name in edge_attributes_ordered])
            sql_query = f"SELECT E.{edge_id_col}, {edge_cols_str} " \
                        f"FROM edges AS E " \
                        f"WHERE E.{edge_id_col} IN ('{tier0_edge_ids_str}')"
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            cursor.close()
            connection.close()

            response.debug(f"Got {len(rows)} rows back from tier0 sqlite")

            response.debug("Adding attributes to edges in the KG")
            # Create helper maps for easy access to returned rows and attribute shells
            tier0_edge_id_to_tier0_edge_tuple_map = {row[0]: row for row in rows}
            attribute_type_id_map = {self.create_attribute(property_name, "irrelevant").attribute_type_id: property_name
                                     for property_name in set(self.edge_attributes)}
            # Loop through and add attributes to KG edges based on rows returned from tier0 sqlite
            for tier0_edge_id, tier0_edge_tuple in tier0_edge_id_to_tier0_edge_tuple_map.items():
                kg_edge_key = tier0_edge_ids_to_kg_keys_map[tier0_edge_id]
                kg_edge = kg.edges[kg_edge_key]
                new_attributes = []
                # Make sure we don't add a duplicate attribute (in case a decoration step happened previously)
                existing_attribute_type_ids = {attribute.attribute_type_id for attribute in kg_edge.attributes
                                               if attribute.attribute_type_id in attribute_type_id_map} if kg_edge.attributes else set()
                existing_attribute_short_names = {attribute_type_id_map[existing_attribute_type_id]
                                                  for existing_attribute_type_id in existing_attribute_type_ids}
                for index, property_name in enumerate(edge_attributes_ordered):
                    raw_value = tier0_edge_tuple[index + 1]
                    if raw_value and property_name not in existing_attribute_short_names:
                        value = self._load_property(property_name, raw_value)
                        # Figure out if we should cite a specific attribute source
                        if property_name in ("publications", "supporting_text"):
                            primary_ks = self._get_primary_knowledge_source(kg_edge)
                            attribute_source = primary_ks if primary_ks else self.tier0_infores_curie
                        else:
                            attribute_source = self.tier0_infores_curie
                        attribute = self.create_attribute(attribute_short_name=property_name,
                                                          value=value,
                                                          attribute_source=attribute_source,
                                                          log=response)
                        new_attributes.append(attribute)

                # Actually tack the new attributes onto the edge
                if new_attributes:
                    if not kg_edge.attributes:
                        kg_edge.attributes = new_attributes
                    else:
                        kg_edge.attributes += new_attributes

        return response

    def _decorate_ngd_edges(self, edge_keys_to_decorate, kg, response):
        # Determine the search keys for these edges that we need to look up in sqlite
        search_key_to_edge_keys_map = defaultdict(set)
        for edge_key in edge_keys_to_decorate:
            edge = kg.edges[edge_key]
            search_key = f"{edge.subject}--{edge.object}"
            search_key_to_edge_keys_map[search_key].add(edge_key)
        node_pair_key_col = "node_pair"

        # Extract the proper entries from sqlite. Tier0 doesn't have KG2c's `publications_info`
        # dict field; the nearest analog is `supporting_text`, which is what we pull here.
        connection, cursor = self._connect_to_sqlite()
        response.debug("Looking up EPC edge info in tier0 sqlite to decorate NGD edges")
        search_keys_set = set(search_key.replace("'", "''") for search_key in set(search_key_to_edge_keys_map))  # Escape quotes
        search_keys_str = "','".join(search_keys_set)  # SQL wants ('edge1', 'edge2') format for string lists
        sql_query = f"SELECT E.{node_pair_key_col}, E.supporting_text " \
                    f"FROM edges AS E " \
                    f"WHERE E.{node_pair_key_col} IN ('{search_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        response.debug(f"Got {len(rows)} rows back from tier0 sqlite")

        response.debug("Adding attributes to NGD edges in the KG")
        # Create a helper lookup map for easy access to returned rows
        search_key_to_tier0_edge_tuples_map = defaultdict(list)
        for row in rows:
            search_key = row[0]
            search_key_to_tier0_edge_tuples_map[search_key].append(row)

        attribute_type_id_map = {self.create_attribute(property_name, "irrelevant").attribute_type_id: property_name
                                 for property_name in set(self.edge_attributes)}
        for search_key, tier0_edge_tuples in search_key_to_tier0_edge_tuples_map.items():
            # Collect supporting_text values for all edges between the two nodes specified in the search key
            merged_supporting_text = []
            for tier0_edge_tuple in tier0_edge_tuples:
                raw_value = tier0_edge_tuple[1]
                if raw_value:  # Skip empty attributes
                    value = self._load_property("supporting_text", raw_value)
                    merged_supporting_text.append(value)

            # Add the attributes to each of the edges with the given search key (as needed)
            corresponding_kg_edge_keys = search_key_to_edge_keys_map[search_key]
            for edge_key in corresponding_kg_edge_keys:
                kg_edge = kg.edges[edge_key]
                # Make sure we don't add a duplicate attribute (in case a decoration step happened previously)
                existing_attribute_type_ids = {attribute.attribute_type_id for attribute in kg_edge.attributes
                                               if attribute.attribute_type_id in attribute_type_id_map} if kg_edge.attributes else set()
                existing_attribute_short_names = {attribute_type_id_map[existing_attribute_type_id]
                                                  for existing_attribute_type_id in existing_attribute_type_ids}
                if merged_supporting_text and "supporting_text" not in existing_attribute_short_names:
                    attribute = self.create_attribute(attribute_short_name="supporting_text",
                                                      value=merged_supporting_text,
                                                      attribute_source=self.tier0_infores_curie)
                    if not kg_edge.attributes:
                        kg_edge.attributes = [attribute]
                    else:
                        kg_edge.attributes.append(attribute)

    def create_attribute(self, attribute_short_name: str,
                         value: Any,
                         attribute_source: Optional[str] = None,
                         log: Optional[ARAXResponse] = None) -> Attribute:
        if log is None:
            log = ARAXResponse()
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

    @staticmethod
    def _get_primary_knowledge_source(edge: Edge) -> str:
        primary_ks_sources = [source.resource_id for source in edge.sources
                              if source.resource_role == "primary_knowledge_source"] if edge.sources else []
        return primary_ks_sources[0] if primary_ks_sources else ""

    def _connect_to_sqlite(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Tier0'])
        sqlite_name = rtxc.tier0_sqlite_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()
        return connection, cursor

    def _load_property(self, property_name: str, raw_value: str) -> Union[str, list[str], dict[str, Any], None]:
        attributes_info_lookup = self.node_attributes if property_name in self.node_attributes else self.edge_attributes
        ultimate_value_type = attributes_info_lookup[property_name]
        if ultimate_value_type is list:
            return [item for item in raw_value.split(self.array_delimiter_char) if item]
        elif ultimate_value_type is dict:
            if '"' not in raw_value:
                raw_value = raw_value.replace("'", '"')
            try:
                return ujson.loads(raw_value)
            except Exception:
                return {}
        else:
            return raw_value

    @staticmethod
    def _get_attribute_triple(attribute: Attribute) -> str:
        return f"{attribute.attribute_type_id}--{attribute.value}--{attribute.attribute_source}"



