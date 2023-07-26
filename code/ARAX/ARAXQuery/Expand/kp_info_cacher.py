import json
import os
import pathlib
import pickle
import subprocess
import sys
import psutil
from datetime import datetime, timedelta
from typing import Set, Dict, Optional

import requests
import requests_cache
import time

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

pathlist = os.path.realpath(__file__).split(os.path.sep)
rtx_index = pathlist.index("RTX")

sys.path.append(os.path.sep.join([*pathlist[:(rtx_index + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.sep.join([*pathlist[:(rtx_index + 1)], 'code', 'ARAX', 'ARAXQuery']))
from ARAX_response import ARAXResponse
sys.path.append(os.path.sep.join([*pathlist[:(rtx_index + 1)], 'code', 'ARAX', 'ARAXQuery', 'Expand']))
from smartapi import SmartAPI


MAX_TOTAL_WAIT_FOR_CACHE_SEC = 60.0
WAIT_LOOP_SEC = 0.1

class KPInfoCacher:

    def __init__(self):
        self.rtx_config = RTXConfiguration()
        version_string = f"{self.rtx_config.trapi_major_version}--{self.rtx_config.maturity}"
        self.smart_api_cache_path = f"{os.path.dirname(os.path.abspath(__file__))}/cache_smart_api_{version_string}.pkl"
        self.meta_map_cache_path = f"{os.path.dirname(os.path.abspath(__file__))}/cache_meta_map_{version_string}.pkl"
        self.cache_refresh_pid_path = f"{os.path.dirname(os.path.abspath(__file__))}/cache_refresh.pid"
    def refresh_kp_info_caches(self):
        """
        This method is meant to be called periodically by a background task. It refreshes two caches of KP info:
        one containing Meta KG info and one containing SmartAPI registration info.
        """

        current_pid = os.getpid() # This is the PID of the process that is currently refreshing the caches
        eprint(f"The process with process ID {current_pid} has STARTED refreshing the KP info caches")
        with open(self.cache_refresh_pid_path, "w") as f:
            f.write(str(current_pid))   # Writing the PID of the process that is currently refreshing the caches to a file

        # Grab KP registrations from Smart API
        smart_api_helper = SmartAPI()
        smart_api_kp_registrations = smart_api_helper.get_all_trapi_kp_registrations(trapi_version=self.rtx_config.trapi_major_version,
                                                                                     req_maturity=self.rtx_config.maturity)
        if not smart_api_kp_registrations:
            print(f"Didn't get any KP registrations back from SmartAPI!")
        previous_smart_api_cache_exists = pathlib.Path(self.smart_api_cache_path).exists()
        if smart_api_kp_registrations or not previous_smart_api_cache_exists:
            # Transform the info into the format we want
            allowed_kp_urls = {kp_registration["infores_name"]: self._get_kp_url_from_smartapi_registration(kp_registration)
                               for kp_registration in smart_api_kp_registrations}
            # Add entries for our local KPs (that are not web services)
            allowed_kp_urls["infores:arax-drug-treats-disease"] = None
            allowed_kp_urls["infores:arax-normalized-google-distance"] = None

            smart_api_cache_contents = {"allowed_kp_urls": allowed_kp_urls,
                                        "kps_excluded_by_version": smart_api_helper.kps_excluded_by_version,
                                        "kps_excluded_by_maturity": smart_api_helper.kps_excluded_by_maturity}

            # Save the SmartAPI info to the proper cache file in a thread-safe way (utilizing a temp file)
            with open(f"{self.smart_api_cache_path}.tmp", "wb") as smart_api_cache_temp:
                pickle.dump(smart_api_cache_contents, smart_api_cache_temp)
            subprocess.check_call(["mv", f"{self.smart_api_cache_path}.tmp", self.smart_api_cache_path])
        else:
            eprint(f"Keeping pre-existing SmartAPI cache since we got no results back from SmartAPI")
            with open(self.smart_api_cache_path, "rb") as smart_api_file:
                smart_api_cache_contents = pickle.load(smart_api_file)

        # Grab KPs' meta map info based off of their /meta_knowledge_graph endpoints
        meta_map = self._build_meta_map(allowed_kps_dict=smart_api_cache_contents["allowed_kp_urls"])

        # Save the meta map to the proper cache file in a thread-safe way (utilizing a temp file)
        with open(f"{self.meta_map_cache_path}.tmp", "wb") as meta_map_cache_temp:
            pickle.dump(meta_map, meta_map_cache_temp)
        subprocess.check_call(["mv", f"{self.meta_map_cache_path}.tmp", self.meta_map_cache_path])

        eprint(f"The process with process ID {current_pid} has FINISHED refreshing the KP info caches") 
        os.remove(self.cache_refresh_pid_path)

    def _get_kp_url_from_smartapi_registration(self, kp_smart_api_registration: dict) -> Optional[str]:
        if kp_smart_api_registration.get("servers"):

            # Just use the first URL listed for this KP (for this maturity level and TRAPI version)
            raw_url = kp_smart_api_registration["servers"][0]["url"]

            # Handle the special case of RTX-KG2
            if kp_smart_api_registration["infores_name"] == "infores:rtx-kg2":
                # Choose which KG2 URL to use based on whether this is an ITRB instance and any potential overrides
                all_kg2_urls = {server["url"] for server in kp_smart_api_registration["servers"]}
                if self.rtx_config.rtx_kg2_url:
                    # This means there's an override in place; we'll use whatever URL was specified
                    raw_url = self.rtx_config.rtx_kg2_url
                elif self.rtx_config.is_itrb_instance:
                    itrb_kg2_urls = [url for url in all_kg2_urls if "transltr.io" in url]
                    if itrb_kg2_urls:
                        raw_url = itrb_kg2_urls[0]  # Should really only be one KG2 per TRAPI version / maturity level
                else:
                    non_itrb_kg2_urls = [url for url in all_kg2_urls if "transltr.io" not in url]
                    if non_itrb_kg2_urls:
                        raw_url = non_itrb_kg2_urls[0]

            # Remove any trailing slashes
            return raw_url.strip("/") if isinstance(raw_url, str) else raw_url
        else:
            return None

    def load_kp_info_caches(self, log: ARAXResponse):
        """
        This method is meant to be used anywhere the meta map or smart API
        caches need to be used (i.e., by KPSelector).  Other modules should
        NEVER try to load the caches directly! They should only load them via
        this method.  It ensures that caches are up to date and that they don't
        become corrupted while refreshing.
        """
        if not (os.path.exists(self.smart_api_cache_path) and
                os.path.exists(self.meta_map_cache_path)):
            # if either pickled cache file is missing, then check if they are
            # being generated (on the other hand, if both exist, just move on
            # since we will use the cache files); see RTX issue 2072
            if (os.path.exists(self.cache_refresh_pid_path)):
                # Check if the refresher PID file exists
                with open(self.cache_refresh_pid_path, "r") as f:
                    refresher_pid = int(f.read())
                    # Get the PID of the process that is currently refreshing
                    # the caches
                    caches_are_being_refreshed = True if \
                        (psutil.pid_exists(refresher_pid)) else False
                    # Check if the process is still running
                    iter_ctr = 0
                    while caches_are_being_refreshed:
                        # if the caches are being actively refreshed, wait for
                        # it to finish
                        time.sleep(0.1)
                        iter_ctr += 1
                        caches_are_being_refreshed = True if \
                            (psutil.pid_exists(refresher_pid)) else False
                        if WAIT_LOOP_SEC * iter_ctr > \
                           MAX_TOTAL_WAIT_FOR_CACHE_SEC:
                            raise Exception("Timed out waiting for SmartAPI " +
                                            "cache creation; perhaps " +
                                            "MAX_TOTAL_WAIT_FOR_CACHE_SEC " +
                                            "value was too small: " +
                                            f"{MAX_TOTAL_WAIT_FOR_CACHE_SEC}")

        # At this point the KP info caches must NOT be in the process of being
        # refreshed, so we create/update if needed.  In particular, this ensures
        # that the caches will be created/fresh even on dev machines, that don't
        # run the background refresh task.
        one_day_ago = datetime.now() - timedelta(hours=24)
        smart_api_info_cache_pathlib_path = pathlib.Path(self.smart_api_cache_path)
        meta_map_cache_pathlib_path = pathlib.Path(self.meta_map_cache_path)
        if not smart_api_info_cache_pathlib_path.exists() or not meta_map_cache_pathlib_path.exists():
            log.warning(f"Missing KP info cache(s). Creating now.")
            self.refresh_kp_info_caches()
        elif (datetime.fromtimestamp(smart_api_info_cache_pathlib_path.stat().st_mtime) < one_day_ago or
              datetime.fromtimestamp(meta_map_cache_pathlib_path.stat().st_mtime) < one_day_ago):
            log.info(f"KP info cache(s) have not been updated for 24+ hours. Refreshing stale cache(s).")
            self.refresh_kp_info_caches()

        # The caches MUST be up to date at this point, so we just load them
        log.debug(f"Loading cached Smart API info")
        with open(self.smart_api_cache_path, "rb") as smart_api_file:
            smart_api_info = pickle.load(smart_api_file)
        log.debug(f"Loading cached meta map")
        with open(self.meta_map_cache_path, "rb") as map_file:
            meta_map = pickle.load(map_file)

        return smart_api_info, meta_map

    # --------------------------------- METHODS FOR BUILDING META MAP ----------------------------------------------- #
    # --- Note: These methods can't go in KPSelector because it would create a circular dependency with this class -- #

    def _build_meta_map(self, allowed_kps_dict: Dict[str, str]):
        # Start with whatever pre-existing meta map we might already have (can use this info in case an API fails)
        meta_map_file = pathlib.Path(self.meta_map_cache_path)
        if meta_map_file.exists():
            with open(self.meta_map_cache_path, "rb") as existing_meta_map_file:
                meta_map = pickle.load(existing_meta_map_file)
        else:
            meta_map = dict()

        # Then (try to) get updated meta info from each KP
        for kp_infores_curie, kp_endpoint_url in allowed_kps_dict.items():
            if kp_endpoint_url:
                try:
                    eprint(f"  - Getting meta info from {kp_infores_curie}")
                    with requests_cache.disabled():
                        kp_response = requests.get(f"{kp_endpoint_url}/meta_knowledge_graph", timeout=10)
                except requests.exceptions.Timeout:
                    eprint(f"Timed out when trying to hit {kp_infores_curie}'s /meta_knowledge_graph endpoint "
                          f"(waited 10 seconds)")
                except Exception:
                    eprint(f"Ran into a problem getting {kp_infores_curie}'s meta info")
                else:
                    if kp_response.status_code == 200:
                        try:
                            kp_meta_kg = kp_response.json()
                        except:
                            eprint(f"Skipping {kp_infores_curie} because they returned invalid JSON")
                            kp_meta_kg = "Failed"

                        if type(kp_meta_kg) != dict:
                            eprint(f"Skipping {kp_infores_curie} because they returned an invalid meta knowledge graph")
                        else:
                            meta_map[kp_infores_curie] = {"predicates": self._convert_meta_kg_to_meta_map(kp_meta_kg),
                                                          "prefixes": {category: meta_node["id_prefixes"]
                                                                       for category, meta_node in kp_meta_kg["nodes"].items()}}
                    else:
                        eprint(f"Unable to access {kp_infores_curie}'s /meta_knowledge_graph endpoint "
                              f"(returned status of {kp_response.status_code} for URL {kp_endpoint_url})")
            elif kp_infores_curie == "infores:arax-drug-treats-disease":
                meta_map[kp_infores_curie] = {"predicates": self._get_dtd_meta_map(),
                                              "prefixes": dict()}
            elif kp_infores_curie == "infores:arax-normalized-google-distance":
                # This is just a placeholder; not really used for KP selection
                predicates = {"biolink:NamedThing": {"biolink:NamedThing": {"biolink:occurs_together_in_literature_with"}}}
                meta_map[kp_infores_curie] = {"predicates": predicates,
                                              "prefixes": dict()}

        # Make sure the map doesn't contain any 'stale' KPs (KPs that used to be in SmartAPI but no longer are)
        stale_kps = set(meta_map).difference(allowed_kps_dict)
        if stale_kps:  # For dev work, we don't want to edit the metamap when in KG2 mode
            for stale_kp in stale_kps:
                eprint(f"Detected a stale KP in meta map ({stale_kp}) - deleting it")
                del meta_map[stale_kp]

        return meta_map

    @staticmethod
    def _convert_meta_kg_to_meta_map(kp_meta_kg: dict) -> dict:
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
