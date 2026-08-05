#!/bin/env python3
"""
Usage:  python biolink_helper.py [biolink version number, e.g. 3.0.3]
"""

import datetime
import json
import os
import pathlib
import sys
from typing import Optional

import yaml
from biolink_helper_pkg import BiolinkHelper


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


def get_biolink_helper(biolink_version: Optional[str] = None):
    timestamp = str(datetime.datetime.now().isoformat())
    eprint(f"{timestamp}: DEBUG: In BiolinkHelper init")

    biolink_version = biolink_version if biolink_version else get_current_arax_biolink_version()
    if biolink_version == "4.2.0":
        eprint(f"{timestamp}: DEBUG: Overriding Biolink version from 4.2.0 to 4.2.1 due to issues with "
               f"treats predicates in 4.2.0")
        biolink_version = "4.2.1"

    biolink_helper_dir = os.path.dirname(os.path.abspath(__file__))

    return BiolinkHelper(biolink_version, biolink_helper_dir)


def get_current_arax_biolink_version() -> str:
    """
    Returns the current Biolink version that the ARAX system is using, according to the OpenAPI YAML file.
    """
    code_dir = f"{os.path.dirname(os.path.abspath(__file__))}/../.."
    openapi_yaml_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
    openapi_json_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.json"

    # Read the cached JSON openAPI file if it's already been created by RTXConfiguration (faster than YAML)
    openapi_json_file = pathlib.Path(openapi_json_path)
    if openapi_json_file.exists():
        with open(openapi_json_file) as json_file:
            opanapi_data = json.load(json_file)
    else:
        with open(openapi_yaml_path) as api_file:
            opanapi_data = yaml.safe_load(api_file)
    return opanapi_data["info"]["x-translator"]["biolink-version"]



