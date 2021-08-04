#!/bin/env python3
import pickle
from datetime import datetime, timedelta
import os
import pathlib
import sys
from typing import Set, Dict, List, Optional
from collections import defaultdict
from itertools import product

import requests
import requests_cache

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph


class KPSelector:

    def __init__(self, log: ARAXResponse):
        self.meta_map_path = f"{os.path.dirname(os.path.abspath(__file__))}/meta_map_v2.pickle"
        self.biolink_version = "2.1.0"
        self.descendants_map_path = f"{os.path.dirname(os.path.abspath(__file__))}/descendants_biolink{self.biolink_version}.pickle"
        self.log = log
        self.all_kps = eu.get_all_kps()
        self.meta_map = self._load_meta_map()
        self.descendants_map = self._load_descendants_map()

    def get_kps_for_single_hop_qg(self, qg: QueryGraph) -> Optional[Set[str]]:
        """
        This function returns the names of the KPs that say they can answer the given one-hop query graph (based on
        the categories/predicates the QG uses).
        """
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        self.log.debug(f"Selecting KPs to use for qedge {qedge_key}")
        starting_descendants = set(self.descendants_map)
        # confirm that the qg is one hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.", error_code="UnexpectedQG")
            return None
        # isolate possible subject predicate object from qg
        sub_categories = self._get_category_descendants(qg.nodes[qedge.subject].categories)
        obj_categories = self._get_category_descendants(qg.nodes[qedge.object].categories)
        predicates = self._get_predicate_descendants(qedge.predicates)
        
        # use metamap to check kp for predicate triple
        accepting_kps = set()
        for kp in self.meta_map:
            if self._triple_is_in_meta_map(kp, sub_categories, predicates, obj_categories):
                accepting_kps.add(kp)

        kps_to_return = self._select_best_kps(accepting_kps, qg)

        # Cache any new category/predicate descendants we learned
        ending_descendants = set(self.descendants_map)
        if ending_descendants != starting_descendants:
            with open(self.descendants_map_path, "wb") as descendants_file:
                pickle.dump(self.descendants_map, descendants_file)

        return kps_to_return

    def kp_accepts_single_hop_qg(self, qg: QueryGraph, kp: str) -> Optional[bool]:
        """
        This function determines whether a KP can answer a given one-hop query based on the categories/predicates
        used in the query graph.
        """
        self.log.debug(f"Verifying that {kp} can answer this kind of one-hop query")
        starting_descendants = set(self.descendants_map)
        # Confirm that the qg is one-hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.",
                           error_code="UnexpectedQG")
            return None

        qedge = list(qg.edges.values())[0]
        sub_categories = self._get_category_descendants(qg.nodes[qedge.subject].categories)
        obj_categories = self._get_category_descendants(qg.nodes[qedge.object].categories)
        predicates = self._get_predicate_descendants(qedge.predicates)
        kp_accepts = self._triple_is_in_meta_map(kp, sub_categories, predicates, obj_categories)

        # Cache any new category/predicate descendants we learned
        ending_descendants = set(self.descendants_map)
        if ending_descendants != starting_descendants:
            with open(self.descendants_map_path, "wb") as descendants_file:
                pickle.dump(self.descendants_map, descendants_file)

        return kp_accepts

    def convert_curies_to_supported_prefixes(self, curies: List[str], categories: List[str], kp: str) -> List[str]:
        """
        This function looks up what curie prefixes the KP says it knows about, and makes the query graph
        only use (synonymous) curies with those prefixes.
        """
        self.log.debug(f"Converting curies in the QG to kinds that {kp} can answer")
        if not self.meta_map.get(kp):
            self.log.warning(f"Somehow missing meta info for {kp}. Cannot do curie prefix conversion; will send "
                             f"curies as they are.")
            return curies
        elif not self.meta_map[kp].get("prefixes"):
            self.log.warning(f"No supported prefix info is available for {kp}. Will send curies as they are.")
            return curies
        else:
            supported_prefixes = {prefix.upper() for category in categories
                                  for prefix in self.meta_map[kp]["prefixes"].get(category, set())}
            self.log.debug(f"Prefixes {kp} supports for {categories} are: {supported_prefixes}")
            synonymous_curies = eu.get_curie_synonyms(curies)
            final_curies = [curie for curie in synonymous_curies if curie.split(":")[0].upper() in supported_prefixes]
            return final_curies

    # returns True if at least one possible triple exists in the KP's meta map
    def _triple_is_in_meta_map(self, kp: str, subject_categories: Set[str], predicates: Set[str], object_categories: Set[str]) -> bool:
        kp_meta_map = self.meta_map.get(kp)
        if not kp_meta_map:
            if kp not in self.all_kps:
                self.log.error(f"{kp} does not seem to be a valid KP for ARAX. Valid KPs are: {self.all_kps}", error_code="InvalidKP")
            else:
                self.log.warning(f"Somehow missing meta info for {kp}.")
            return False
        else:
            predicates_map = kp_meta_map["predicates"]
            # handle potential emptiness of sub, obj, predicate lists
            if not subject_categories:  # any subject
                subject_categories = set(predicates_map.keys())
            if not object_categories:  # any object
                object_set = set()
                _ = [object_set.add(obj) for obj_dict in predicates_map.values() for obj in obj_dict.keys()]
                object_categories = object_set
            any_predicate = False if predicates or kp == "NGD" else True

            # handle combinations of subject and objects using cross product
            qg_sub_obj_dict = defaultdict(lambda: set())
            for sub, obj in list(product(subject_categories, object_categories)):
                qg_sub_obj_dict[sub].add(obj)

            # check for subjects
            kp_allowed_subs = set(predicates_map.keys())
            accepted_subs = kp_allowed_subs.intersection(set(qg_sub_obj_dict.keys()))

            # check for objects
            for sub in accepted_subs:
                kp_allowed_objs = set(predicates_map[sub].keys())
                accepted_objs = kp_allowed_objs.intersection(qg_sub_obj_dict[sub])
                if len(accepted_objs) > 0:
                    # check predicates
                    for obj in accepted_objs:
                        if any_predicate or predicates.intersection(predicates_map[sub][obj]):
                            return True
            return False

    @staticmethod
    def _select_best_kps(possible_kps: Set[str], qg: QueryGraph) -> Set[str]:
        # Apply some special rules to filter down the KPs we'll use for this QG
        chosen_kps = possible_kps

        # Always hit up KG2 for now (it fails fast anyway)
        chosen_kps.add("RTX-KG2")
        # Use NGD only if specific predicate is used (regardless of categories)
        qedge = next(qedge for qedge in qg.edges.values())
        if qedge.predicates and "biolink:has_normalized_google_distance_with" in qedge.predicates:
            chosen_kps.add("NGD")

        # If a qnode has a lot of curies, only use KG2 for now (until figure out which KPs are reasonably fast for this)
        if any(qnode for qnode in qg.nodes.values() if len(eu.convert_to_list(qnode.ids)) > 20):
            chosen_kps = {"RTX-KG2"}

        # Don't use BTE if this is a curie-to-curie query (they have a bug with such queries currently)
        if all(qnode.ids for qnode in qg.nodes.values()):
            chosen_kps = chosen_kps.difference({"BTE"})

        # TODO: keep a record of which KPs have been timing out recently, and skip them?

        return chosen_kps

    def _load_meta_map(self):
        # This function loads the meta map and updates it as needed
        meta_map_file = pathlib.Path(self.meta_map_path)
        two_days_ago = datetime.now() - timedelta(hours=48)
        if not meta_map_file.exists():
            self.log.debug(f"Creating local copy of meta map for all KPs")
            meta_map = self._refresh_meta_map()
        elif datetime.fromtimestamp(meta_map_file.stat().st_mtime) < two_days_ago:
            self.log.debug(f"Doing a refresh of local meta map for all KPs")
            meta_map = self._refresh_meta_map()
        else:
            self.log.debug(f"Loading meta map (already exists and isn't due for a refresh)")
            with open(self.meta_map_path, "rb") as map_file:
                meta_map = pickle.load(map_file)
            # Check for any missing KPs
            missing_kps = self.all_kps.difference(set(meta_map))
            if missing_kps:
                self.log.debug(f"Missing meta info for {missing_kps}; will try to get this info")
                meta_map = self._refresh_meta_map(missing_kps, meta_map)

        # Make sure the map doesn't contain any 'stale' KPs
        stale_kps = set(meta_map).difference(self.all_kps)
        if stale_kps:
            for stale_kp in stale_kps:
                self.log.debug(f"Detected a stale KP in meta map ({stale_kp}) - deleting it")
                del meta_map[stale_kp]
            with open(self.meta_map_path, "wb") as map_file:
                pickle.dump(meta_map, map_file)  # Save these changes

        return meta_map

    def _refresh_meta_map(self, kps: Optional[Set[str]] = None, meta_map: Optional[Dict[str, dict]] = None):
        # Create an up to date version of the meta map
        kps_to_update = kps if kps else self.all_kps

        if not meta_map:
            # Load whatever pre-existing meta-map we might already have (could use this info in case an API fails)
            meta_map_file = pathlib.Path(self.meta_map_path)
            if meta_map_file.exists():
                with open(self.meta_map_path, "rb") as existing_meta_map_file:
                    meta_map = pickle.load(existing_meta_map_file)
            else:
                meta_map = dict()

        # Then (try to) get updated meta info from each KP
        for kp in kps_to_update:
            kp_endpoint = eu.get_kp_endpoint_url(kp)
            if kp_endpoint:
                try:
                    self.log.debug(f"Getting meta info from {kp}")
                    with requests_cache.disabled():
                        kp_response = requests.get(f"{kp_endpoint}/meta_knowledge_graph", timeout=10)
                except requests.exceptions.Timeout:
                    self.log.warning(f"Timed out when trying to hit {kp}'s /meta_knowledge_graph endpoint")
                except Exception:
                    self.log.warning(f"Ran into a problem getting {kp}'s meta info")
                else:
                    if kp_response.status_code == 200:
                        kp_meta_kg = kp_response.json()
                        meta_map[kp] = {"predicates": self._convert_to_meta_map(kp_meta_kg),
                                        "prefixes": {category: meta_node["id_prefixes"]
                                                     for category, meta_node in kp_meta_kg["nodes"].items()}}
                    else:
                        self.log.warning(f"Unable to access {kp}'s /meta_knowledge_graph endpoint (returned status of "
                                         f"{kp_response.status_code})")
            elif kp == "DTD":
                meta_map[kp] = {"predicates": self._get_dtd_meta_map(),
                                "prefixes": dict()}
            elif kp == "NGD":
                # This is just a placeholder; not really used for KP selection
                predicates = {"biolink:NamedThing": {"biolink:NamedThing": {"biolink:has_normalized_google_distance_with"}}}
                meta_map[kp] = {"predicates": predicates,
                                "prefixes": dict()}

        # Save our big combined metamap to a local json file
        with open(self.meta_map_path, "wb") as map_file:
            pickle.dump(meta_map, map_file)

        return meta_map

    @staticmethod
    def _convert_to_meta_map(kp_meta_kg: dict) -> dict:
        kp_meta_map = dict()
        for meta_edge in kp_meta_kg["edges"]:
            subject_category = meta_edge["subject"]
            object_category = meta_edge["object"]
            predicate = meta_edge["predicate"]
            if subject_category not in kp_meta_map:
                kp_meta_map[subject_category] = dict()
            if object_category not in kp_meta_map[subject_category]:
                kp_meta_map[subject_category][object_category] = set()
            kp_meta_map[subject_category][object_category].add(predicate)
        return kp_meta_map

    @staticmethod
    def _get_dtd_meta_map():
        dtd_predicates = {"biolink:treats", "biolink:treated_by"}
        dtd_meta_map = {"biolink:Drug": {"biolink:Disease": dtd_predicates,
                                         "biolink:PhenotypicFeature": dtd_predicates,
                                         "biolink:DiseaseOrPhenotypicFeature": dtd_predicates},
                        "biolink:ChemicalSubstance": {"biolink:Disease": dtd_predicates,
                                                      "biolink:PhenotypicFeature": dtd_predicates,
                                                      "biolink:DiseaseOrPhenotypicFeature": dtd_predicates},
                        "biolink:Disease": {"biolink:Drug": dtd_predicates,
                                            "biolink:ChemicalSubstance": dtd_predicates},
                        "biolink:PhenotypicFeature": {"biolink:Drug": dtd_predicates,
                                                      "biolink:ChemicalSubstance": dtd_predicates},
                        "biolink:DiseaseOrPhenotypicFeature": {"biolink:Drug": dtd_predicates,
                                                               "biolink:ChemicalSubstance": dtd_predicates}}
        return dtd_meta_map

    def _load_descendants_map(self) -> Dict[str, Set[str]]:
        self.log.debug(f"Loading category/predicate descendants map (Biolink model version {self.biolink_version})")
        descendants_map_file = pathlib.Path(self.descendants_map_path)
        if not descendants_map_file.exists():
            return dict()
        else:
            with open(self.descendants_map_path, "rb") as descendants_file:
                descendants_map = pickle.load(descendants_file)
            return descendants_map

    def _get_category_descendants(self, categories: Optional[List[str]]) -> Set[str]:
        if categories:
            all_descendants = set(categories)
            for category in categories:
                category_descendants = self._get_descendants(category)
                all_descendants.update(category_descendants)
            return all_descendants
        else:
            return set()

    def _get_predicate_descendants(self, predicates: Optional[List[str]]) -> Set[str]:
        if predicates:
            all_descendants = set(predicates)
            for predicate in predicates:
                predicate_descendants = self._get_descendants(predicate)
                all_descendants.update(predicate_descendants)
            return all_descendants
        else:
            return set()

    def _get_descendants(self, term: str) -> Set[str]:
        term_descendants = {term}
        if term in self.descendants_map:
            term_descendants.update(self.descendants_map[term])
        else:
            self.log.debug(f"Querying Biolink Model Lookup API for descendants of {term}")
            try:
                bl_url = f"https://bl-lookup-sri.renci.org/bl/{term}/descendants?version={self.biolink_version}"
                response = requests.get(bl_url, timeout=10)
            except requests.exceptions.Timeout:
                self.log.warning(f"Timed out when trying to get descendants from Biolink Model Lookup API")
            except Exception:
                self.log.warning(f"Ran into a problem using Biolink Model Lookup API")
            else:
                if response.status_code == 200:
                    term_descendants = set(response.json())
                    self.descendants_map[term] = term_descendants  # Save these for easy lookup later
                else:
                    self.log.warning(
                        f"Biolink Model Lookup API returned {response.status_code} response: {response.text}")
        return term_descendants
