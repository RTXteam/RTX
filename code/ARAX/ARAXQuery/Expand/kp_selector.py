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
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../BiolinkHelper")
from biolink_helper import BiolinkHelper
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph


class KPSelector:

    def __init__(self, log: ARAXResponse = ARAXResponse()):
        self.meta_map_path = f"{os.path.dirname(os.path.abspath(__file__))}/meta_map_v2.pickle"
        self.timeout_record_path = f"{os.path.dirname(os.path.abspath(__file__))}/kp_timeout_record.pickle"
        self.log = log
        self.all_kps = eu.get_all_kps()
        self.timeout_record = self._load_timeout_record()
        self.meta_map = self._load_meta_map()
        self.biolink_helper = BiolinkHelper()

    def get_kps_for_single_hop_qg(self, qg: QueryGraph) -> Optional[Set[str]]:
        """
        This function returns the names of the KPs that say they can answer the given one-hop query graph (based on
        the categories/predicates the QG uses).
        """
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        self.log.debug(f"Selecting KPs to use for qedge {qedge_key}")
        # confirm that the qg is one hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.", error_code="UnexpectedQG")
            return None
        # isolate possible subject predicate object from qg
        sub_categories = set(self.biolink_helper.get_descendants(qg.nodes[qedge.subject].categories))
        obj_categories = set(self.biolink_helper.get_descendants(qg.nodes[qedge.object].categories))
        predicates = set(self.biolink_helper.get_descendants(qedge.predicates))

        # use metamap to check kp for predicate triple
        accepting_kps = set()
        for kp in self.meta_map:
            if self._triple_is_in_meta_map(kp, sub_categories, predicates, obj_categories):
                accepting_kps.add(kp)
            else:
                self.log.update_query_plan(qedge_key, kp, "Skipped", "MetaKG indicates this qedge is unsupported")

        return accepting_kps

    def kp_accepts_single_hop_qg(self, qg: QueryGraph, kp: str) -> Optional[bool]:
        """
        This function determines whether a KP can answer a given one-hop query based on the categories/predicates
        used in the query graph.
        """
        self.log.debug(f"Verifying that {kp} can answer this kind of one-hop query")
        # Confirm that the qg is one-hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.",
                           error_code="UnexpectedQG")
            return None

        qedge = list(qg.edges.values())[0]
        sub_categories = set(self.biolink_helper.get_descendants(qg.nodes[qedge.subject].categories))
        obj_categories = set(self.biolink_helper.get_descendants(qg.nodes[qedge.object].categories))
        predicates = set(self.biolink_helper.get_descendants(qedge.predicates))
        kp_accepts = self._triple_is_in_meta_map(kp, sub_categories, predicates, obj_categories)

        return kp_accepts

    def get_desirable_equivalent_curies(self, curies: List[str], categories: Optional[List[str]], kp: str) -> List[str]:
        """
        For each input curie, this function returns an equivalent curie(s) that uses a prefix the KP supports.
        """
        self.log.debug(f"{kp}: Converting curies in the QG to kinds that {kp} can answer")
        if not self.meta_map.get(kp):
            self.log.warning(f"{kp}: Somehow missing meta info for {kp}. Cannot do curie prefix conversion; will send "
                             f"curies as they are.")
            return curies
        elif not self.meta_map[kp].get("prefixes"):
            self.log.warning(f"{kp}: No supported prefix info is available for {kp}. Will send curies as they are.")
            return curies
        else:
            supported_prefixes = self._get_supported_prefixes(eu.convert_to_list(categories), kp)
            self.log.debug(f"{kp}: Prefixes {kp} supports for categories {categories} (and descendants) are: "
                           f"{supported_prefixes}")
            converted_curies = set()
            unsupported_curies = set()
            synonyms_dict = eu.get_curie_synonyms_dict(curies)
            # Convert each input curie to a preferred, supported prefix
            for input_curie, equivalent_curies in synonyms_dict.items():
                input_curie_prefix = self._get_uppercase_prefix(input_curie)
                supported_equiv_curies_by_prefix = defaultdict(set)
                for curie in equivalent_curies:
                    prefix = self._get_uppercase_prefix(curie)
                    if prefix in supported_prefixes:
                        supported_equiv_curies_by_prefix[prefix].add(curie)
                if supported_equiv_curies_by_prefix:
                    # Grab equivalent curies with the same prefix as the input curie, if available
                    if input_curie_prefix in supported_equiv_curies_by_prefix:
                        curies_to_send = supported_equiv_curies_by_prefix[input_curie_prefix]
                    # Otherwise pick any supported curie prefix present
                    else:
                        curies_to_send = next(curie_set for curie_set in supported_equiv_curies_by_prefix.values())
                    converted_curies = converted_curies.union(curies_to_send)
                else:
                    unsupported_curies.add(input_curie)
            if unsupported_curies:
                self.log.warning(f"{kp}: Could not find curies with prefixes {kp} prefers for these curies: "
                                 f"{unsupported_curies}; will not send these to KP")
            return list(converted_curies)

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

    def _load_meta_map(self):
        # This function loads the meta map and updates it as needed
        meta_map_file = pathlib.Path(self.meta_map_path)
        one_day_ago = datetime.now() - timedelta(hours=24)
        if not meta_map_file.exists():
            self.log.debug(f"Creating local copy of meta map for all KPs")
            meta_map = self._refresh_meta_map()
        elif datetime.fromtimestamp(meta_map_file.stat().st_mtime) < one_day_ago:
            self.log.debug(f"Doing a refresh of local meta map for all KPs")
            meta_map = self._refresh_meta_map()
        else:
            self.log.debug(f"Loading meta map (already exists and isn't due for a refresh)")
            with open(self.meta_map_path, "rb") as map_file:
                meta_map = pickle.load(map_file)
            # Check for any missing KPs
            missing_kps = self.all_kps.difference(set(meta_map))
            if missing_kps:
                self.log.debug(f"Missing meta info for {missing_kps}")
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
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        non_functioning_kps = [kp for kp in kps_to_update if self.timeout_record.get(kp) and
                               self.timeout_record[kp] > ten_minutes_ago]
        if non_functioning_kps:
            self.log.debug(f"Not trying to grab meta info for {non_functioning_kps} because they timed out "
                           f"within the last 10 minutes")
        functioning_kps_to_update = set(kps_to_update).difference(set(non_functioning_kps))
        for kp in functioning_kps_to_update:
            kp_endpoint = eu.get_kp_endpoint_url(kp)
            if kp_endpoint:
                try:
                    self.log.debug(f"Getting meta info from {kp}")
                    with requests_cache.disabled():
                        kp_response = requests.get(f"{kp_endpoint}/meta_knowledge_graph", timeout=10)
                except requests.exceptions.Timeout:
                    self.log.warning(f"Timed out when trying to hit {kp}'s /meta_knowledge_graph endpoint "
                                     f"(waited 10 seconds)")
                    self.timeout_record[kp] = datetime.now()
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
            elif kp == "infores:arax-drug-treats-disease":
                meta_map[kp] = {"predicates": self._get_dtd_meta_map(),
                                "prefixes": dict()}
            elif kp == "infores:arax-normalized-google-distance":
                # This is just a placeholder; not really used for KP selection
                predicates = {"biolink:NamedThing": {"biolink:NamedThing": {"biolink:has_normalized_google_distance_with"}}}
                meta_map[kp] = {"predicates": predicates,
                                "prefixes": dict()}

        # Save our big combined metamap to a local json file
        with open(self.meta_map_path, "wb") as map_file:
            pickle.dump(meta_map, map_file)
        with open(self.timeout_record_path, "wb") as timeout_file:
            pickle.dump(self.timeout_record, timeout_file)

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
        drug_ish_dict = {"biolink:Drug": dtd_predicates,
                         "biolink:SmallMolecule": dtd_predicates}
        disease_ish_dict = {"biolink:Disease": dtd_predicates,
                            "biolink:PhenotypicFeature": dtd_predicates,
                            "biolink:DiseaseOrPhenotypicFeature": dtd_predicates}
        dtd_meta_map = {"biolink:Drug": disease_ish_dict,
                        "biolink:SmallMolecule": disease_ish_dict,
                        "biolink:Disease": drug_ish_dict,
                        "biolink:PhenotypicFeature": drug_ish_dict,
                        "biolink:DiseaseOrPhenotypicFeature": drug_ish_dict}
        return dtd_meta_map

    def _load_timeout_record(self) -> Dict[str, datetime]:
        self.log.debug(f"Loading record of KP timeouts")
        timeout_record_file = pathlib.Path(self.timeout_record_path)
        if not timeout_record_file.exists():
            return dict()
        else:
            with open(self.timeout_record_path, "rb") as timeout_file:
                return pickle.load(timeout_file)

    def make_qg_use_supported_prefixes(self, qg: QueryGraph, kp_name: str, log: ARAXResponse) -> Optional[QueryGraph]:
        for qnode_key, qnode in qg.nodes.items():
            if qnode.ids:
                if kp_name == "infores:rtx-kg2":
                    # Just convert them into canonical curies
                    qnode.ids = eu.get_canonical_curies_list(qnode.ids, log)
                else:
                    # Otherwise figure out which kind of curies KPs want
                    categories = eu.convert_to_list(qnode.categories)
                    supported_prefixes = self._get_supported_prefixes(categories, kp_name)
                    used_prefixes = {self._get_uppercase_prefix(curie) for curie in qnode.ids}
                    # Only convert curie(s) if any use an unsupported prefix
                    if used_prefixes.issubset(supported_prefixes):
                        self.log.debug(f"{kp_name}: All {qnode_key} curies use prefix(es) {kp_name} supports; no "
                                       f"conversion necessary")
                    else:
                        self.log.debug(f"{kp_name}: One or more {qnode_key} curies use a prefix {kp_name} doesn't "
                                       f"support; will convert these")
                        converted_curies = self.get_desirable_equivalent_curies(qnode.ids, qnode.categories, kp_name)
                        if converted_curies:
                            log.debug(f"{kp_name}: Converted {qnode_key}'s {len(qnode.ids)} curies to a list of "
                                      f"{len(converted_curies)} curies tailored for {kp_name}")
                            qnode.ids = converted_curies
                        else:
                            log.info(f"{kp_name} cannot answer the query because no equivalent curies were found "
                                     f"with prefixes it supports for qnode {qnode_key}. Original curies were: "
                                     f"{qnode.ids}")
                            return None
        return qg

    @staticmethod
    def _get_uppercase_prefix(curie: str) -> str:
        return curie.split(":")[0].upper()

    def _get_supported_prefixes(self, categories: List[str], kp: str) -> Set[str]:
        bh = BiolinkHelper()
        categories_with_descendants = bh.get_descendants(eu.convert_to_list(categories), include_mixins=False)
        supported_prefixes = {prefix.upper() for category in categories_with_descendants
                              for prefix in self.meta_map[kp]["prefixes"].get(category, set())}
        return supported_prefixes
