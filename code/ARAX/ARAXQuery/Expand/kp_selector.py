#!/bin/env python3
import os
import pprint
import sys
from typing import Set, List, Optional
from collections import defaultdict
from itertools import product

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import expand_utilities as eu
from kp_info_cacher import KPInfoCacher
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../BiolinkHelper")
from biolink_helper import BiolinkHelper
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()


class KPSelector:

    def __init__(self, kg2_mode: bool = False, log: ARAXResponse = ARAXResponse()):
        self.log = log
        self.kg2_mode = kg2_mode
        self.kp_cacher = KPInfoCacher()
        self.meta_map, self.kp_urls, self.kps_excluded_by_version, self.kps_excluded_by_maturity = self._load_cached_kp_info()
        self.valid_kps = {"infores:rtx-kg2"} if self.kg2_mode else set(self.kp_urls.keys())
        self.bh = BiolinkHelper()

    def _load_cached_kp_info(self) -> tuple:
        if self.kg2_mode:
            # We don't need any KP meta info when in KG2 mode, because there are no KPs to choose from
            return None, None, None, None
        else:
            # Load cached KP info
            kp_cacher = KPInfoCacher()
            try:
                smart_api_info, meta_map = kp_cacher.load_kp_info_caches(self.log)
            except Exception as e:
                self.log.error(f"Failed to load KP info caches due to {e}", error_code="LoadKPCachesFailed")
                return None, None, None, None

            # Record None URLs for our local KPs
            allowed_kp_urls = smart_api_info["allowed_kp_urls"]

            return (meta_map, allowed_kp_urls, smart_api_info["kps_excluded_by_version"],
                    smart_api_info["kps_excluded_by_maturity"])

    def get_kps_for_single_hop_qg(self, qg: QueryGraph) -> Optional[Set[str]]:
        """
        This function returns the names of the KPs that say they can answer the given one-hop query graph (based on
        the categories/predicates the QG uses).
        """
        qedge_key = next(qedge_key for qedge_key in qg.edges)
        qedge = qg.edges[qedge_key]
        qedge_predicates = qedge.predicates if qedge.predicates else [self.bh.root_predicate]
        self.log.debug(f"Selecting KPs to use for qedge {qedge_key}")
        # confirm that the qg is one hop
        if len(qg.edges) > 1:
            self.log.error(f"Query graph can only have one edge, but instead has {len(qg.edges)}.",
                           error_code="UnexpectedQG")
            return None
        # isolate possible subject predicate object from qg
        sub_categories = set(self.bh.get_descendants(qg.nodes[qedge.subject].categories))
        obj_categories = set(self.bh.get_descendants(qg.nodes[qedge.object].categories))
        predicates = set(self.bh.get_descendants(qedge_predicates))

        # use metamap to check kp for predicate triple
        self.log.debug(f"selecting from {len(self.valid_kps)} kps")
        accepting_kps = set()
        for kp in self.meta_map:
            if self._triple_is_in_meta_map(kp,
                                           sub_categories,
                                           predicates,
                                           obj_categories):
                accepting_kps.add(kp)
            # account for symmetrical predicates by checking if kp accepts with swapped sub and obj categories
            elif self._triple_is_in_meta_map(kp,
                                             obj_categories,
                                             predicates,
                                             sub_categories):
                accepting_kps.add(kp)
            else:
                self.log.update_query_plan(qedge_key, kp, "Skipped", "MetaKG indicates this qedge is unsupported")
        kps_missing_meta_info = self.valid_kps.difference(set(self.meta_map))
        for missing_kp in kps_missing_meta_info:
            self.log.update_query_plan(qedge_key, missing_kp, "Skipped", "No MetaKG info available")

        version = RTXConfig.trapi_major_version
        for kp in set(filter(None, self.kps_excluded_by_version)):  # TODO: Look into why sometimes infores is None?
            self.log.update_query_plan(qedge_key, kp, "Skipped", f"KP does not have a TRAPI {version} endpoint")
            self.log.debug(f"Skipped {kp}: KP does not have a TRAPI {version} endpoint")
        maturity = RTXConfig.maturity
        for kp in set(filter(None, self.kps_excluded_by_maturity)):
            self.log.update_query_plan(qedge_key, kp, "Skipped", f"KP does not have a {maturity} TRAPI {version} endpoint")
            self.log.debug(f"Skipped {kp}: KP does not have a {maturity} TRAPI {version} endpoint")

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
        sub_categories = set(self.bh.get_descendants(qg.nodes[qedge.subject].categories))
        obj_categories = set(self.bh.get_descendants(qg.nodes[qedge.object].categories))
        qedge_predicates = qedge.predicates if qedge.predicates else [self.bh.root_predicate]
        predicates = set(self.bh.get_descendants(qedge_predicates))
        kp_accepts = self._triple_is_in_meta_map(kp, sub_categories, predicates, obj_categories)

        # account for symmetrical predicates by checking if kp accepts with swapped sub and obj categories
        kp_accepts = kp_accepts or self._triple_is_in_meta_map(kp,
                                                               obj_categories,
                                                               predicates,
                                                               sub_categories)

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
        categories_with_descendants = self.bh.get_descendants(eu.convert_to_list(categories), include_mixins=False)
        supported_prefixes = {prefix.upper() for category in categories_with_descendants
                              for prefix in self.meta_map[kp]["prefixes"].get(category, set())}
        return supported_prefixes

    def _triple_is_in_meta_map(self, kp: str,
                               subject_categories: Set[str],
                               predicates: Set[str],
                               object_categories: Set[str]) -> bool:
        """
        Returns True if at least one possible triple exists in the KP's meta map. NOT meant to handle empty predicates;
        you should sub in "biolink:related_to" for QEdges without predicates before calling this method.
        """
        kp_meta_map = self.meta_map.get(kp)
        if not kp_meta_map:
            if kp not in self.valid_kps:
                self.log.error(f"{kp} does not seem to be a valid KP for ARAX. Valid KPs are: {self.valid_kps}",
                               error_code="InvalidKP")
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
                        if predicates.intersection(predicates_map[sub][obj]):
                            return True
            return False


def main():
    kp_selector = KPSelector()
    print(f"Meta map is:")
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(kp_selector.meta_map)


if __name__ == "__main__":
    main()
