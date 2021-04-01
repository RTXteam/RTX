#!/bin/env python3
from datetime import datetime, timedelta
import json
import os
import pathlib
import sys
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph


class Director:

    def __init__(self, log: ARAXResponse):
        self.meta_map_path = f"{os.path.dirname(os.path.abspath(__file__))}/meta_map.json"
        self.log = log
        # Check if it's time to update the local copy of the meta_map
        if self._need_to_regenerate_meta_map():
            self._regenerate_meta_map()
        # Load our map now that we know it's up to date
        with open(self.meta_map_path) as map_file:
            self.meta_map = json.load(map_file)

    def get_kps_for_single_hop_qg(self, qg: QueryGraph) -> List[str]:
        # TODO: Copy over Lindsey's work from ARAX_expander.py that does this (but have it look at self.meta_map)
        pass

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
        # TODO: Copy over Lindsey's work from ARAX_expander.py to generate one big dictionary of /predicates for all KPs
        self.meta_map = {"hello": "world"}  # TODO: Store it here

        # Save our big combined metamap to a local json file
        with open(self.meta_map_path, "w+") as map_file:
            json.dump(self.meta_map, map_file)

    def _get_non_api_kps_meta_info(self):
        # TODO: Hardcode info for our KPs that don't have APIs here... (then include when building meta map)
        pass
