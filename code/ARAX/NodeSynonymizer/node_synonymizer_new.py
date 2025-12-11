import argparse
import json
import os
import string
import sys
import time
import math
from collections import defaultdict, Counter
from typing import Optional, Union, List, Set, Dict, Tuple

import bmt
import pprint
import requests
import collections

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.node import Node
from openapi_server.models.edge import Edge
from openapi_server.models.attribute import Attribute
from openapi_server.models.retrieval_source import RetrievalSource


class NodeSynonymizer:

    def __init__(self, sqlite_file_name: Optional[str] = None):
        # sqlite_file_name parameter kept for backward compatibility but no longer used
        self.rtx_config = RTXConfiguration()
        self.api_base_url = "https://nodenorm.ci.transltr.io/1.5"
        self.unnecessary_chars_map = {ord(char): None for char in string.punctuation + string.whitespace}
        self.kg2_infores_curie = "infores:rtx-kg2"
        self.sri_nn_infores_curie = "infores:sri-node-normalizer"
        self.arax_infores_curie = "infores:arax"
        self.bmt_tk = bmt.Toolkit()
        self.category_levels = self._get_categories_and_levels()

    # --------------------------------------- EXTERNAL MAIN METHODS ----------------------------------------------- #

    def get_canonical_curies(self,
                             curies: Optional[Union[str, Set[str], List[str]]] = None,
                             names: Optional[Union[str, Set[str], List[str]]] = None,
                             return_all_categories: bool = False,
                             debug: bool = False) -> dict:
        start = time.time()

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict = dict()

        if curies_set:
            # Query the Node Normalizer API for these curies
            api_results = self._call_normalizer_api(list(curies_set))

            # Transform the results into the proper response format
            for input_curie in curies_set:
                if input_curie in api_results and api_results[input_curie] is not None:
                    result = api_results[input_curie]
                    preferred_id = result.get("id", {}).get("identifier")
                    preferred_category = result.get("id", {}).get("type", [None])[0] if result.get("id", {}).get("type") else None
                    preferred_name = result.get("id", {}).get("label")
                    if preferred_category:
                        preferred_category = preferred_category.replace("biolink:", "")
                    results_dict[input_curie] = self._create_preferred_node_dict(
                        preferred_id=preferred_id,
                        preferred_category=preferred_category,
                        preferred_name=preferred_name
                    )

        if names_set:
            # For names, we need to search through equivalent identifiers
            # First, try to find curies that match the names by looking up all known curies
            # This is a limitation - the API doesn't have a direct name search endpoint
            # We'll try to find matches by searching through equivalent identifiers of a sample set
            # For now, we'll return None for name-based lookups as the API doesn't support direct name search
            # In practice, users should provide curies instead of names
            pass

        # Tack on all categories, if asked for
        if return_all_categories:
            cluster_ids = {canonical_info["preferred_curie"]
                           for canonical_info in results_dict.values() if canonical_info}
            if cluster_ids:
                # Get all equivalent nodes for these cluster IDs to count categories
                api_results = self._call_normalizer_api(list(cluster_ids))

                # Count up how many members this cluster has with different categories
                clusters_by_category_counts = defaultdict(lambda: defaultdict(int))
                for cluster_id, result in api_results.items():
                    if result is not None:
                        # Get all equivalent identifiers and their categories
                        equivalent_ids = result.get("equivalent_identifiers", [])
                        for equiv_id in equivalent_ids:
                            equiv_types = equiv_id.get("type", [])
                            for equiv_type in equiv_types:
                                equiv_type = self._add_biolink_prefix(equiv_type.replace("biolink:", ""))
                                clusters_by_category_counts[cluster_id][equiv_type] += 1
                        # Also count the main ID's type
                        main_types = result.get("id", {}).get("type", [])
                        for main_type in main_types:
                            main_type = self._add_biolink_prefix(main_type.replace("biolink:", ""))
                            clusters_by_category_counts[cluster_id][main_type] += 1

                # Add the counts to our response
                for canonical_info in results_dict.values():
                    if canonical_info:
                        cluster_id = canonical_info["preferred_curie"]
                        category_counts = clusters_by_category_counts.get(cluster_id, {})
                        canonical_info["all_categories"] = dict(category_counts)

        # Add None values for any unrecognized input values
        unrecognized_input_values = (curies_set.union(names_set)).difference(results_dict)
        for unrecognized_value in unrecognized_input_values:
            results_dict[unrecognized_value] = None

        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_equivalent_nodes(self, curies: Optional[Union[str, Set[str], List[str]]] = None,
                             names: Optional[Union[str, Set[str], List[str]]] = None,
                             include_unrecognized_entities: bool = True,
                             debug: bool = False) -> dict:
        start = time.time()

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict = dict()

        if curies_set:
            # Query the Node Normalizer API for these curies
            api_results = self._call_normalizer_api(list(curies_set))

            # Transform the results into the proper response format
            for input_curie in curies_set:
                if input_curie in api_results and api_results[input_curie] is not None:
                    result = api_results[input_curie]
                    # Get all equivalent identifiers
                    equivalent_ids = [equiv.get("identifier") for equiv in result.get("equivalent_identifiers", [])]
                    # Also include the main ID
                    main_id = result.get("id", {}).get("identifier")
                    if main_id:
                        equivalent_ids.append(main_id)
                    results_dict[input_curie] = list(set(equivalent_ids))  # Remove duplicates

        if names_set:
            # The API doesn't support direct name search, so we return None for name-based lookups
            # In practice, users should provide curies instead of names
            pass

        if include_unrecognized_entities:
            # Add None values for any unrecognized input curies
            unrecognized_curies = (curies_set.union(names_set)).difference(results_dict)
            for unrecognized_curie in unrecognized_curies:
                results_dict[unrecognized_curie] = None

        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_preferred_names(self,
                            curies: Union[str, Set[str], List[str]],
                            debug: bool = False) -> dict:
        """
        Returns preferred names for input curies - i.e., the name of the curie's canonical identifier.
        """
        start = time.time()

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        results_dict = dict()

        if curies_set:
            curies_list = list(curies_set)
            api_results = self._call_normalizer_api(curies_list)
            results_dict = {k: v['id']['label'] for k, v in api_results.items() if v is not None and v.get('id', {}).get('label')}
 
        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_curie_names(self,
                        curies: Union[str, Set[str], List[str]],
                        debug: bool = False) -> dict:
        """
        Returns NON-preferred names for input curies; i.e., the curie's direct name, not the name of its canonical
        identifier.
        """
        start = time.time()

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        results_dict = dict()

        if curies_set:
            curies_list = list(curies_set)
            api_results = self._call_normalizer_api(curies_list)
            results_dict = {k: i['label'] for k, v in api_results.items() 
                           if v is not None 
                           for i in v.get('equivalent_identifiers', []) 
                           if i.get('identifier') == k and i.get('label')}

        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_curie_category(self,
                           curies: Union[str, Set[str], List[str]],
                           debug: bool = False) -> dict:
        """
        Returns NON-preferred names for input curies; i.e., the curie's direct name, not the name of its canonical
        identifier.
        """
        start = time.time()

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        results_dict = dict()

        if curies_set:
            curies_list = list(curies_set)
            api_results = self._call_normalizer_api(curies_list)
            results_dict = {k: {t: self.category_levels.get(t.replace("biolink:", ""), None) 
                               for t in v.get('type', [])} 
                           for k, v in api_results.items() if v is not None}
            results_dict = {k: {t: l for t, l in v.items() if l is not None} for k, v in results_dict.items()}
            best_by_parent = {
                parent_key: max(subdict.items(), key=lambda kv: kv[1])[0]
                for parent_key, subdict in results_dict.items() if subdict
            }
        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return best_by_parent

    def _get_categories_and_levels(self, debug: bool = False) -> dict[str, int]:
        start = time.time()
        q = collections.deque(['biolink:NamedThing'])
        levels = {'biolink:NamedThing': 0}
        while q:
            i = q.popleft()
            for neighbor in self.bmt_tk.get_children(i, formatted=True):
                if neighbor not in levels:
                    levels[neighbor] = levels[i] + 1
                    q.append(neighbor)
        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return {k.replace("biolink:", ""):v for k, v in levels.items()}

    def get_distinct_category_list(self, debug: bool = False) -> list:
        start = time.time()
        curies = list(self.category_levels.keys())
        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return curies

    def get_normalizer_results(self, entities: Optional[Union[str, Set[str], List[str]]],
                               max_synonyms: int = 1000000,
                               debug: bool = False) -> dict:
        start = time.time()

        # First handle any special input from /entity endpoint
        output_format = None
        if isinstance(entities, dict):
            entities_dict = entities
            entities = entities_dict.get("terms")
            output_format = entities_dict.get("format")

            # Allow the caller to encode the max_synonyms in the input dict (used by web UI)
            max_synonyms_raw = entities_dict.get("max_synonyms")
            try:
                max_synonyms_int = int(max_synonyms_raw)
                if max_synonyms_int > 0:
                    max_synonyms = max_synonyms_int
            except:
                pass

        # Convert any input curies to Set format
        entities_set = self._convert_to_set_format(entities)

        # First try looking up input entities as curies
        equivalent_curies_dict = self.get_equivalent_nodes(curies=entities_set, include_unrecognized_entities=False)
        unrecognized_entities = entities_set.difference(equivalent_curies_dict)
        # If we weren't successful at looking up some entities as curies, try looking them up as names
        if unrecognized_entities:
            equivalent_curies_dict_names = self.get_equivalent_nodes(names=unrecognized_entities, include_unrecognized_entities=False)
            equivalent_curies_dict.update(equivalent_curies_dict_names)

        # Truncate synonyms to max number allowed per node
        # First record counts for full list of equivalent curies before trimming
        equiv_curie_counts_untrimmed = {input_entity: len(equivalent_curies) if equivalent_curies else 0
                                        for input_entity, equivalent_curies in equivalent_curies_dict.items()}
        all_node_ids_untrimmed = set().union(*equivalent_curies_dict.values()) if equivalent_curies_dict else set()
        
        # Get category information from API
        if all_node_ids_untrimmed:
            api_results_untrimmed = self._call_normalizer_api(list(all_node_ids_untrimmed))
            categories_map_untrimmed = {}
            for node_id, result in api_results_untrimmed.items():
                if result is not None:
                    # Get category from the main ID or first equivalent identifier
                    types = result.get("id", {}).get("type", [])
                    if types:
                        categories_map_untrimmed[node_id] = types[0]  # Already has biolink: prefix
                    else:
                        # Try to get from equivalent identifiers
                        equiv_ids = result.get("equivalent_identifiers", [])
                        for equiv in equiv_ids:
                            equiv_types = equiv.get("type", [])
                            if equiv_types:
                                categories_map_untrimmed[node_id] = equiv_types[0]
                                break
        else:
            categories_map_untrimmed = {}
        
        category_counts_untrimmed = dict()
        equivalent_curies_dict_trimmed = dict()
        for input_entity, equivalent_curies in equivalent_curies_dict.items():
            category_counts_untrimmed[input_entity] = dict(Counter([categories_map_untrimmed.get(equiv_curie, "biolink:NamedThing")
                                                                    for equiv_curie in equivalent_curies]))
            equivalent_curies_trimmed = equivalent_curies[:max_synonyms] if equivalent_curies else None
            equivalent_curies_dict_trimmed[input_entity] = equivalent_curies_trimmed
        equivalent_curies_dict = equivalent_curies_dict_trimmed

        # Then get info for all of those equivalent nodes from API
        all_node_ids = set().union(*equivalent_curies_dict.values()) if equivalent_curies_dict else set()
        nodes_dict = {}
        if all_node_ids:
            api_results = self._call_normalizer_api(list(all_node_ids))
            for node_id, result in api_results.items():
                if result is not None:
                    main_id = result.get("id", {})
                    cluster_id = main_id.get("identifier")
                    cluster_name = main_id.get("label")
                    types = main_id.get("type", [])
                    category = types[0] if types else "NamedThing"
                    
                    # Extract information from equivalent identifiers
                    equiv_ids = result.get("equivalent_identifiers", [])
                    in_sri = False
                    name_sri = None
                    category_sri = None
                    in_kg2pre = False
                    name_kg2pre = None
                    category_kg2pre = None
                    
                    for equiv in equiv_ids:
                        equiv_id = equiv.get("identifier", "")
                        # Check if it's from SRI or KG2
                        # This is a heuristic - in practice, the API may not provide this info
                        # We'll mark all as potentially from SRI since the API is SRI-based
                        if not in_sri:
                            in_sri = True
                            name_sri = equiv.get("label")
                            equiv_types = equiv.get("type", [])
                            category_sri = equiv_types[0] if equiv_types else None
                    
                    nodes_dict[node_id] = {
                        "identifier": node_id,
                        "category": category,
                        "label": main_id.get("label", ""),
                        "major_branch": None,  # Not available from API
                        "in_sri": in_sri,
                        "name_sri": name_sri,
                        "category_sri": category_sri,
                        "in_kg2pre": in_kg2pre,
                        "name_kg2pre": name_kg2pre,
                        "category_kg2pre": category_kg2pre,
                        "cluster_id": cluster_id,
                        "cluster_preferred_name": cluster_name
                    }

        # Transform the results into the proper response format
        results_dict = dict()
        for input_entity, equivalent_curies in equivalent_curies_dict.items():
            if equivalent_curies:
                # Get cluster info from the first equivalent curie
                first_curie = next(iter(equivalent_curies))
                if first_curie in nodes_dict:
                    cluster_rep = nodes_dict[first_curie]
                    cluster_id = cluster_rep["cluster_id"]
                    # Get cluster preferred name from the cluster ID if available
                    if cluster_id in nodes_dict:
                        cluster_rep = nodes_dict[cluster_id]
                    results_dict[input_entity] = {"id": {"identifier": cluster_id,
                                                         "name": cluster_rep.get("cluster_preferred_name", cluster_rep.get("label", "")),
                                                         "category": cluster_rep.get("category", "biolink:NamedThing"),
                                                         "SRI_normalizer_name": cluster_rep.get("name_sri"),
                                                         "SRI_normalizer_category": cluster_rep.get("category_sri"),
                                                         "SRI_normalizer_curie": cluster_id if cluster_rep.get("category_sri") else None},
                                                  "total_synonyms": equiv_curie_counts_untrimmed[input_entity],
                                                  "categories": category_counts_untrimmed[input_entity],
                                                  "nodes": [nodes_dict.get(equivalent_curie, {
                                                      "identifier": equivalent_curie,
                                                      "category": "biolink:NamedThing",
                                                      "label": equivalent_curie
                                                  }) for equivalent_curie in equivalent_curies if equivalent_curie in nodes_dict]}

        # Do some post-processing (remove no-longer-needed 'cluster_id' property)
        normalizer_info = None
        for normalizer_info in results_dict.values():
            for equivalent_node in normalizer_info["nodes"]:
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
                if normalizer_info is None:
                    continue
                keys_to_delete = set(normalizer_info.keys()).difference({"id"})
                for dict_key in keys_to_delete:
                    del normalizer_info[dict_key]
        # Otherwise add in cluster graphs
        elif output_format == "slim":
            pass
        else:
            for normalizer_info in results_dict.values():
                if normalizer_info:
                    normalizer_info["knowledge_graph"] = self._get_cluster_graph(normalizer_info)

        # Attempt to squash NaNs, which are not legal in JSON. Turn them into nulls
        if ( normalizer_info is not None and 'knowledge_graph' in normalizer_info and
                normalizer_info["knowledge_graph"] is not None and 'edges' in normalizer_info["knowledge_graph"] and
                isinstance(normalizer_info["knowledge_graph"]['edges'],dict) ):
            for edge_name, edge_data in normalizer_info["knowledge_graph"]['edges'].items():
                if 'attributes' in edge_data and isinstance(edge_data['attributes'], list):
                    for attribute in edge_data['attributes']:
                        try:
                            if 'value' in attribute and math.isnan(attribute['value']):
                                attribute['value'] = None
                        except:
                            pass

        if debug:
            print(f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    # ---------------------------------------- EXTERNAL DEBUG METHODS --------------------------------------------- #

    def print_cluster_table(self, curie_or_name: str, include_edges: bool = True):
        # First figure out what cluster this concept belongs to
        canonical_info = self.get_canonical_curies(curies=curie_or_name)
        if not canonical_info.get(curie_or_name):
            canonical_info = self.get_canonical_curies(names=curie_or_name)

        # Grab the cluster nodes if we found a corresponding cluster
        if canonical_info.get(curie_or_name):
            cluster_id = canonical_info[curie_or_name]["preferred_curie"]

            # Get equivalent nodes for this cluster
            equivalent_nodes = self.get_equivalent_nodes(curies=cluster_id, include_unrecognized_entities=False)
            if cluster_id in equivalent_nodes and equivalent_nodes[cluster_id]:
                member_ids = equivalent_nodes[cluster_id]
                
                # Get node information from API
                api_results = self._call_normalizer_api(member_ids)
                
                # Build nodes dataframe
                nodes_data = []
                for node_id in member_ids:
                    if node_id in api_results and api_results[node_id] is not None:
                        result = api_results[node_id]
                        main_id = result.get("id", {})
                        types = main_id.get("type", [])
                        category = types[0].replace("biolink:", "") if types else "NamedThing"
                        name = main_id.get("label", node_id)
                        nodes_data.append({"id": node_id, "category": category, "name": name})
                
                if nodes_data:
                    import pandas as pd
                    nodes_df = pd.DataFrame(nodes_data)
                    
                    # Note: The API doesn't provide edge information, so we can't show edges
                    if include_edges:
                        print(f"\nCluster for {curie_or_name} has 0 edges (edge information not available from API):\n")
                    print(f"\nCluster for {curie_or_name} has {nodes_df.shape[0]} nodes:\n")
                    print(f"{nodes_df.to_markdown(index=False)}\n")
                else:
                    print(f"No nodes found for cluster_id {cluster_id}")
            else:
                print(f"No cluster exists with a cluster_id of {cluster_id}")
                return dict()
        else:
            print(f"Sorry, input concept {curie_or_name} is not recognized.")

    # ---------------------------------------- INTERNAL HELPER METHODS -------------------------------------------- #

    def _call_normalizer_api(self, curies: List[str]) -> dict:
        """
        Call the Node Normalizer API with a list of curies.
        Returns a dictionary mapping curie to API response (or None if not found).
        """
        if not curies:
            return {}
        
        # Batch the requests to avoid very large API calls
        batch_size = 1000
        all_results = {}
        
        for i in range(0, len(curies), batch_size):
            batch = curies[i:i + batch_size]
            try:
                response = requests.post(
                    f"{self.api_base_url}/get_normalized_nodes",
                    json={"curies": batch},
                    headers={'accept': 'application/json'},
                    timeout=30
                )
                response.raise_for_status()
                batch_results = response.json()
                all_results.update(batch_results)
            except requests.exceptions.RequestException as e:
                # If API call fails, mark all curies in batch as None
                for curie in batch:
                    all_results[curie] = None
                if len(curies) <= 10:  # Only print error for small batches to avoid spam
                    print(f"Warning: API call failed for batch: {e}")
        
        return all_results

    @staticmethod
    def _convert_to_set_format(some_value: any) -> set:
        if isinstance(some_value, set):
            return some_value
        elif isinstance(some_value, list):
            return set(some_value)
        elif isinstance(some_value, str):
            return {some_value}
        elif some_value is None:
            return set()
        else:
            # Try to convert pandas Series or other iterables
            try:
                return set(some_value)
            except TypeError:
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
        if cluster_id in trapi_nodes:
            trapi_nodes[cluster_id].attributes.append(Attribute(attribute_type_id="biolink:description",
                                                                value_type_id="metatype:String",
                                                                value="This node is the preferred/canonical identifier "
                                                                      "for this concept cluster.",
                                                                attribute_source="infores:arax"))
        kg.nodes = trapi_nodes

        # Note: The API doesn't provide edge information, so we return an empty edges dict
        kg.edges = {}

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
            "preferred_category": self._add_biolink_prefix(preferred_category) if preferred_category else None
        }


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("curie_or_name")
    # Add flags corresponding to each of the three main synonymizer methods
    arg_parser.add_argument("-c", "--canonical", dest="canonical", action="store_true")
    arg_parser.add_argument("-e", "--equivalent", dest="equivalent", action="store_true")
    arg_parser.add_argument("-n", "--normalizer", dest="normalizer", action="store_true")
    arg_parser.add_argument("-l", "--names", dest="names", action="store_true")
    arg_parser.add_argument("-p", "--preferrednames", dest="preferred_names", action="store_true")
    # Add a couple other data viewing options (tabular and TRAPI cluster graph format)
    arg_parser.add_argument("-t", "--table", dest="table", action="store_true")
    arg_parser.add_argument("-g", "--graph", dest="graph", action="store_true")
    arg_parser.add_argument("-k", "--kategory", dest="kategory", action="store_true")
    args = arg_parser.parse_args()

    synonymizer = NodeSynonymizer()
    if args.canonical:
        results = synonymizer.get_canonical_curies(curies=args.curie_or_name, debug=True)
        if not results[args.curie_or_name]:
            results = synonymizer.get_canonical_curies(names=args.curie_or_name)
        print(json.dumps(results, indent=2))
    if args.equivalent:
        results = synonymizer.get_equivalent_nodes(curies=args.curie_or_name, debug=True)
        if not results[args.curie_or_name]:
            results = synonymizer.get_equivalent_nodes(names=args.curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.normalizer:
        results = synonymizer.get_normalizer_results(entities=args.curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.names:
        results = synonymizer.get_curie_names(curies=args.curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.preferred_names:
        results = synonymizer.get_preferred_names(curies=args.curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.kategory:
        results = synonymizer.get_curie_category(curies=args.curie_or_name, debug=True)
        pprint.pprint(results)
    # Default to printing the tabular view of the cluster if nothing else was specified
    if args.table or not (args.canonical or args.equivalent or args.normalizer or args.names or args.preferred_names or args.graph):
        synonymizer.print_cluster_table(args.curie_or_name)

if __name__ == "__main__":
    main()
