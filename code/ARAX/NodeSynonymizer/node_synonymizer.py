import argparse
import collections
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Optional, Union, List, Set

import bmt  # type: ignore[import-not-found]
import pandas as pd  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration  # type: ignore[import-not-found]  # noqa: E402

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.knowledge_graph import KnowledgeGraph  # type: ignore[import-not-found]  # noqa: E402
from openapi_server.models.node import Node  # type: ignore[import-not-found]  # noqa: E402
from openapi_server.models.attribute import Attribute  # type: ignore[import-not-found]  # noqa: E402


class NodeSynonymizer:

    def __init__(self, sqlite_file_name: Optional[str] = None):
        # Kept for interface compatibility; implementation now reads from APIs.
        _ = sqlite_file_name
        self.rtx_config = RTXConfiguration()
        self.api_base_url, self.name_resolver_url = self._get_api_urls()
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
        results_dict: dict[str, Optional[dict[str, Any]]] = {}

        if curies_set:
            api_results = self._call_normalizer_api(list(curies_set))

            for input_curie in curies_set:
                if input_curie in api_results and api_results[input_curie] is not None:
                    result = api_results[input_curie]
                    preferred_id = result.get("id", {}).get("identifier")
                    # New API returns categories in top-level "type", not under "id".
                    types = result.get("type", [])
                    preferred_category = types[0] if types else None
                    preferred_name = result.get("id", {}).get("label")
                    if preferred_category:
                        preferred_category = preferred_category.replace("biolink:", "")
                    results_dict[input_curie] = self._create_preferred_node_dict(
                        preferred_id=preferred_id,
                        preferred_category=preferred_category,
                        preferred_name=preferred_name
                    )

        if names_set:
            # Old SQLite implementation could query names directly from `nodes.name_simplified`.
            # In API mode we must do a two-step lookup:
            #   1) Name Resolver `/bulk-lookup` -> best CURIE candidate
            #   2) Node Normalizer `/get_normalized_nodes` -> canonical metadata
            name_to_curie = self._call_name_resolver_api(list(names_set))
            resolved_curies = [c for c in name_to_curie.values() if c is not None]
            if resolved_curies:
                api_results = self._call_normalizer_api(resolved_curies)
                for name in names_set:
                    curie = name_to_curie.get(name)
                    if curie and curie in api_results and api_results[curie] is not None:
                        result = api_results[curie]
                        types = result.get("type", [])
                        preferred_category = types[0] if types else None
                        if preferred_category:
                            preferred_category = preferred_category.replace("biolink:", "")
                        results_dict[name] = self._create_preferred_node_dict(
                            preferred_id=result.get("id", {}).get("identifier"),
                            preferred_category=preferred_category,
                            preferred_name=result.get("id", {}).get("label")
                        )

        if return_all_categories:
            # Old DB flow counted member categories from per-node rows in `nodes.category`.
            # New API flow exposes categories at cluster level (`result["type"]`) and does not
            # annotate each equivalent identifier with its own category. We approximate prior
            # semantics by weighting each returned category by cluster size.
            cluster_ids = {canonical_info["preferred_curie"]
                           for canonical_info in results_dict.values() if canonical_info}
            if cluster_ids:
                api_results = self._call_normalizer_api(list(cluster_ids))

                clusters_by_category_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
                for cluster_id, result in api_results.items():
                    if result is not None:
                        # Old DB counted member categories directly, API only provides cluster-level types.
                        num_equivs = len(result.get("equivalent_identifiers", []))
                        for category in result.get("type", []):
                            category_with_prefix = self._add_biolink_prefix(category.replace("biolink:", ""))
                            if category_with_prefix is None:
                                continue
                            clusters_by_category_counts[cluster_id][category_with_prefix] += max(num_equivs, 1)

                for canonical_info in results_dict.values():
                    if canonical_info:
                        cluster_id = canonical_info["preferred_curie"]
                        category_counts: dict[str, int] = dict(clusters_by_category_counts.get(cluster_id, {}))
                        canonical_info["all_categories"] = dict(category_counts)

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
        results_dict: dict[str, Optional[list[str]]] = {}

        if curies_set:
            api_results = self._call_normalizer_api(list(curies_set))

            for input_curie in curies_set:
                if input_curie in api_results and api_results[input_curie] is not None:
                    result = api_results[input_curie]
                    # Guardrail for API variance:
                    # occasionally `equivalent_identifiers` may contain records without `identifier`.
                    # The old SQLite path never produced such rows (ID column was NOT NULL), so we
                    # drop them to preserve legacy behavior and avoid `None` in synonym lists.
                    equivalent_ids = [equiv.get("identifier") for equiv in result.get("equivalent_identifiers", []) if equiv.get("identifier")]
                    main_id = result.get("id", {}).get("identifier")
                    if main_id:
                        equivalent_ids.append(main_id)
                    results_dict[input_curie] = list(set(equivalent_ids))

        if names_set:
            name_to_curie = self._call_name_resolver_api(list(names_set))
            resolved_curies = [c for c in name_to_curie.values() if c is not None]
            if resolved_curies:
                api_results = self._call_normalizer_api(resolved_curies)
                for name in names_set:
                    curie = name_to_curie.get(name)
                    if curie and curie in api_results and api_results[curie] is not None:
                        result = api_results[curie]
                        equivalent_ids = [equiv.get("identifier") for equiv in result.get("equivalent_identifiers", []) if equiv.get("identifier")]
                        main_id = result.get("id", {}).get("identifier")
                        if main_id:
                            equivalent_ids.append(main_id)
                        results_dict[name] = list(set(equivalent_ids))

        if include_unrecognized_entities:
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
        results_dict: dict[str, str] = {}

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
        results_dict: dict[str, str] = {}

        if curies_set:
            api_results = self._call_normalizer_api(list(curies_set))
            for input_curie in curies_set:
                result = api_results.get(input_curie)
                if not result:
                    continue
                for equiv in result.get("equivalent_identifiers", []):
                    if equiv.get("identifier") == input_curie and equiv.get("label"):
                        results_dict[input_curie] = equiv["label"]
                        break

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

        curies_set = self._convert_to_set_format(curies)
        best_by_parent: dict[str, str] = {}

        if curies_set:
            api_results = self._call_normalizer_api(list(curies_set))
            levels_by_curie: dict[str, dict[str, int]] = {}
            for curie, result in api_results.items():
                if result is None:
                    continue
                category_levels: dict[str, int] = {}
                for category in result.get("type", []):
                    level = self.category_levels.get(category.replace("biolink:", ""))
                    if level is not None:
                        category_levels[category] = level
                levels_by_curie[curie] = category_levels
            # Old implementation returned one category from a single DB column.
            # API returns a category list; choose the most specific one (deepest in Biolink hierarchy)
            # so downstream consumers still receive one deterministic category per input CURIE.
            best_by_parent = {
                parent_key: max(subdict.items(), key=lambda kv: kv[1])[0]
                for parent_key, subdict in levels_by_curie.items() if subdict
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

        output_format = None
        if isinstance(entities, dict):
            entities_dict = entities
            entities = entities_dict.get("terms")
            output_format = entities_dict.get("format")

            max_synonyms_raw = entities_dict.get("max_synonyms")
            try:
                max_synonyms_int = int(max_synonyms_raw)
                if max_synonyms_int > 0:
                    max_synonyms = max_synonyms_int
            except (TypeError, ValueError):
                pass

        entities_set = self._convert_to_set_format(entities)

        equivalent_curies_raw = self.get_equivalent_nodes(curies=entities_set, include_unrecognized_entities=False)
        equivalent_curies_dict = {entity: curies for entity, curies in equivalent_curies_raw.items() if curies}
        unrecognized_entities = entities_set.difference(equivalent_curies_dict)
        if unrecognized_entities:
            # Preserve old behavior: if direct CURIE lookup misses, retry as name-based lookup.
            equivalent_curies_dict_names_raw = self.get_equivalent_nodes(names=unrecognized_entities, include_unrecognized_entities=False)
            equivalent_curies_dict_names = {entity: curies
                                           for entity, curies in equivalent_curies_dict_names_raw.items() if curies}
            equivalent_curies_dict.update(equivalent_curies_dict_names)

        equiv_curie_counts_untrimmed = {input_entity: len(equivalent_curies) if equivalent_curies else 0
                                        for input_entity, equivalent_curies in equivalent_curies_dict.items()}
        all_node_ids_untrimmed = set().union(*equivalent_curies_dict.values()) if equivalent_curies_dict else set()
        categories_map_untrimmed = {}
        if all_node_ids_untrimmed:
            api_results_untrimmed = self._call_normalizer_api(list(all_node_ids_untrimmed))
            for node_id, result in api_results_untrimmed.items():
                if result is not None:
                    types = result.get("type", [])
                    if types:
                        # API `type` is top-level and cluster-oriented; use first type as primary category
                        # to mimic legacy single-category node records.
                        categories_map_untrimmed[node_id] = types[0]

        category_counts_untrimmed: dict[str, dict[str, int]] = {}
        equivalent_curies_dict_trimmed: dict[str, list[str]] = {}
        for input_entity, equivalent_curies in equivalent_curies_dict.items():
            category_counts_untrimmed[input_entity] = dict(Counter([categories_map_untrimmed.get(equiv_curie, "biolink:NamedThing")
                                                                    for equiv_curie in equivalent_curies]))
            equivalent_curies_trimmed = equivalent_curies[:max_synonyms]
            equivalent_curies_dict_trimmed[input_entity] = equivalent_curies_trimmed
        equivalent_curies_dict = equivalent_curies_dict_trimmed

        # Then get info for all of those equivalent nodes from API
        all_node_ids = set().union(*equivalent_curies_dict.values()) if equivalent_curies_dict else set()
        nodes_dict: dict[str, dict[str, Any]] = {}
        if all_node_ids:
            api_results = self._call_normalizer_api(list(all_node_ids))
            for node_id, result in api_results.items():
                if result is not None:
                    main_id = result.get("id", {})
                    cluster_id = main_id.get("identifier")
                    cluster_name = main_id.get("label")
                    types = result.get("type", [])
                    category = types[0] if types else "biolink:NamedThing"

                    equiv_ids = result.get("equivalent_identifiers", [])
                    in_sri = False
                    name_sri = None
                    category_sri = None
                    in_kg2pre = False
                    name_kg2pre = None
                    category_kg2pre = None

                    if equiv_ids:
                        # In API mode all records come from Node Normalizer, so `in_sri=True`
                        # when we have any equivalent identifiers. We keep legacy output fields
                        # for compatibility even though some SQLite-era source distinctions are gone.
                        in_sri = True
                        name_sri = equiv_ids[0].get("label")
                        category_sri = types[0] if types else None
                    
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

        results_dict: dict[str, Optional[dict[str, Any]]] = {}
        for input_entity, equivalent_curies in equivalent_curies_dict.items():
            if equivalent_curies:
                first_curie = next(iter(equivalent_curies))
                if first_curie in nodes_dict:
                    cluster_rep = nodes_dict[first_curie]
                    cluster_id = cluster_rep["cluster_id"]
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
                                                  }) for equivalent_curie in equivalent_curies]}

        for normalizer_info in results_dict.values():
            if normalizer_info is None:
                continue
            for equivalent_node in normalizer_info["nodes"]:
                if "cluster_id" in equivalent_node:
                    del equivalent_node["cluster_id"]
                if "cluster_preferred_name" in equivalent_node:
                    del equivalent_node["cluster_preferred_name"]
            normalizer_info["nodes"].sort(key=lambda node: node["identifier"].upper())

        unrecognized_curies = entities_set.difference(results_dict)
        for unrecognized_curie in unrecognized_curies:
            results_dict[unrecognized_curie] = None

        if output_format == "minimal":
            for normalizer_info in results_dict.values():
                if normalizer_info is None:
                    continue
                keys_to_delete = set(normalizer_info.keys()).difference({"id"})
                for dict_key in keys_to_delete:
                    del normalizer_info[dict_key]
        elif output_format == "slim":
            pass
        else:
            for normalizer_info in results_dict.values():
                if normalizer_info:
                    normalizer_info["knowledge_graph"] = self._get_cluster_graph(normalizer_info)

        for normalizer_info in results_dict.values():
            if (normalizer_info is None or "knowledge_graph" not in normalizer_info or
                    normalizer_info["knowledge_graph"] is None or
                    "edges" not in normalizer_info["knowledge_graph"] or
                    not isinstance(normalizer_info["knowledge_graph"]["edges"], dict)):
                continue
            for _, edge_data in normalizer_info["knowledge_graph"]["edges"].items():
                if 'attributes' in edge_data and isinstance(edge_data['attributes'], list):
                    for attribute in edge_data['attributes']:
                        try:
                            if 'value' in attribute and math.isnan(attribute['value']):
                                attribute['value'] = None
                        except (TypeError, ValueError):
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

        if canonical_info.get(curie_or_name):
            cluster_id = canonical_info[curie_or_name]["preferred_curie"]

            equivalent_nodes = self.get_equivalent_nodes(curies=cluster_id, include_unrecognized_entities=False)
            if cluster_id in equivalent_nodes and equivalent_nodes[cluster_id]:
                member_ids = equivalent_nodes[cluster_id]

                api_results = self._call_normalizer_api(member_ids)

                nodes_data = []
                for node_id in member_ids:
                    if node_id in api_results and api_results[node_id] is not None:
                        result = api_results[node_id]
                        main_id = result.get("id", {})  # keep node label from canonical record
                        types = result.get("type", [])
                        category = types[0].replace("biolink:", "") if types else "NamedThing"
                        name = main_id.get("label", node_id)
                        nodes_data.append({"id": node_id, "category": category, "name": name})
                
                if nodes_data:
                    nodes_df = pd.DataFrame(nodes_data)

                    # Old SQLite output included intra-cluster edges; API does not expose them.
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
                for curie in batch:
                    all_results[curie] = None
                if len(curies) <= 10:
                    print(f"Warning: API call failed for batch: {e}")
        
        return all_results

    def _call_name_resolver_api(self, names: List[str]) -> dict:
        # Name lookup is a required pre-step in API mode because Node Normalizer only accepts CURIEs.
        # We ask for a single best hit (`limit=1`) with autocomplete enabled, which is closest to the
        # old DB strategy of collapsing ambiguous names to one representative cluster.
        if not names:
            return {}

        results = {}
        try:
            response = requests.post(
                f"{self.name_resolver_url}/bulk-lookup",
                json={"strings": names, "autocomplete": True, "limit": 1},
                headers={"accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            for name in names:
                candidates = data.get(name, [])
                results[name] = candidates[0]["curie"] if candidates else None
        except requests.exceptions.RequestException as e:
            for name in names:
                results[name] = None
            print(f"Warning: Name Resolver API call failed: {e}")

        return results

    @staticmethod
    def _convert_to_set_format(some_value: Any) -> set:
        if isinstance(some_value, set):
            return some_value
        if isinstance(some_value, list):
            return set(some_value)
        if isinstance(some_value, str):
            return {some_value}
        if some_value is None:
            return set()
        try:
            return set(some_value)
        except TypeError as error:
            raise ValueError("Input is not an allowable data type (list, set, or string)!") from error

    @staticmethod
    def _add_biolink_prefix(category: Optional[str]) -> Optional[str]:
        if category:
            return f"biolink:{category}"
        else:
            return category

    def _get_api_urls(self) -> tuple[str, str]:
        # Project convention: use RTXConfiguration/config-file overrides, not env vars.
        node_normalizer_url = self.rtx_config.config_dbs.get("node_normalizer_url_override")
        name_resolver_url = self.rtx_config.config_dbs.get("name_resolver_url_override")
        if node_normalizer_url and name_resolver_url:
            return node_normalizer_url.rstrip("/"), name_resolver_url.rstrip("/")
        if node_normalizer_url or name_resolver_url:
            raise ValueError("Both node_normalizer_url_override and name_resolver_url_override must be set together in config_dbs.json")

        # Default to prod only on production maturity; use CI elsewhere.
        if self.rtx_config.maturity == "production":
            return "https://nodenorm.transltr.io/1.5", "https://name-lookup.transltr.io"
        return "https://nodenorm.ci.transltr.io/1.5", "https://name-lookup.ci.transltr.io"

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

        # Old DB-backed synonymizer had intra-cluster edges, API-backed version has membership only.
        kg.edges = {}

        return kg.to_dict()

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

    def _create_preferred_node_dict(self, preferred_id: Optional[str], preferred_category: Optional[str], preferred_name: Optional[str]) -> dict:
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
        print(json.dumps(results, indent=2))
    # Default to printing the tabular view of the cluster if nothing else was specified
    if args.table or not (args.canonical or args.equivalent or args.normalizer or args.names or args.preferred_names or args.graph):
        synonymizer.print_cluster_table(args.curie_or_name)

if __name__ == "__main__":
    main()
