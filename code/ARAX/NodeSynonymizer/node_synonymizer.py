import argparse
import ast
import json
import os
import pathlib
import sqlite3
import string
import sys
from collections import defaultdict
from typing import Optional, Union, List, Set, Dict, Tuple

import pandas as pd

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))
from ARAX_database_manager import ARAXDatabaseManager

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.retrieval_source import RetrievalSource


class NodeSynonymizer:

    def __init__(self):
        self.rtx_config = RTXConfiguration()
        self.database_name = self.rtx_config.node_synonymizer_path.split("/")[-1]
        synonymizer_dir = os.path.dirname(os.path.abspath(__file__))
        self.database_path = f"{synonymizer_dir}/{self.database_name}"
        self.placeholder_lookup_values_str = "**LOOKUP_VALUES_GO_HERE**"
        self.unnecessary_chars_map = {ord(char): None for char in string.punctuation + string.whitespace}
        self.kg2_infores_curie = "infores:rtx-kg2"
        self.sri_nn_infores_curie = "infores:sri-node-normalizer"
        self.arax_infores_curie = "infores:arax"

        # If the database doesn't seem to exist, try running the DatabaseManager
        if not pathlib.Path(self.database_path).exists():
            print(f"Synonymizer not present at {self.database_path}; attempting to download with database manager..")
            db_manager = ARAXDatabaseManager()
            db_manager.update_databases()

        if not pathlib.Path(self.database_path).exists():
            raise ValueError(f"Synonymizer specified in config_dbs file does not exist locally, even after "
                             f"running the database manager! It should be at: {self.database_path}")
        else:
            self.db_connection = sqlite3.connect(self.database_path)

    def __del__(self):
        if hasattr(self, "db_connection"):
            self.db_connection.close()

    # --------------------------------------- EXTERNAL MAIN METHODS ----------------------------------------------- #

    def get_canonical_curies(self, curies: Optional[Union[str, Set[str], List[str]]] = None,
                             names: Optional[Union[str, Set[str], List[str]]] = None,
                             return_all_categories: bool = False) -> dict:

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict = dict()

        if curies_set:
            # First transform curies so that their prefixes are entirely uppercase
            curies_to_capitalized_curies, capitalized_curies = self._map_to_capitalized_curies(curies_set)

            # Query the synonymizer sqlite database for these identifiers
            sql_query_template = f"""
                        SELECT N.id_simplified, N.cluster_id, C.name, C.category
                        FROM nodes as N
                        INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                        WHERE N.id_simplified in ('{self.placeholder_lookup_values_str}')"""
            matching_rows = self._run_sql_query_in_batches(sql_query_template, capitalized_curies)

            # Transform the results into the proper response format
            results_dict_capitalized = {row[0]: self._create_preferred_node_dict(preferred_id=row[1],
                                                                                 preferred_category=row[3],
                                                                                 preferred_name=row[2])
                                        for row in matching_rows}
            results_dict = {input_curie: results_dict_capitalized[capitalized_curie]
                            for input_curie, capitalized_curie in curies_to_capitalized_curies.items()
                            if capitalized_curie in results_dict_capitalized}

        if names_set:
            # First transform to simplified names (lowercase, no punctuation/whitespace)
            names_to_simplified_names, simplified_names = self._map_to_simplified_names(names_set)

            # Query the synonymizer sqlite database for these names
            sql_query_template = f"""
                        SELECT N.id, N.name_simplified, N.cluster_id, C.name, C.category
                        FROM nodes as N
                        INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                        WHERE N.name_simplified in ('{self.placeholder_lookup_values_str}')"""
            matching_rows = self._run_sql_query_in_batches(sql_query_template, simplified_names)

            # For each simplified name, pick the cluster that nodes with that simplified name most often belong to
            names_to_best_cluster_id = self._count_clusters_per_name(matching_rows, name_index=1, cluster_id_index=2)

            # Create some helper maps
            cluster_ids_to_node_id = {row[2]: row[0] for row in matching_rows}  # Doesn't matter that this gives ONE node per cluster
            node_ids_to_rows = {row[0]: row for row in matching_rows}
            names_to_cluster_rows = {name: node_ids_to_rows[cluster_ids_to_node_id[cluster_id]]
                                     for name, cluster_id in names_to_best_cluster_id.items()}

            # Transform the results into the proper response format
            results_dict_names_simplified = {name: self._create_preferred_node_dict(preferred_id=cluster_id,
                                                                                    preferred_category=names_to_cluster_rows[name][4],
                                                                                    preferred_name=names_to_cluster_rows[name][3])
                                             for name, cluster_id in names_to_best_cluster_id.items()}
            results_dict_names = {input_name: results_dict_names_simplified[simplified_name]
                                  for input_name, simplified_name in names_to_simplified_names.items()
                                  if simplified_name in results_dict_names_simplified}

            # Merge these results with any results for input curies
            results_dict.update(results_dict_names)

        # Tack on all categories, if asked for (infrequent enough that it's ok to have an extra query for this)
        if return_all_categories:
            cluster_ids = {canonical_info["preferred_curie"]
                           for canonical_info in results_dict.values()}
            sql_query_template = f"""
                        SELECT N.cluster_id, N.category
                        FROM nodes as N
                        WHERE N.cluster_id in ('{self.placeholder_lookup_values_str}')"""
            matching_rows = self._run_sql_query_in_batches(sql_query_template, cluster_ids)

            # Count up how many members this cluster has with different categories
            clusters_by_category_counts = defaultdict(lambda: defaultdict(int))
            for cluster_id, member_category in matching_rows:
                member_category = self._add_biolink_prefix(member_category)
                clusters_by_category_counts[cluster_id][member_category] += 1

            # Add the counts to our response
            for canonical_info in results_dict.values():
                cluster_id = canonical_info["preferred_curie"]
                category_counts = clusters_by_category_counts[cluster_id]
                canonical_info["all_categories"] = dict(category_counts)

        # Add None values for any unrecognized input values
        unrecognized_input_values = (curies_set.union(names_set)).difference(results_dict)
        for unrecognized_value in unrecognized_input_values:
            results_dict[unrecognized_value] = None

        return results_dict

    def get_equivalent_nodes(self, curies: Optional[Union[str, Set[str], List[str]]] = None,
                             names: Optional[Union[str, Set[str], List[str]]] = None,
                             include_unrecognized_entities: bool = True) -> dict:

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict = dict()

        if curies_set:
            # First transform curies so that their prefixes are entirely uppercase
            curies_to_capitalized_curies, capitalized_curies = self._map_to_capitalized_curies(curies_set)

            # Query the synonymizer sqlite database for these identifiers (in batches, if necessary)
            sql_query_template = f"""
                        SELECT N.id_simplified, C.member_ids
                        FROM nodes as N
                        INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                        WHERE N.id_simplified in ('{self.placeholder_lookup_values_str}')"""
            matching_rows = self._run_sql_query_in_batches(sql_query_template, capitalized_curies)

            # Transform the results into the proper response format
            results_dict_capitalized = {row[0]: ast.literal_eval(row[1]) for row in matching_rows}
            results_dict = {input_curie: results_dict_capitalized[capitalized_curie]
                            for input_curie, capitalized_curie in curies_to_capitalized_curies.items()
                            if capitalized_curie in results_dict_capitalized}

        if names_set:
            # First transform to simplified names (lowercase, no punctuation/whitespace)
            names_to_simplified_names, simplified_names = self._map_to_simplified_names(names_set)

            # Query the synonymizer sqlite database for these names
            sql_query_template = f"""
                        SELECT N.id, N.name_simplified, C.cluster_id, C.member_ids
                        FROM nodes as N
                        INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                        WHERE N.name_simplified in ('{self.placeholder_lookup_values_str}')"""
            matching_rows = self._run_sql_query_in_batches(sql_query_template, simplified_names)

            # For each simplified name, pick the cluster that nodes with that simplified name most often belong to
            names_to_best_cluster_id = self._count_clusters_per_name(matching_rows, name_index=1, cluster_id_index=2)

            # Create some helper maps
            cluster_ids_to_node_id = {row[2]: row[0] for row in matching_rows}  # Doesn't matter that this gives ONE node per cluster
            node_ids_to_rows = {row[0]: row for row in matching_rows}
            names_to_cluster_rows = {name: node_ids_to_rows[cluster_ids_to_node_id[cluster_id]]
                                     for name, cluster_id in names_to_best_cluster_id.items()}

            # Transform the results into the proper response format
            results_dict_names_simplified = {name: ast.literal_eval(cluster_row[3])
                                             for name, cluster_row in names_to_cluster_rows.items()}
            results_dict_names = {input_name: results_dict_names_simplified[simplified_name]
                                  for input_name, simplified_name in names_to_simplified_names.items()
                                  if simplified_name in results_dict_names_simplified}

            # Merge these results with any results for input curies
            results_dict.update(results_dict_names)

        if include_unrecognized_entities:
            # Add None values for any unrecognized input curies
            unrecognized_curies = (curies_set.union(names_set)).difference(results_dict)
            for unrecognized_curie in unrecognized_curies:
                results_dict[unrecognized_curie] = None

        return results_dict

    def get_normalizer_results(self, entities: Optional[Union[str, Set[str], List[str]]]) -> dict:

        # First handle any special input from /entity endpoint
        output_format = None
        if isinstance(entities, dict):
            entities_dict = entities
            entities = entities_dict.get("terms")
            output_format = entities_dict.get("format")

        # Convert any input curies to Set format
        entities_set = self._convert_to_set_format(entities)

        # First try looking up input entities as curies
        equivalent_curies_dict = self.get_equivalent_nodes(curies=entities_set, include_unrecognized_entities=False)
        unrecognized_entities = entities_set.difference(equivalent_curies_dict)
        # If we weren't successful at looking up some entities as curies, try looking them up as names
        if unrecognized_entities:
            equivalent_curies_dict_names = self.get_equivalent_nodes(names=unrecognized_entities, include_unrecognized_entities=False)
            equivalent_curies_dict.update(equivalent_curies_dict_names)

        # Then get info for all of those equivalent nodes
        # Note: We don't need to query by capitalized curies because these are all curies that exist in the synonymizer
        all_node_ids = set().union(*equivalent_curies_dict.values())
        sql_query_template = f"""
                    SELECT N.id, N.cluster_id, N.name, N.category, N.major_branch, N.name_sri, N.category_sri, N.name_kg2pre, N.category_kg2pre, C.name
                    FROM nodes as N
                    INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                    WHERE N.id in ('{self.placeholder_lookup_values_str}')"""
        matching_rows = self._run_sql_query_in_batches(sql_query_template, all_node_ids)
        nodes_dict = {row[0]: {"identifier": row[0],
                               "category": self._add_biolink_prefix(row[3]),
                               "label": row[2],
                               "major_branch": row[4],
                               "in_sri": row[6] is not None,
                               "name_sri": row[5],
                               "category_sri": self._add_biolink_prefix(row[6]),
                               "in_kg2pre": row[8] is not None,
                               "name_kg2pre": row[7],
                               "category_kg2pre": self._add_biolink_prefix(row[8]),
                               "cluster_id": row[1],
                               "cluster_preferred_name": row[9]} for row in matching_rows}

        # Transform the results into the proper response format
        results_dict = dict()
        for input_entity, equivalent_curies in equivalent_curies_dict.items():
            cluster_id = nodes_dict[next(iter(equivalent_curies))]["cluster_id"]  # All should have the same cluster ID
            cluster_rep = nodes_dict[cluster_id]
            results_dict[input_entity] = {"id": {"identifier": cluster_id,
                                                 "name": cluster_rep["cluster_preferred_name"],
                                                 "category": cluster_rep["category"],
                                                 "SRI_normalizer_name": cluster_rep["name_sri"],
                                                 "SRI_normalizer_category": cluster_rep["category_sri"],
                                                 "SRI_normalizer_curie": cluster_id if cluster_rep["category_sri"] else None},
                                          "categories": defaultdict(int),
                                          "nodes": [nodes_dict[equivalent_curie] for equivalent_curie in equivalent_curies]}

        # Do some post-processing (tally up category counts and remove no-longer-needed 'cluster_id' property)
        for normalizer_info in results_dict.values():
            for equivalent_node in normalizer_info["nodes"]:
                normalizer_info["categories"][equivalent_node["category"]] += 1
                if "cluster_id" in equivalent_node:
                    del equivalent_node["cluster_id"]
                if "cluster_preferred_name" in equivalent_node:
                    del equivalent_node["cluster_preferred_name"]
            # Sort nodes by their curies
            normalizer_info["nodes"].sort(key=lambda node: node["identifier"].upper())

        # Add None values for any unrecognized input curies
        unrecognized_curies = entities_set.difference(results_dict)
        for unrecognized_curie in unrecognized_curies:
            results_dict[unrecognized_curie] = None

        # Trim down to minimal output, if requested
        if output_format == "minimal":
            for normalizer_info in results_dict.values():
                keys_to_delete = set(normalizer_info.keys()).difference({"id"})
                for dict_key in keys_to_delete:
                    del normalizer_info[dict_key]
        # Otherwise add in cluster graphs
        else:
            for normalizer_info in results_dict.values():
                if normalizer_info:
                    normalizer_info["knowledge_graph"] = self._get_cluster_graph(normalizer_info)

        return results_dict

    # ---------------------------------------- EXTERNAL DEBUG METHODS --------------------------------------------- #

    def print_cluster_table(self, curie_or_name: str):
        # First figure out what cluster this concept belongs to
        canonical_info = self.get_canonical_curies(curies=curie_or_name)
        if not canonical_info[curie_or_name]:
            canonical_info = self.get_canonical_curies(names=curie_or_name)

        # Grab the cluster nodes/edges if we found a corresponding cluster
        if canonical_info[curie_or_name]:
            cluster_id = canonical_info[curie_or_name]["preferred_curie"]

            sql_query = f"SELECT member_ids, intra_cluster_edge_ids FROM clusters WHERE cluster_id = '{cluster_id}'"
            results = self._execute_sql_query(sql_query)
            if results:
                cluster_row = results[0]
                member_ids = ast.literal_eval(cluster_row[0])  # Lists are stored as strings in sqlite
                intra_cluster_edge_ids_str = "[]" if cluster_row[1] == "nan" else cluster_row[1]
                intra_cluster_edge_ids = ast.literal_eval(
                    intra_cluster_edge_ids_str)  # Lists are stored as strings in sqlite

                nodes_query = f"SELECT * FROM nodes WHERE id IN ('{self._convert_to_str_format(member_ids)}')"
                node_rows = self._execute_sql_query(nodes_query)
                nodes_df = self._load_records_into_dataframe(node_rows, "nodes")

                # TODO: Improve formatting! (indicate if in SRI vs. KG2pre, etc...)
                nodes_df = nodes_df[["id", "category", "name"]]
                edges_query = f"SELECT * FROM edges WHERE id IN ('{self._convert_to_str_format(intra_cluster_edge_ids)}')"
                edge_rows = self._execute_sql_query(edges_query)
                edges_df = self._load_records_into_dataframe(edge_rows, "edges")
                edges_df = edges_df[["subject", "predicate", "object", "upstream_resource_id", "primary_knowledge_source"]]

                print(f"\nCluster for {curie_or_name} has {edges_df.shape[0]} edges:\n")
                print(f"{edges_df.to_markdown(index=False)}\n")
                print(f"\nCluster for {curie_or_name} has {nodes_df.shape[0]} nodes:\n")
                print(f"{nodes_df.to_markdown(index=False)}\n")
            else:
                print(f"No cluster exists with a cluster_id of {cluster_id}")
                return dict()
        else:
            print(f"Sorry, input concept {curie_or_name} is not recognized.")

    # ---------------------------------------- INTERNAL HELPER METHODS -------------------------------------------- #

    @staticmethod
    def _convert_to_str_format(list_or_set: Union[Set[str], List[str]]) -> str:
        preprocessed_list = [item.replace("'", "''") for item in list_or_set if item]  # Need to escape ' characters for SQL
        list_str = "','".join(preprocessed_list)  # SQL wants ('id1', 'id2') format for string lists
        return list_str

    @staticmethod
    def _convert_to_set_format(some_value: any) -> set:
        if isinstance(some_value, set):
            return some_value
        elif isinstance(some_value, list):
            return set(some_value)
        elif isinstance(some_value, str):
            return {some_value}
        elif isinstance(some_value, pd.Series):
            return set(some_value.values)
        elif some_value is None:
            return set()
        else:
            raise ValueError(f"Input is not an allowable data type (list, set, or string)!")

    @staticmethod
    def _add_biolink_prefix(category: Optional[str]) -> Optional[str]:
        if category:
            return f"biolink:{category}"
        else:
            return category

    @staticmethod
    def _count_clusters_per_name(rows: list, name_index: int, cluster_id_index: int) -> dict:
        names_to_cluster_counts = defaultdict(lambda: defaultdict(int))
        for row in rows:
            name = row[name_index]
            cluster_id = row[cluster_id_index]
            names_to_cluster_counts[name][cluster_id] += 1
        names_to_best_cluster_id = {name: max(cluster_counts, key=cluster_counts.get)
                                    for name, cluster_counts in names_to_cluster_counts.items()}
        return names_to_best_cluster_id

    @staticmethod
    def _divide_into_chunks(some_set: Set[str], chunk_size: int) -> List[List[str]]:
        some_list = list(some_set)
        return [some_list[start:start + chunk_size] for start in range(0, len(some_list), chunk_size)]

    @staticmethod
    def _capitalize_curie_prefix(curie: str) -> str:
        curie_chunks = curie.split(":")
        curie_chunks[0] = curie_chunks[0].upper()
        return ":".join(curie_chunks)

    def _get_cluster_graph(self, normalizer_info: dict) -> dict:
        kg = KnowledgeGraph()
        cluster_id = normalizer_info["id"]["identifier"]

        # Add TRAPI nodes for each cluster member
        trapi_nodes = {node["identifier"]: self._convert_to_trapi_node(node)
                       for node in normalizer_info["nodes"]}
        # Indicate which one is the cluster representative (i.e., 'preferred' identifier
        trapi_nodes[cluster_id].attributes.append(Attribute(attribute_type_id="biolink:description",
                                                            value_type_id="metatype:String",
                                                            value="This node is the preferred/canonical identifier "
                                                                  "for this concept cluster.",
                                                            attribute_source="infores:arax"))
        kg.nodes = trapi_nodes

        # Add TRAPI edges for any intra-cluster edges
        sql_query = f"SELECT intra_cluster_edge_ids FROM clusters WHERE cluster_id = '{cluster_id}'"
        results = self._execute_sql_query(sql_query)
        if results:
            cluster_row = results[0]
            intra_cluster_edge_ids_str = "[]" if cluster_row[0] == "nan" else cluster_row[0]
            intra_cluster_edge_ids = ast.literal_eval(intra_cluster_edge_ids_str)  # Lists are stored as strings in sqlite

            edges_query = f"SELECT * FROM edges WHERE id IN ('{self._convert_to_str_format(intra_cluster_edge_ids)}')"
            edge_rows = self._execute_sql_query(edges_query)
            edges_df = self._load_records_into_dataframe(edge_rows, "edges")
            edge_dicts = edges_df.to_dict(orient="records")
            trapi_edges = {edge["id"]: self._convert_to_trapi_edge(edge)
                           for edge in edge_dicts}
            kg.edges = trapi_edges

        return kg.to_dict()

    def _convert_to_trapi_edge(self, edge_dict: dict) -> Edge:
        # Fix the predicate used for name similarity edges created during the synonymizer build..
        predicate = "similar_to" if edge_dict["predicate"] == "has_similar_name" else edge_dict["predicate"]

        edge = Edge(subject=edge_dict["subject"],
                    object=edge_dict["object"],
                    predicate=self._add_biolink_prefix(predicate))

        # Tack on provenance information
        primary_ks = edge_dict["primary_knowledge_source"]
        ingested_ks = edge_dict["upstream_resource_id"]
        if ingested_ks == "infores:arax-node-synonymizer":
            ingested_ks = self.arax_infores_curie  # For now there isn't a curie specifically for the NodeSynonymizer
        sources = []
        if primary_ks:
            sources.append(RetrievalSource(resource_id=primary_ks,
                                           resource_role="primary_knowledge_source"))
            sources.append(RetrievalSource(resource_id=ingested_ks,
                                           resource_role="aggregator_knowledge_source",
                                           upstream_resource_ids=[primary_ks]))
        else:
            sources.append(RetrievalSource(resource_id=ingested_ks,
                                           resource_role="primary_knowledge_source"))
        if ingested_ks != self.arax_infores_curie:
            # List ARAX as an aggregator knowledge source, unless this is an ARAX-created edge...
            sources.append(RetrievalSource(resource_id=self.arax_infores_curie,
                                           resource_role="aggregator_knowledge_source",
                                           upstream_resource_ids=[ingested_ks]))
        edge.sources = sources

        # Tack on the edge weight used during the synonymizer build
        edge.attributes = [Attribute(attribute_type_id="EDAM-DATA:1772",
                                     value=edge_dict["weight"],
                                     value_type_id="metatype:Float",
                                     attribute_source=self.arax_infores_curie,
                                     description="The edge weight used for the clustering algorithm run as "
                                                 "part of the ARAX NodeSynonymizer's build process")]

        # Add a description for name-similarity edges
        if edge.predicate == "biolink:similar_to":
            edge.attributes.append(Attribute(attribute_type_id="biolink:description",
                                             value_type_id="metatype:String",
                                             attribute_source=self.arax_infores_curie,
                                             value="This edge was created during the ARAX NodeSynonymizer build "
                                                   "to represent the similarity between the names of the two involved "
                                                   "nodes."))

        return edge

    def _convert_to_trapi_node(self, normalizer_node: dict) -> Node:
        node = Node(name=normalizer_node["label"],
                    categories=[normalizer_node["category"]],
                    attributes=[])

        # Indicate which sources provided this node
        provided_bys = []
        if normalizer_node["in_sri"]:
            provided_bys.append(self.sri_nn_infores_curie)
        if normalizer_node["in_kg2pre"]:
            provided_bys.append(self.kg2_infores_curie)
        node.attributes.append(Attribute(attribute_type_id="biolink:provided_by",
                                         value=provided_bys,
                                         value_type_id="biolink:Uriorcurie",
                                         attribute_source=self.arax_infores_curie,
                                         description="The sources the ARAX NodeSynonymizer extracted this node from"))

        # Tack on the SRI NN's name and category for this node
        if normalizer_node["in_sri"]:
            node.attributes.append(Attribute(attribute_type_id="biolink:name",
                                             value=normalizer_node["name_sri"],
                                             value_type_id="metatype:String",
                                             attribute_source=self.sri_nn_infores_curie,
                                             description="Name for this identifier in the SRI NodeNormalizer bulk download"))
            node.attributes.append(Attribute(attribute_type_id="biolink:category",
                                             value=normalizer_node["category_sri"],
                                             value_type_id="metatype:Uriorcurie",
                                             attribute_source=self.sri_nn_infores_curie,
                                             description="Category for this identifier in the SRI NodeNormalizer bulk download"))

        # Tack on KG2pre's name and category for this node
        if normalizer_node["in_kg2pre"]:
            node.attributes.append(Attribute(attribute_type_id="biolink:name",
                                             value=normalizer_node["name_kg2pre"],
                                             value_type_id="metatype:String",
                                             attribute_source=self.kg2_infores_curie,
                                             description="Name for this identifier in RTX-KG2pre"))
            node.attributes.append(Attribute(attribute_type_id="biolink:category",
                                             value=normalizer_node["category_kg2pre"],
                                             value_type_id="metatype:Uriorcurie",
                                             attribute_source=self.kg2_infores_curie,
                                             description="Category for this identifier in RTX-KG2pre"))

        return node

    def _create_preferred_node_dict(self, preferred_id: str, preferred_category: str, preferred_name: Optional[str]) -> dict:
        return {
            "preferred_curie": preferred_id,
            "preferred_name": preferred_name,
            "preferred_category": self._add_biolink_prefix(preferred_category)
        }

    def _run_sql_query_in_batches(self, sql_query_template: str, lookup_values: Set[str]) -> list:
        """
        Sqlite has a max length allowed for SQL statements, so we divide really long curie/name lists into batches.
        """
        lookup_values_batches = self._divide_into_chunks(lookup_values, 5000)
        all_matching_rows = []
        for lookup_values_batch in lookup_values_batches:
            sql_query = sql_query_template.replace(self.placeholder_lookup_values_str,
                                                   self._convert_to_str_format(lookup_values_batch))
            matching_rows = self._execute_sql_query(sql_query)
            all_matching_rows += matching_rows
        return all_matching_rows

    def _execute_sql_query(self, sql_query: str) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(sql_query)
        matching_rows = cursor.fetchall()
        cursor.close()
        return matching_rows

    def _map_to_capitalized_curies(self, curies_set: Set[str]) -> Tuple[Dict[str, str], Set[str]]:
        curies_to_capitalized_curies = {curie: self._capitalize_curie_prefix(curie) for curie in curies_set}
        capitalized_curies = set(curies_to_capitalized_curies.values())
        return curies_to_capitalized_curies, capitalized_curies

    def _map_to_simplified_names(self, names_set: Set[str]) -> Tuple[Dict[str, str], Set[str]]:
        names_to_simplified_names = {name: name.lower().translate(self.unnecessary_chars_map)
                                     for name in names_set if name}  # Skip None names
        simplified_names = set(names_to_simplified_names.values())
        return names_to_simplified_names, simplified_names

    def _load_records_into_dataframe(self, records: list, table_name: str) -> pd.DataFrame:
        column_info = self._execute_sql_query(f"PRAGMA table_info({table_name})")
        column_names = [column_info[1] for column_info in column_info]
        records_df = pd.DataFrame(records, columns=column_names)
        return records_df


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("curie_or_name")
    # Add flags corresponding to each of the three main synonymizer methods
    arg_parser.add_argument("-c", "--canonical", dest="canonical", action="store_true")
    arg_parser.add_argument("-e", "--equivalent", dest="equivalent", action="store_true")
    arg_parser.add_argument("-n", "--normalizer", dest="normalizer", action="store_true")
    # Add a couple other data viewing options (tabular and TRAPI cluster graph format)
    arg_parser.add_argument("-t", "--table", dest="table", action="store_true")
    arg_parser.add_argument("-g", "--graph", dest="graph", action="store_true")
    args = arg_parser.parse_args()

    synonymizer = NodeSynonymizer()
    if args.canonical:
        results = synonymizer.get_canonical_curies(curies=args.curie_or_name)
        if not results[args.curie_or_name]:
            results = synonymizer.get_canonical_curies(names=args.curie_or_name)
        print(json.dumps(results, indent=2))
    if args.equivalent:
        results = synonymizer.get_equivalent_nodes(curies=args.curie_or_name)
        if not results[args.curie_or_name]:
            results = synonymizer.get_equivalent_nodes(names=args.curie_or_name)
        print(json.dumps(results, indent=2))
    if args.normalizer:
        results = synonymizer.get_normalizer_results(entities=args.curie_or_name)
        print(json.dumps(results, indent=2))
    # Default to printing the tabular view of the cluster if nothing else was specified
    if args.table or (not args.canonical and not args.equivalent and not args.normalizer and not args.graph):
        synonymizer.print_cluster_table(args.curie_or_name)


if __name__ == "__main__":
    main()
