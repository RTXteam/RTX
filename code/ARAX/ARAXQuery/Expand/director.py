#!/bin/env python3
from datetime import datetime, timedelta
import json
import os
import pathlib
import sys
import urllib.request
import expand_utilities as eu
from typing import Set, Dict, List
from collections import defaultdict
from itertools import product

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph


class Director:

    def __init__(self, log: ARAXResponse, all_kps: Set[str]):
        self.meta_map_path = f"{os.path.dirname(os.path.abspath(__file__))}/meta_map.json"
        self.log = log
        self.all_kps = all_kps
        # Check if it's time to update the local copy of the meta_map
        if self._need_to_regenerate_meta_map():
            self._regenerate_meta_map()
        # Load our map now that we know it's up to date
        with open(self.meta_map_path) as map_file:
            self.meta_map = json.load(map_file)

    def get_kps_for_single_hop_qg(self, qg: QueryGraph) -> Set[str]:
        # confirm that the qg is one hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.", error_code="UnexpectedQG")
            return
        # isolate possible subject predicate object from qg
        qedge = list(qg.edges.values())[0]
        sub_category_list = eu.convert_to_list(qg.nodes[qedge.subject].category)
        obj_category_list = eu.convert_to_list(qg.nodes[qedge.object].category)
        predicate_list = eu.convert_to_list(qedge.predicate)
        
        # use metamap to check kp for predicate triple
        accepting_kps = set()
        for kp, predicates_dict in self.meta_map.items():
            if self._triple_is_in_predicates_response(kp, predicates_dict, sub_category_list, predicate_list, obj_category_list):
                accepting_kps.add(kp)
            # Also check the reverse direction for KG2, since it actually ignores edge direction
            elif kp == "ARAX/KG2" and self._triple_is_in_predicates_response(kp, predicates_dict, obj_category_list, predicate_list, sub_category_list):
                accepting_kps.add(kp)

        kps_to_return = self._select_best_kps(accepting_kps, qg)
        return kps_to_return

    # returns True if at least one possible triple exists in the predicates endpoint response
    @staticmethod
    def _triple_is_in_predicates_response(kp: str, predicates_dict: dict, subject_list: list, predicate_list: list, object_list: list)  -> bool:
        # handle potential emptiness of sub, obj, predicate lists
        if not subject_list and eu.kp_supports_none_for_category(kp): # any subject
            subject_list = list(predicates_dict.keys())
        if not object_list and eu.kp_supports_none_for_category(kp): # any object
            object_set = set()
            _ = [object_set.add(obj) for obj_dict in predicates_dict.values() for obj in obj_dict.keys()]
            object_list = list(object_set)
        any_predicate = False if predicate_list or not eu.kp_supports_none_for_predicate(kp) else True

        # handle combinations of subject and objects using cross product
        qg_sub_obj_dict = defaultdict(lambda: set())
        for sub, obj in list(product(subject_list, object_list)):
            qg_sub_obj_dict[sub].add(obj)

        # check for subjects
        kp_allowed_subs = set(predicates_dict.keys())
        accepted_subs = kp_allowed_subs.intersection(set(qg_sub_obj_dict.keys()))

        # check for objects
        for sub in accepted_subs:
            kp_allowed_objs = set(predicates_dict[sub].keys())
            accepted_objs = kp_allowed_objs.intersection(qg_sub_obj_dict[sub])
            if len(accepted_objs) > 0:
                # check predicates
                for obj in accepted_objs:
                    if any_predicate or set(predicate_list).intersection(set(predicates_dict[sub][obj])):
                        return True
        return False

    @staticmethod
    def _select_best_kps(possible_kps: Set[str], qg: QueryGraph) -> Set[str]:
        # Apply some special rules to filter down the KPs we'll use for this QG
        chosen_kps = possible_kps
        # If a qnode has a lot of curies, only use KPs that support batch querying (no TRAPI standard yet)
        if any(qnode for qnode in qg.nodes.values() if len(eu.convert_to_list(qnode.id)) > 10):
            chosen_kps = chosen_kps.intersection(eu.get_kps_that_support_curie_lists())

        # Always hit up KG2 for now (until its /predicates is made more comprehensive. it fails fast anyway)
        chosen_kps.add("ARAX/KG2")

        # TODO: keep a record of which KPs have been timing out recently, and skip them?

        return chosen_kps

    def _need_to_regenerate_meta_map(self) -> bool:
        # Check if file doesn't exist or if it hasn't been modified in the last day
        meta_map_file = pathlib.Path(self.meta_map_path)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        if not meta_map_file.exists() or datetime.fromtimestamp(meta_map_file.stat().st_mtime) < twenty_four_hours_ago:
            self.log.debug(f"Local copy of meta map either doesn't exist or needs to be refreshed")
            return True
        else:
            return False

    def _regenerate_meta_map(self):
        # Create an up to date version of the meta map
        self.log.debug(f"Regenerating combined meta map for all KPs")

        # First load whatever pre-existing meta-map we might already have (could use this info in case an API fails)
        meta_map_file = pathlib.Path(self.meta_map_path)
        if meta_map_file.exists():
            with open(self.meta_map_path, "r") as existing_meta_map_file:
                meta_map = json.load(existing_meta_map_file)
        else:
            meta_map = dict()

        # Then (try to) get updated info from each KPs /predicates endpoint
        for kp in self.all_kps:
            # get predicates dictionary from KP
            kp_endpoint = eu.get_kp_endpoint_url(kp)
            if kp_endpoint is None:
                self.log.debug(f"No endpoint for {kp}. Skipping for now.")
                continue
            try:
                kp_predicates_response = urllib.request.urlopen(f"{kp_endpoint}/predicates", timeout=10)
            except Exception:
                self.log.warning(f"Timed out when trying to hit {kp}'s /predicates endpoint")
            else:
                if kp_predicates_response.status != 200:
                    self.log.warning(f"Unable to access {kp}'s predicates endpoint "
                                 f"(returned status of {kp_predicates_response.status})")
                    continue
                predicates_dict = json.loads(kp_predicates_response.read())
                meta_map[kp] = predicates_dict

        # Merge what we found with our hard-coded info for API-less KPs
        non_api_kps_meta_info = self._get_non_api_kps_meta_info(meta_map)
        meta_map.update(non_api_kps_meta_info)

        # Save our big combined metamap to a local json file
        with open(self.meta_map_path, "w+") as map_file:
            json.dump(meta_map, map_file)

    @staticmethod
    def _get_non_api_kps_meta_info(meta_map: Dict[str, Dict[str, Dict[str, List[str]]]]) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
        # This is where we can hardcode our 'local' (non-TRAPI) KPs' /predicates info
        dtd_predicates = ["biolink:treats", "biolink:treated_by"]
        dtd_predicates_dict = {"biolink:Drug": {"biolink:Disease": dtd_predicates,
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

        # NGD should have same subject/object combinations as KG2, but only a single predicate for now
        ngd_predicates = ["biolink:has_normalized_google_distance_with"]
        ngd_predicates_dict = dict()
        for subject_category, objects_dict in meta_map.get("ARAX/KG2").items():
            ngd_predicates_dict[subject_category] = {object_category: ngd_predicates for object_category in objects_dict}

        # CHP Expand can only answer a subset of what's in their /predicates endpoint, so we'll hardcode it here
        chp_predicates = ["biolink:pairs_with"]
        chp_predicates_dict = {"biolink:Gene": {"biolink:Drug": chp_predicates},
                               "biolink:Drug": {"biolink:Gene": chp_predicates}}

        # COHD Expand can only answer a subset of what's in their /predicates endpoint, so we'll hardcode it here
        cohd_predicates = ["biolink:correlated_with"]
        cohd_predicates_dict = {"biolink:ChemicalSubstance": {"biolink:ChemicalSubstance": cohd_predicates,
                                                              "biolink:DiseaseOrPhenotypicFeature": cohd_predicates,
                                                              "biolink:Drug": cohd_predicates},
                                "biolink:DiseaseOrPhenotypicFeature": {"biolink:ChemicalSubstance": cohd_predicates,
                                                                       "biolink:DiseaseOrPhenotypicFeature": cohd_predicates,
                                                                       "biolink:Drug": cohd_predicates},
                                "biolink:Drug": {"biolink:ChemicalSubstance": cohd_predicates,
                                                 "biolink:DiseaseOrPhenotypicFeature": cohd_predicates,
                                                 "biolink:Drug": cohd_predicates}}

        non_api_predicates_info = {
            "DTD": dtd_predicates_dict,
            "NGD": ngd_predicates_dict,
            "CHP": chp_predicates_dict,
            "COHD": cohd_predicates_dict
        }
        return non_api_predicates_info
