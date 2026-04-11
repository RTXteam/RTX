"""API-backed Node Synonymizer for CURIE/name normalization via SRI services."""
import argparse
import asyncio
import collections
import json
import logging
import math
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Optional, Union, List, Set

import aiohttp  # type: ignore[import-untyped]
import bmt  # type: ignore[import-not-found]
import pandas as pd  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]

# The ARAX repo doesn't use a standard Python package layout,
# so we need sys.path.append to resolve cross-module imports.
# This means pylint can't find these modules (import-error)
# and the imports come after non-import code (wrong-import-position).
# This pattern is standard across all ARAX source files.
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration  # type: ignore[import-not-found]  # noqa: E402  # pylint: disable=import-error,wrong-import-position

sys.path.append(os.path.sep.join(
    [*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))

sys.path.append(os.path.sep.join(
    [*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI',
     'python-flask-server']))
from openapi_server.models.knowledge_graph import KnowledgeGraph  # type: ignore[import-not-found]  # noqa: E402  # pylint: disable=import-error,wrong-import-position
from openapi_server.models.node import Node  # type: ignore[import-not-found]  # noqa: E402  # pylint: disable=import-error,wrong-import-position
from openapi_server.models.attribute import Attribute  # type: ignore[import-not-found]  # noqa: E402  # pylint: disable=import-error,wrong-import-position


logger = logging.getLogger(__name__)

# 13 instance attrs (limit 7): API URLs, session, cache, config,
# infores CURIEs, bmt toolkit, category levels. All needed for the
# API-based lifecycle — the old SQLite version had similar state.
class NodeSynonymizer:  # pylint: disable=too-many-instance-attributes
    """CURIE/name normalization via SRI Node Normalizer and Name Resolver APIs.

    Migration context (issue #2585):
    The old implementation queried a local SQLite database built
    from KG2 + SRI bulk downloads. This version replaces all
    SQLite queries with live API calls to two SRI services:

    SRI Node Normalizer (CURIE -> canonical info + equivalents):
      Production: https://nodenorm.transltr.io/1.5
      CI/Dev:     https://nodenorm.ci.transltr.io/1.5
      Docs:       https://nodenorm.ci.transltr.io/1.5/docs
      Main endpoint: POST /get_normalized_nodes

    SRI Name Resolver (free-text name -> best CURIE match):
      CI/Dev:     https://name-lookup.ci.transltr.io
      Production: https://name-lookup.transltr.io  (NO /bulk-lookup)
      Docs:       https://name-lookup.ci.transltr.io/docs
      Main endpoint: POST /bulk-lookup
      WARNING: The production Name Resolver deployment does NOT
      expose /bulk-lookup -- only /lookup, /reverse_lookup, /status.
      This implementation relies on /bulk-lookup, so it currently
      only works against the CI endpoint. Selecting the production
      URL in _get_api_urls() will cause every name-based call to
      fail with HTTP 404 until either:
        (a) the production deployment adds /bulk-lookup, or
        (b) this code falls back to the single-string /lookup.

    Which URLs are used depends on the ARAX maturity setting:
    production maturity uses production URLs, everything else
    (dev, test, beta) uses CI URLs. This is handled in
    _get_api_urls(). Both can be overridden via config_dbs.json
    keys: node_normalizer_url_override, name_resolver_url_override.

    The return contracts (get_canonical_curies, get_equivalent_nodes,
    get_normalizer_results) are preserved so downstream ARAX callers
    don't need changes.
    """

    def __init__(self, sqlite_file_name: Optional[str] = None,
                 autocomplete: bool = True,
                 use_async: bool = False):
        # sqlite_file_name: kept for interface compat so existing
        # callers don't break. The new implementation ignores it
        # entirely — no local database is used.
        _ = sqlite_file_name

        # autocomplete controls the Name Resolver's behavior.
        # True (default) = partial/fuzzy name matching, which
        # is what ARAX needs for query resolution.
        # False = exact phrase matching, used for NGD builds
        # where we need precise name-to-curie mapping.
        self._autocomplete = autocomplete

        # use_async controls whether _call_name_resolver_api
        # sends batches sequentially (sync, default) or
        # concurrently via aiohttp (async). Async sends up to
        # MAX_CONCURRENT batches in parallel using a semaphore,
        # which gives ~4-5x speedup on bulk workloads like the
        # NGD build (~8M names). Default is sync because most
        # ARAX callers send small name lists where the overhead
        # of an event loop isn't worth it.
        self._use_async = use_async

        self.rtx_config = RTXConfiguration()
        self.api_base_url, self.name_resolver_url = (
            self._get_api_urls())
        self.kg2_infores_curie = "infores:rtx-kg2"
        self.sri_nn_infores_curie = "infores:sri-node-normalizer"
        self.arax_infores_curie = "infores:arax"
        self.bmt_tk = bmt.Toolkit()
        self.category_levels = self._get_categories_and_levels()

        # Since we now hit external APIs instead of a local DB,
        # connection reuse and caching matter a lot more.
        # requests.Session keeps TCP connections alive across
        # calls to the same host, avoiding repeated TLS
        # handshakes.
        self._session = requests.Session()
        self._session.headers.update({'accept': 'application/json'})

        # In-memory CURIE cache: the old SQLite was essentially
        # an on-disk cache. With APIs, repeated lookups for the
        # same CURIE (which happens often in get_normalizer_results)
        # would be redundant network calls. This dict stores
        # Node Normalizer responses so each CURIE is fetched once
        # per NodeSynonymizer instance.
        self._normalizer_cache: dict[str, dict | None] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    # ------------ EXTERNAL MAIN METHODS ------------- #

    # Locals/branches are high because this method orchestrates
    # a multi-step API workflow (curie lookup, name resolution,
    # category aggregation). Splitting further would fragment
    # the sequential flow and make it harder to follow.
    def get_canonical_curies(  # pylint: disable=too-many-locals,too-many-branches
            self,
            curies: Optional[Union[str, Set[str], List[str]]] = None,
            names: Optional[Union[str, Set[str], List[str]]] = None,
            return_all_categories: bool = False,
            debug: bool = False) -> dict:
        """Return canonical CURIE info for input curies and/or names."""
        start = time.time()

        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict: dict[str, Optional[dict[str, Any]]] = {}

        # CURIE branch: send directly to Node Normalizer.
        # Response "type" is the cluster-level category list,
        # and "id" holds the canonical identifier + label.
        if curies_set:
            api_results = self._call_normalizer_api(list(curies_set))

            for input_curie in curies_set:
                api_val = api_results.get(input_curie)
                if api_val is not None:
                    result = api_val
                    preferred_id = (
                        result.get("id", {}).get("identifier"))
                    # Node Normalizer returns categories in
                    # top-level "type", not inside "id".
                    types = result.get("type", [])
                    preferred_category = (
                        types[0] if types else None)
                    preferred_name = (
                        result.get("id", {}).get("label"))
                    if preferred_category:
                        preferred_category = (
                            preferred_category.replace(
                                "biolink:", ""))
                    results_dict[input_curie] = (
                        self._create_preferred_node_dict(
                            preferred_id=preferred_id,
                            preferred_category=preferred_category,
                            preferred_name=preferred_name
                        ))

        # Name branch: two-step lookup required because the
        # Node Normalizer only accepts CURIEs, not free text.
        # Step 1: Name Resolver /bulk-lookup → best CURIE
        # Step 2: Node Normalizer /get_normalized_nodes → metadata
        # The old SQLite could resolve names directly from
        # a `name_simplified` column. With APIs we need both.
        if names_set:
            name_to_curie = self._call_name_resolver_api(
                list(names_set))
            resolved_curies = [
                c for c in name_to_curie.values()
                if c is not None]
            if resolved_curies:
                api_results = self._call_normalizer_api(
                    resolved_curies)
                for name in names_set:
                    # If curie branch already resolved this
                    # string, skip to avoid overwriting.
                    if name in results_dict:
                        continue
                    curie = name_to_curie.get(name)
                    api_val = api_results.get(curie)
                    if curie and api_val is not None:
                        result = api_val
                        types = result.get("type", [])
                        if "id" not in result:
                            raise ValueError(
                                f"for name {name}, there is "
                                "no field 'id' in the result")
                        result_name_dict = result["id"]
                        if "label" not in result_name_dict:
                            raise ValueError(
                                f"for name {name}, there is "
                                "no 'label' field in the 'id'"
                                " dictionary in the result")
                        result_name = result_name_dict['label']
                        if not self._names_match(
                                name, result_name):
                            results_dict[name] = None
                            continue
                        preferred_category = (
                            types[0] if types else None)
                        if preferred_category:
                            preferred_category = (
                                preferred_category.replace(
                                    "biolink:", ""))
                        results_dict[name] = (
                            self._create_preferred_node_dict(
                                preferred_id=result.get(
                                    "id", {}).get("identifier"),
                                preferred_category=(
                                    preferred_category),
                                preferred_name=result.get(
                                    "id", {}).get("label")
                            ))

        if return_all_categories:
            self._populate_all_categories(results_dict)

        unrecognized = (
            curies_set.union(names_set)).difference(results_dict)
        for val in unrecognized:
            results_dict[val] = None

        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def _populate_all_categories(
            self,
            results_dict: dict[str, Optional[dict[str, Any]]]
    ) -> None:
        """Add all_categories counts to each entry in results_dict.

        Note: this is an approximation. The old SQLite counted
        categories per-node (each equivalent ID had its own
        category). The Node Normalizer API only exposes
        cluster-level categories in the "type" field, so we
        weight each category by the total number of equivalent
        identifiers. The counts are larger than old SQLite
        values, but relative ordering is preserved and
        downstream callers only check count > 0.
        """
        cluster_ids = {
            info["preferred_curie"]
            for info in results_dict.values() if info}
        if not cluster_ids:
            return
        api_results = self._call_normalizer_api(
            list(cluster_ids))

        cat_counts: defaultdict[str, defaultdict[str, int]] = (
            defaultdict(lambda: defaultdict(int)))
        for cluster_id, result in api_results.items():
            if result is None:
                continue
            num_equivs = len(
                result.get("equivalent_identifiers", []))
            for category in result.get("type", []):
                cat_with_prefix = self._add_biolink_prefix(
                    category.replace("biolink:", ""))
                if cat_with_prefix is None:
                    continue
                cat_counts[cluster_id][cat_with_prefix] += (
                    max(num_equivs, 1))

        for canonical_info in results_dict.values():
            if canonical_info:
                cid = canonical_info["preferred_curie"]
                canonical_info["all_categories"] = dict(
                    cat_counts.get(cid, {}))

    # Same rationale as get_canonical_curies — multi-step API
    # workflow with curie + name resolution branches.
    def get_equivalent_nodes(  # pylint: disable=too-many-locals
            self,
            curies: Optional[
                Union[str, Set[str], List[str]]] = None,
            names: Optional[
                Union[str, Set[str], List[str]]] = None,
            include_unrecognized_entities: bool = True,
            debug: bool = False) -> dict:
        """Return equivalent node CURIEs for input curies/names."""
        start = time.time()

        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict: dict[str, Optional[list[str]]] = {}

        if curies_set:
            api_results = self._call_normalizer_api(
                list(curies_set))
            for input_curie in curies_set:
                api_val = api_results.get(input_curie)
                if api_val is not None:
                    result = api_val
                    equivalent_ids = [
                        equiv.get("identifier")
                        for equiv in result.get(
                            "equivalent_identifiers", [])
                        if equiv.get("identifier")]
                    main_id = (
                        result.get("id", {}).get("identifier"))
                    if main_id:
                        equivalent_ids.append(main_id)
                    results_dict[input_curie] = (
                        self._dedupe_preserve_order(
                            equivalent_ids))

        if names_set:
            name_to_curie = self._call_name_resolver_api(
                list(names_set))
            resolved_curies = [
                c for c in name_to_curie.values()
                if c is not None]
            if resolved_curies:
                api_results = self._call_normalizer_api(
                    resolved_curies)
                for name in names_set:
                    curie = name_to_curie.get(name)
                    api_val = api_results.get(curie)
                    if curie and api_val is not None:
                        result = api_val
                        equivalent_ids = [
                            equiv.get("identifier")
                            for equiv in result.get(
                                "equivalent_identifiers", [])
                            if equiv.get("identifier")]
                        main_id = result.get(
                            "id", {}).get("identifier")
                        if main_id:
                            equivalent_ids.append(main_id)
                        results_dict[name] = (
                            self._dedupe_preserve_order(
                                equivalent_ids))

        if include_unrecognized_entities:
            unrecognized = (
                curies_set.union(names_set)
            ).difference(results_dict)
            for curie in unrecognized:
                results_dict[curie] = None

        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_preferred_names(
            self,
            curies: Union[str, Set[str], List[str]],
            debug: bool = False) -> dict:
        """Return preferred names for input curies."""
        start = time.time()

        curies_set = self._convert_to_set_format(curies)
        results_dict: dict[str, str] = {}

        if curies_set:
            curies_list = list(curies_set)
            api_results = self._call_normalizer_api(curies_list)
            results_dict = {
                k: v['id']['label']
                for k, v in api_results.items()
                if v is not None
                and v.get('id', {}).get('label')}

        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_curie_names(
            self,
            curies: Union[str, Set[str], List[str]],
            debug: bool = False) -> dict:
        """Return NON-preferred names for input curies.

        Returns the curie's direct name, not the name of its
        canonical identifier.
        """
        start = time.time()

        curies_set = self._convert_to_set_format(curies)
        results_dict: dict[str, str] = {}

        if curies_set:
            api_results = self._call_normalizer_api(
                list(curies_set))
            for input_curie in curies_set:
                result = api_results.get(input_curie)
                if not result:
                    continue
                for equiv in result.get(
                        "equivalent_identifiers", []):
                    if (equiv.get("identifier") == input_curie
                            and equiv.get("label")):
                        results_dict[input_curie] = (
                            equiv["label"])
                        break

        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def get_curie_category(
            self,
            curies: Union[str, Set[str], List[str]],
            debug: bool = False) -> dict:
        """Return the most specific Biolink category for each input curie."""
        start = time.time()

        curies_set = self._convert_to_set_format(curies)
        best_by_parent: dict[str, str] = {}

        if curies_set:
            api_results = self._call_normalizer_api(
                list(curies_set))
            levels_by_curie: dict[str, dict[str, int]] = {}
            for curie, result in api_results.items():
                if result is None:
                    continue
                category_levels: dict[str, int] = {}
                for category in result.get("type", []):
                    level = self.category_levels.get(
                        category.replace("biolink:", ""))
                    if level is not None:
                        category_levels[category] = level
                levels_by_curie[curie] = category_levels
            best_by_parent = {
                parent_key: max(
                    subdict.items(),
                    key=lambda kv: kv[1])[0]
                for parent_key, subdict
                in levels_by_curie.items() if subdict
            }
        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return best_by_parent

    def _get_categories_and_levels(
            self, debug: bool = False) -> dict[str, int]:
        """Build Biolink category hierarchy with depth levels."""
        start = time.time()
        q = collections.deque(['biolink:NamedThing'])
        levels = {'biolink:NamedThing': 0}
        while q:
            item = q.popleft()
            for neighbor in self.bmt_tk.get_children(
                    item, formatted=True):
                if neighbor not in levels:
                    levels[neighbor] = levels[item] + 1
                    q.append(neighbor)
        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return {
            k.replace("biolink:", ""): v
            for k, v in levels.items()}

    def get_distinct_category_list(
            self, debug: bool = False) -> list:
        """Return all known Biolink category names."""
        start = time.time()
        result = list(self.category_levels.keys())
        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return result

    # This is the most complex public method — it combines
    # equivalent node lookup, category counting, node metadata
    # assembly, trimming, and output formatting. Already split
    # into 6 helper methods; remaining locals are inherent.
    def get_normalizer_results(  # pylint: disable=too-many-locals
            self,
            entities: Optional[
                Union[str, Set[str], List[str]]],
            max_synonyms: int = 1000000,
            debug: bool = False) -> dict:
        """Return full normalizer info including equivalents and KG."""
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

        equiv_raw = self.get_equivalent_nodes(
            curies=entities_set,
            include_unrecognized_entities=False)
        equiv_dict = {
            entity: curies_list
            for entity, curies_list in equiv_raw.items()
            if curies_list}
        unrecognized_entities = (
            entities_set.difference(equiv_dict))
        if unrecognized_entities:
            equiv_names_raw = self.get_equivalent_nodes(
                names=unrecognized_entities,
                include_unrecognized_entities=False)
            equiv_names = {
                entity: curies_list
                for entity, curies_list
                in equiv_names_raw.items()
                if curies_list}
            equiv_dict.update(equiv_names)

        equiv_counts_untrimmed = {
            ent: len(eq) if eq else 0
            for ent, eq in equiv_dict.items()}

        # Optimization: collect ALL equivalent CURIE IDs
        # upfront and fetch them in ONE API call. The old
        # code made separate calls for categories and node
        # metadata. With network latency this matters, and
        # the in-memory cache handles overlap with the
        # get_equivalent_nodes calls above.
        all_ids_untrimmed = (
            set().union(*equiv_dict.values())
            if equiv_dict else set())
        all_api_results: dict[str, dict | None] = {}
        if all_ids_untrimmed:
            all_api_results = self._call_normalizer_api(
                list(all_ids_untrimmed))

        categories_map: dict[str, str] = {}
        for node_id, result in all_api_results.items():
            if result is not None:
                types = result.get("type", [])
                if types:
                    categories_map[node_id] = types[0]

        cat_counts_untrimmed: dict[str, dict[str, int]] = {}
        equiv_dict_trimmed: dict[str, list[str]] = {}
        for input_entity, eq_curies in equiv_dict.items():
            cat_counts_untrimmed[input_entity] = dict(Counter(
                [categories_map.get(ec, "biolink:NamedThing")
                 for ec in eq_curies]))
            equiv_dict_trimmed[input_entity] = (
                eq_curies[:max_synonyms])
        equiv_dict = equiv_dict_trimmed

        all_node_ids = (
            set().union(*equiv_dict.values())
            if equiv_dict else set())
        missing_ids = all_node_ids - set(all_api_results.keys())
        if missing_ids:
            extra = self._call_normalizer_api(list(missing_ids))
            all_api_results.update(extra)

        nodes_dict = self._build_nodes_dict(
            all_node_ids, all_api_results)

        results_dict = self._build_normalizer_results(
            equiv_dict, nodes_dict,
            equiv_counts_untrimmed, cat_counts_untrimmed)

        self._clean_normalizer_nodes(results_dict)

        unrecognized = entities_set.difference(results_dict)
        for curie in unrecognized:
            results_dict[curie] = None

        self._apply_output_format(
            results_dict, output_format)

        self._sanitize_nan_attributes(results_dict)

        if debug:
            print(
                f"Took {round(time.time() - start, 5)} seconds")
        return results_dict

    def _build_nodes_dict(
            self,
            all_node_ids: set,
            all_api_results: dict[str, dict | None]
    ) -> dict[str, dict[str, Any]]:
        """Build per-node metadata dict from API results.

        The output dict preserves the same field names that
        the old SQLite version produced (in_sri, name_sri,
        category_sri, in_kg2pre, name_kg2pre, category_kg2pre).
        In API mode all data comes from the Node Normalizer,
        so in_sri is always True when we have equivalent IDs,
        and in_kg2pre is always False (KG2pre source info is
        not available from the API).
        """
        nodes_dict: dict[str, dict[str, Any]] = {}
        for node_id in all_node_ids:
            result = all_api_results.get(node_id)
            if result is None:
                continue
            main_id = result.get("id", {})
            cluster_id = main_id.get("identifier")
            cluster_name = main_id.get("label")
            types = result.get("type", [])
            category = (
                types[0] if types else "biolink:NamedThing")

            equiv_ids = result.get(
                "equivalent_identifiers", [])
            in_sri = bool(equiv_ids)
            name_sri = (
                equiv_ids[0].get("label") if equiv_ids
                else None)
            category_sri = (
                types[0] if (types and equiv_ids)
                else None)

            nodes_dict[node_id] = {
                "identifier": node_id,
                "category": category,
                "label": main_id.get("label", ""),
                "major_branch": None,
                "in_sri": in_sri,
                "name_sri": name_sri,
                "category_sri": category_sri,
                "in_kg2pre": False,
                "name_kg2pre": None,
                "category_kg2pre": None,
                "cluster_id": cluster_id,
                "cluster_preferred_name": cluster_name
            }
        return nodes_dict

    # Builds the nested result dict for each input entity.
    # The local vars come from unpacking cluster metadata
    # into the return contract fields.
    def _build_normalizer_results(  # pylint: disable=too-many-locals
            self,
            equiv_dict: dict[str, list[str]],
            nodes_dict: dict[str, dict[str, Any]],
            equiv_counts: dict[str, int],
            cat_counts: dict[str, dict[str, int]]
    ) -> dict[str, Optional[dict[str, Any]]]:
        """Assemble the normalizer result dict per input entity."""
        results_dict: dict[str, Optional[dict[str, Any]]] = {}
        for input_entity, eq_curies in equiv_dict.items():
            if not eq_curies:
                continue
            first_curie = next(iter(eq_curies))
            if first_curie not in nodes_dict:
                continue
            cluster_rep = nodes_dict[first_curie]
            cluster_id = cluster_rep["cluster_id"]
            cluster_rep = nodes_dict.get(
                cluster_id, cluster_rep)
            fallback_name = cluster_rep.get(
                "cluster_preferred_name",
                cluster_rep.get("label", ""))
            fallback_cat = cluster_rep.get(
                "category", "biolink:NamedThing")
            sri_curie = (
                cluster_id
                if cluster_rep.get("category_sri")
                else None)
            node_list = [
                nodes_dict.get(ec, {
                    "identifier": ec,
                    "category": "biolink:NamedThing",
                    "label": ec
                }) for ec in eq_curies]
            results_dict[input_entity] = {
                "id": {
                    "identifier": cluster_id,
                    "name": fallback_name,
                    "category": fallback_cat,
                    "SRI_normalizer_name": cluster_rep.get(
                        "name_sri"),
                    "SRI_normalizer_category": cluster_rep.get(
                        "category_sri"),
                    "SRI_normalizer_curie": sri_curie},
                "total_synonyms": equiv_counts[input_entity],
                "categories": cat_counts[input_entity],
                "nodes": node_list}
        return results_dict

    @staticmethod
    def _clean_normalizer_nodes(
            results_dict: dict[str, Optional[dict[str, Any]]]
    ) -> None:
        """Remove internal fields and sort nodes."""
        for normalizer_info in results_dict.values():
            if normalizer_info is None:
                continue
            for eq_node in normalizer_info["nodes"]:
                eq_node.pop("cluster_id", None)
                eq_node.pop("cluster_preferred_name", None)
            normalizer_info["nodes"].sort(
                key=lambda node: node["identifier"].upper())

    def _apply_output_format(
            self,
            results_dict: dict[str, Optional[dict[str, Any]]],
            output_format: Optional[str]
    ) -> None:
        """Apply minimal/slim/full formatting to results."""
        if output_format == "minimal":
            for info in results_dict.values():
                if info is None:
                    continue
                to_delete = set(info.keys()).difference({"id"})
                for key in to_delete:
                    del info[key]
        elif output_format == "slim":
            pass
        else:
            for info in results_dict.values():
                if info:
                    info["knowledge_graph"] = (
                        self._get_cluster_graph(info))

    @staticmethod
    def _sanitize_nan_attributes(
            results_dict: dict[str, Optional[dict[str, Any]]]
    ) -> None:
        """Replace NaN attribute values with None."""
        for info in results_dict.values():
            if (info is None
                    or "knowledge_graph" not in info
                    or info["knowledge_graph"] is None):
                continue
            kg = info["knowledge_graph"]
            edges = kg.get("edges")
            if not isinstance(edges, dict):
                continue
            for edge_data in edges.values():
                attrs = edge_data.get('attributes')
                if not isinstance(attrs, list):
                    continue
                for attribute in attrs:
                    try:
                        if ('value' in attribute
                                and math.isnan(
                                    attribute['value'])):
                            attribute['value'] = None
                    except (TypeError, ValueError):
                        pass

    # ------------ EXTERNAL DEBUG METHODS ------------- #

    def print_cluster_table(
            self, curie_or_name: str,
            include_edges: bool = True) -> Optional[dict]:
        """Print a tabular view of a concept's cluster."""
        canonical_info = self.get_canonical_curies(
            curies=curie_or_name)
        if not canonical_info.get(curie_or_name):
            canonical_info = self.get_canonical_curies(
                names=curie_or_name)

        if not canonical_info.get(curie_or_name):
            print(f"Sorry, input concept {curie_or_name}"
                  " is not recognized.")
            return None

        cluster_id = (
            canonical_info[curie_or_name]["preferred_curie"])
        equivalent_nodes = self.get_equivalent_nodes(
            curies=cluster_id,
            include_unrecognized_entities=False)
        if (cluster_id not in equivalent_nodes
                or not equivalent_nodes[cluster_id]):
            print("No cluster exists with a cluster_id"
                  f" of {cluster_id}")
            return {}

        member_ids = equivalent_nodes[cluster_id]
        api_results = self._call_normalizer_api(member_ids)

        nodes_data = []
        for node_id in member_ids:
            api_val = api_results.get(node_id)
            if api_val is not None:
                result = api_val
                main_id = result.get("id", {})
                types = result.get("type", [])
                category = (
                    types[0].replace("biolink:", "")
                    if types else "NamedThing")
                name = main_id.get("label", node_id)
                nodes_data.append({
                    "id": node_id,
                    "category": category,
                    "name": name})

        if not nodes_data:
            print("No nodes found for cluster_id"
                  f" {cluster_id}")
            return None

        nodes_df = pd.DataFrame(nodes_data)
        if include_edges:
            print(f"\nCluster for {curie_or_name} has"
                  " 0 edges (edge information not"
                  " available from API):\n")
        print(f"\nCluster for {curie_or_name} has"
              f" {nodes_df.shape[0]} nodes:\n")
        print(f"{nodes_df.to_markdown(index=False)}\n")
        return None

    # ------------ INTERNAL HELPER METHODS ------------ #

    def _call_normalizer_api(
            self, curies: List[str]) -> dict:
        """Call Node Normalizer POST /get_normalized_nodes.

        Uses in-memory cache and batching (2500 CURIEs per
        request). The old SQLite was a local file, so lookups
        were essentially free. With network calls, caching is
        critical — get_normalizer_results calls this method
        multiple times for overlapping CURIE sets, and without
        caching that would mean redundant round-trips.
        """
        if not curies:
            return {}

        all_results: dict[str, dict | None] = {}
        uncached_curies: list[str] = []

        # Check cache first to avoid network calls for
        # CURIEs we already looked up in this session.
        for curie in curies:
            if curie in self._normalizer_cache:
                all_results[curie] = (
                    self._normalizer_cache[curie])
                self._cache_hits += 1
            else:
                uncached_curies.append(curie)
                self._cache_misses += 1

        if uncached_curies:
            batch_size = 2500
            for i in range(0, len(uncached_curies),
                           batch_size):
                batch = uncached_curies[i:i + batch_size]
                try:
                    response = self._session.post(
                        f"{self.api_base_url}"
                        "/get_normalized_nodes",
                        json={"curies": batch},
                        timeout=30)
                    response.raise_for_status()
                    batch_results = response.json()
                    for curie_key, value in (
                            batch_results.items()):
                        self._normalizer_cache[curie_key] = (
                            value)
                        all_results[curie_key] = value
                except requests.exceptions.RequestException as e:
                    for c in batch:
                        self._normalizer_cache[c] = None
                        all_results[c] = None
                    if len(curies) <= 10:
                        print("Warning: API call failed"
                              f" for batch: {e}")

        return all_results

    # ---- Name Resolver config ----
    _NR_BATCH_SIZE = 50       # names per /bulk-lookup request
    _NR_REQUEST_TIMEOUT = 120.0  # seconds per request
    _NR_MAX_RETRIES = 3       # attempts per batch
    _NR_RETRY_WAIT = 2.0      # seconds between retries
    _NR_MAX_CONCURRENT = 5    # max parallel batches (async)

    def _build_nr_payload(self, batch: list[str]) -> dict:
        """Build /bulk-lookup payload with all required fields.

        All optional fields must be included explicitly —
        the server times out when they are omitted.
        """
        return {
            "strings": batch,
            "autocomplete": self._autocomplete,
            "highlighting": False,
            "offset": 0,
            "limit": 1,
            "biolink_types": [],
            "only_prefixes": "",
            "exclude_prefixes": "",
            "only_taxa": "",
        }

    @staticmethod
    def _extract_curies(
        batch: list[str], data: dict,
    ) -> dict[str, str | None]:
        """Extract the top CURIE for each name from the API response."""
        results: dict[str, str | None] = {}
        for name in batch:
            candidates = data.get(name, [])
            results[name] = (
                candidates[0]["curie"]
                if candidates else None)
        return results

    def _call_name_resolver_api(
            self, names: List[str]) -> dict:
        """Resolve names to CURIEs via Name Resolver /bulk-lookup.

        Auto-batches the input list. Dispatches to sync or
        async based on self._use_async.
        """
        if not names:
            return {}
        if self._use_async:
            return self._call_name_resolver_api_async(names)
        return self._call_name_resolver_api_sync(names)

    def _call_name_resolver_api_sync(
            self, names: List[str]) -> dict:
        """Sequential batches via requests.Session."""
        results: dict[str, str | None] = {}
        batch_size = self._NR_BATCH_SIZE
        total = len(names)
        num_batches = (total + batch_size - 1) // batch_size
        failed_batches = 0
        last_error: Optional[str] = None

        logger.info(
            "Name Resolver SYNC: %d names, %d batches "
            "(batch_size=%d)", total, num_batches, batch_size)

        for i in range(0, total, batch_size):
            batch_num = i // batch_size + 1
            batch = names[i:i + batch_size]

            batch_succeeded = False
            for attempt in range(1, self._NR_MAX_RETRIES + 1):
                batch_start = time.time()
                try:
                    response = self._session.post(
                        f"{self.name_resolver_url}"
                        "/bulk-lookup",
                        json=self._build_nr_payload(batch),
                        timeout=self._NR_REQUEST_TIMEOUT,
                    )
                    elapsed = time.time() - batch_start
                    response.raise_for_status()
                    data = response.json()
                    batch_curies = self._extract_curies(
                        batch, data)
                    results.update(batch_curies)
                    resolved = sum(
                        1 for v in batch_curies.values() if v)
                    nulls = sum(
                        1 for v in batch_curies.values()
                        if not v)
                    logger.info(
                        "batch %d/%d: resolved %d/%d  "
                        "%.2fs  HTTP %d",
                        batch_num, num_batches,
                        resolved, len(batch),
                        elapsed, response.status_code)
                    batch_succeeded = True
                    break
                except requests.exceptions.RequestException as e:
                    elapsed = time.time() - batch_start
                    last_error = str(e)
                    logger.warning(
                        "batch %d/%d  %.2fs  attempt %d/%d "
                        "failed: %s",
                        batch_num, num_batches, elapsed,
                        attempt, self._NR_MAX_RETRIES,
                        str(e)[:120])
                    if attempt < self._NR_MAX_RETRIES:
                        time.sleep(self._NR_RETRY_WAIT)
                        try:
                            self._session.close()
                        except Exception:  # pylint: disable=broad-except
                            pass
                        self._session = requests.Session()
                        self._session.headers.update(
                            {'accept': 'application/json'})

            if not batch_succeeded:
                for name in batch:
                    results[name] = None
                failed_batches += 1
                logger.error(
                    "batch %d/%d giving up after %d attempts, "
                    "%d names set to None",
                    batch_num, num_batches,
                    self._NR_MAX_RETRIES, len(batch))

        if failed_batches > 0:
            failed_names = failed_batches * batch_size
            logger.warning(
                "Name Resolver SYNC finished with %d failed "
                "batches (~%d names set to None). "
                "Last error: %s",
                failed_batches, failed_names, last_error)
        else:
            logger.info(
                "Name Resolver SYNC done: %d names, "
                "%d batches, 0 failures",
                total, num_batches)

        return results

    def _call_name_resolver_api_async(
            self, names: List[str]) -> dict:
        """Async implementation: concurrent batches via aiohttp.

        Concurrent batches via aiohttp with semaphore.
        Uses asyncio.run() so callers don't need to be async.
        """
        batch_size = self._NR_BATCH_SIZE
        total = len(names)
        batches = [
            names[i:i + batch_size]
            for i in range(0, total, batch_size)
        ]
        num_batches = len(batches)

        logger.info(
            "Name Resolver ASYNC: %d names, %d batches "
            "(batch_size=%d, max_concurrent=%d)",
            total, num_batches, batch_size,
            self._NR_MAX_CONCURRENT)

        async def _run() -> dict[str, str | None]:
            sem = asyncio.Semaphore(self._NR_MAX_CONCURRENT)
            results: dict[str, str | None] = {}
            failed_batches = 0
            completed_batches = 0
            total_resolved = 0
            total_null = 0
            last_error: Optional[str] = None

            async with aiohttp.ClientSession(
                headers={'accept': 'application/json'}
            ) as session:
                async def fetch_batch(
                    batch_num: int,
                    batch: list[str],
                ) -> dict[str, str | None]:
                    nonlocal failed_batches, last_error
                    nonlocal completed_batches
                    nonlocal total_resolved, total_null
                    async with sem:
                        for attempt in range(
                                1, self._NR_MAX_RETRIES + 1):
                            batch_start = time.time()
                            try:
                                async with session.post(
                                    f"{self.name_resolver_url}"
                                    "/bulk-lookup",
                                    json=self._build_nr_payload(
                                        batch),
                                    timeout=aiohttp.ClientTimeout(
                                        total=self._NR_REQUEST_TIMEOUT),
                                ) as resp:
                                    elapsed = (
                                        time.time() - batch_start)
                                    resp.raise_for_status()
                                    data = await resp.json()
                                    batch_curies = (
                                        self._extract_curies(
                                            batch, data))
                                    resolved = sum(
                                        1 for v in
                                        batch_curies.values()
                                        if v)
                                    nulls = sum(
                                        1 for v in
                                        batch_curies.values()
                                        if not v)
                                    completed_batches += 1
                                    total_resolved += resolved
                                    total_null += nulls
                                    logger.info(
                                        "batch %d/%d: "
                                        "resolved %d/%d  "
                                        "%.2fs  HTTP %d",
                                        batch_num,
                                        num_batches,
                                        resolved,
                                        len(batch),
                                        elapsed,
                                        resp.status)
                                    return batch_curies
                            except Exception as e:
                                elapsed = (
                                    time.time() - batch_start)
                                last_error = str(e)
                                logger.warning(
                                    "batch %d/%d  %.2fs  "
                                    "attempt %d/%d failed: %s",
                                    batch_num, num_batches,
                                    elapsed, attempt,
                                    self._NR_MAX_RETRIES,
                                    str(e)[:120])
                                if attempt < self._NR_MAX_RETRIES:
                                    await asyncio.sleep(
                                        self._NR_RETRY_WAIT)
                                    continue
                        # All retries exhausted
                        failed_batches += 1
                        logger.error(
                            "batch %d/%d giving up after "
                            "%d attempts, %d names set "
                            "to None",
                            batch_num, num_batches,
                            self._NR_MAX_RETRIES,
                            len(batch))
                        return {name: None for name in batch}

                tasks = [
                    fetch_batch(i + 1, b)
                    for i, b in enumerate(batches)
                ]
                batch_results = await asyncio.gather(*tasks)

            for batch_result in batch_results:
                results.update(batch_result)

            if failed_batches > 0:
                failed_names = failed_batches * batch_size
                logger.warning(
                    "Name Resolver ASYNC finished with "
                    "%d failed batches (~%d names set to "
                    "None). Last error: %s",
                    failed_batches, failed_names, last_error)
            else:
                logger.info(
                    "Name Resolver ASYNC done: %d names, "
                    "%d batches, 0 failures",
                    total, num_batches)

            return results

        return asyncio.run(_run())

    def get_cache_stats(self) -> dict:
        """Return cache performance statistics for debugging."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total * 100)
            if total > 0 else 0)
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_pct": round(hit_rate, 1),
            "cached_curies": len(self._normalizer_cache)
        }

    @staticmethod
    def _convert_to_set_format(some_value: Any) -> set:
        """Convert input to a set, filtering out None values.

        None filtering is important because the Name Resolver
        API returns a 422 for the entire batch if any element
        is null. The old SQLite code handled None gracefully,
        but the API does not.
        """
        if isinstance(some_value, set):
            return some_value
        if isinstance(some_value, list):
            return {v for v in some_value if v is not None}
        if isinstance(some_value, str):
            return {some_value}
        if some_value is None:
            return set()
        try:
            return set(some_value)
        except TypeError as error:
            raise ValueError(
                "Input is not an allowable data type"
                " (list, set, or string)!") from error

    @staticmethod
    def _dedupe_preserve_order(
            values: List[str]) -> List[str]:
        """Keep first-seen order (stable across runs)."""
        seen: set[str] = set()
        ordered_values: List[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                ordered_values.append(value)
        return ordered_values

    @staticmethod
    def _names_match(
            input_name: str,
            canonical_name: str) -> bool:
        """Content-aware name comparison for name-based resolution.

        Accepts minor punctuation/possessive differences
        (e.g. "Parkinson's disease" vs "Parkinson disease")
        but rejects unrelated strings
        (e.g. "Big Bird" vs "BIG").

        Why this exists: the old SQLite synonymizer resolved
        names via exact lookup on a `name_simplified` column.
        With the API-based approach, we ask the Name Resolver
        for a best-match CURIE and then verify the match is
        reasonable. Without this check, the Name Resolver
        can return unrelated hits (e.g. "Big Bird" resolves
        to NCBIGene:820398 — an Arabidopsis gene named "BIG").
        """
        # Step 1: strip all non-alphanumeric and compare.
        # Catches case/punctuation differences like
        # "ATRIAL FIBRILLATION" vs "atrial fibrillation".
        norm_input = ''.join(
            c for c in input_name.lower() if c.isalnum())
        norm_canonical = ''.join(
            c for c in canonical_name.lower() if c.isalnum())
        if not norm_input or not norm_canonical:
            return False
        if norm_input == norm_canonical:
            return True

        # Step 2: substring check with length ratio guard.
        # Handles suffix/prefix differences like
        # "acetaminophens" vs "acetaminophen".
        # The 0.6 ratio prevents short names from matching
        # unrelated longer names (e.g. "big" in "bigbird"
        # has ratio 3/7 = 0.43, which is below 0.6).
        shorter, longer = sorted(
            [norm_input, norm_canonical], key=len)
        if (shorter in longer
                and len(shorter) / len(longer) >= 0.6):
            return True

        # Step 3: token-level comparison with prefix matching.
        # Handles possessive differences like "Parkinson's"
        # vs "Parkinson" (after stripping punctuation:
        # "parkinsons" starts with "parkinson").
        # The > 0.5 threshold (strictly greater) means a
        # single-token match out of 2 tokens is not enough.
        # This is what rejects "Big Bird" vs "BIG": only
        # 1 of 2 tokens overlap (ratio 0.5, not > 0.5).
        norm_tok_in = {
            ''.join(c for c in t.lower() if c.isalnum())
            for t in input_name.split()} - {''}
        norm_tok_can = {
            ''.join(c for c in t.lower() if c.isalnum())
            for t in canonical_name.split()} - {''}
        if not norm_tok_in or not norm_tok_can:
            return False
        overlap = 0
        for ti in norm_tok_in:
            for tc in norm_tok_can:
                if (ti == tc
                        or ti.startswith(tc)
                        or tc.startswith(ti)):
                    overlap += 1
                    break
        max_tokens = max(len(norm_tok_in), len(norm_tok_can))
        return overlap / max_tokens > 0.5

    @staticmethod
    def _add_biolink_prefix(
            category: Optional[str]) -> Optional[str]:
        """Prefix a category string with 'biolink:' if non-empty."""
        if category:
            return f"biolink:{category}"
        return category

    def _get_api_urls(self) -> tuple[str, str]:
        """Determine Node Normalizer and Name Resolver URLs."""
        nn_url = self.rtx_config.config_dbs.get(
            "node_normalizer_url_override")
        nr_url = self.rtx_config.config_dbs.get(
            "name_resolver_url_override")
        if nn_url and nr_url:
            return nn_url.rstrip("/"), nr_url.rstrip("/")
        if nn_url or nr_url:
            raise ValueError(
                "Both node_normalizer_url_override and"
                " name_resolver_url_override must be set"
                " together in config_dbs.json")
        if self.rtx_config.maturity == "production":
            return (
                "https://nodenorm.transltr.io/1.5",
                "https://name-lookup.transltr.io")
        return (
            "https://nodenorm.ci.transltr.io/1.5",
            "https://name-lookup.ci.transltr.io")

    def _get_cluster_graph(
            self, normalizer_info: dict) -> dict:
        """Build a TRAPI KnowledgeGraph for a cluster."""
        kg = KnowledgeGraph()
        cluster_id = normalizer_info["id"]["identifier"]

        trapi_nodes = {
            node["identifier"]:
                self._convert_to_trapi_node(node)
            for node in normalizer_info["nodes"]}
        if cluster_id in trapi_nodes:
            trapi_nodes[cluster_id].attributes.append(
                Attribute(
                    attribute_type_id="biolink:description",
                    value_type_id="metatype:String",
                    value=(
                        "This node is the preferred/canonical"
                        " identifier for this concept"
                        " cluster."),
                    attribute_source="infores:arax"))
        kg.nodes = trapi_nodes
        kg.edges = {}

        return kg.to_dict()

    def _convert_to_trapi_node(
            self, normalizer_node: dict) -> Node:
        """Convert a normalizer node dict to a TRAPI Node."""
        node = Node(
            name=normalizer_node["label"],
            categories=[normalizer_node["category"]],
            attributes=[])

        provided_bys = []
        if normalizer_node["in_sri"]:
            provided_bys.append(self.sri_nn_infores_curie)
        if normalizer_node["in_kg2pre"]:
            provided_bys.append(self.kg2_infores_curie)
        node.attributes.append(Attribute(
            attribute_type_id="biolink:provided_by",
            value=provided_bys,
            value_type_id="biolink:Uriorcurie",
            attribute_source=self.arax_infores_curie,
            description=(
                "The sources the ARAX NodeSynonymizer"
                " extracted this node from")))

        if normalizer_node["in_sri"]:
            node.attributes.append(Attribute(
                attribute_type_id="biolink:name",
                value=normalizer_node["name_sri"],
                value_type_id="metatype:String",
                attribute_source=self.sri_nn_infores_curie,
                description=(
                    "Name for this identifier in the SRI"
                    " NodeNormalizer bulk download")))
            node.attributes.append(Attribute(
                attribute_type_id="biolink:category",
                value=normalizer_node["category_sri"],
                value_type_id="metatype:Uriorcurie",
                attribute_source=self.sri_nn_infores_curie,
                description=(
                    "Category for this identifier in the"
                    " SRI NodeNormalizer bulk download")))

        if normalizer_node["in_kg2pre"]:
            node.attributes.append(Attribute(
                attribute_type_id="biolink:name",
                value=normalizer_node["name_kg2pre"],
                value_type_id="metatype:String",
                attribute_source=self.kg2_infores_curie,
                description=(
                    "Name for this identifier in"
                    " RTX-KG2pre")))
            node.attributes.append(Attribute(
                attribute_type_id="biolink:category",
                value=normalizer_node["category_kg2pre"],
                value_type_id="metatype:Uriorcurie",
                attribute_source=self.kg2_infores_curie,
                description=(
                    "Category for this identifier in"
                    " RTX-KG2pre")))

        return node

    def _create_preferred_node_dict(
            self,
            preferred_id: Optional[str],
            preferred_category: Optional[str],
            preferred_name: Optional[str]) -> dict:
        """Build the standard preferred-node return dict."""
        return {
            "preferred_curie": preferred_id,
            "preferred_name": preferred_name,
            "preferred_category": (
                self._add_biolink_prefix(preferred_category)
                if preferred_category else None)
        }


def main():
    """CLI entry point for NodeSynonymizer lookups."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("curie_or_name")
    arg_parser.add_argument(
        "-c", "--canonical",
        dest="canonical", action="store_true")
    arg_parser.add_argument(
        "-e", "--equivalent",
        dest="equivalent", action="store_true")
    arg_parser.add_argument(
        "-n", "--normalizer",
        dest="normalizer", action="store_true")
    arg_parser.add_argument(
        "-l", "--names",
        dest="names", action="store_true")
    arg_parser.add_argument(
        "-p", "--preferrednames",
        dest="preferred_names", action="store_true")
    arg_parser.add_argument(
        "-t", "--table",
        dest="table", action="store_true")
    arg_parser.add_argument(
        "-g", "--graph",
        dest="graph", action="store_true")
    arg_parser.add_argument(
        "-k", "--kategory",
        dest="kategory", action="store_true")
    args = arg_parser.parse_args()

    synonymizer = NodeSynonymizer()
    curie_or_name = args.curie_or_name
    if args.canonical:
        results = synonymizer.get_canonical_curies(
            curies=curie_or_name, debug=True)
        if not results[curie_or_name]:
            results = synonymizer.get_canonical_curies(
                names=curie_or_name)
        print(json.dumps(results, indent=2))
    if args.equivalent:
        results = synonymizer.get_equivalent_nodes(
            curies=curie_or_name, debug=True)
        if not results[curie_or_name]:
            results = synonymizer.get_equivalent_nodes(
                names=curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.normalizer:
        results = synonymizer.get_normalizer_results(
            entities=curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.names:
        results = synonymizer.get_curie_names(
            curies=curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.preferred_names:
        results = synonymizer.get_preferred_names(
            curies=curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    if args.kategory:
        results = synonymizer.get_curie_category(
            curies=curie_or_name, debug=True)
        print(json.dumps(results, indent=2))
    no_specific_flag = not (
        args.canonical or args.equivalent
        or args.normalizer or args.names
        or args.preferred_names or args.graph)
    if args.table or no_specific_flag:
        synonymizer.print_cluster_table(curie_or_name)

if __name__ == "__main__":
    main()
