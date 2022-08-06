#!/bin/env python3
"""
This script creates a canonicalized version of KG2 stored in various file formats, including TSVs ready for import
into Neo4j. Files are created in the directory this script is in. It relies on the options you specify in
kg2c_config.json; in particular, the KG2c will be built off of the KG2 endpoint you specify in that config file.
Usage: python3 build_kg2c.py [--test]
"""
import argparse
import logging
import pathlib
import json
import os
import subprocess
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from create_kg2c_files import create_kg2c_files
from record_kg2c_meta_info import record_meta_kg_info
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # code directory
from RTXConfiguration import RTXConfiguration

KG2C_DIR = f"{os.path.dirname(os.path.abspath(__file__))}"
CODE_DIR = f"{KG2C_DIR}/.."


def _setup_config_dbs_file(kg2pre_neo4j_endpoint: str, synonymizer_name: str):
    """
    This function locally modifies config_dbs.json to point to the right KG2pre Neo4j and synonymizer.
    """
    logging.info("Creating a config_dbs.json file pointed to the right synonymizer and KG2pre Neo4j..")
    config_dbs_file_path = f"{CODE_DIR}/config_dbs.json"

    # Save a copy of any pre-existing config_dbs.json so we don't overwrite it
    original_config_dbs_file = pathlib.Path(config_dbs_file_path)
    if original_config_dbs_file.exists():
        subprocess.check_call(["mv", config_dbs_file_path, f"{config_dbs_file_path}_KG2CBUILDTEMP"])

    RTXConfiguration()  # Regenerates config_secrets.json with the latest version
    with open(config_dbs_file_path) as config_dbs_file:
        rtx_config_dbs_dict = json.load(config_dbs_file)
    # Point to the 'right' KG2 Neo4j (the one specified in the KG2c config) and synonymizer (we always use simple name)
    rtx_config_dbs_dict["neo4j"]["KG2pre"] = kg2pre_neo4j_endpoint
    rtx_config_dbs_dict["node_synonymizer"] = f"/something/{synonymizer_name}"  # Only need name, not full path

    # Save our new config_dbs.json file
    with open(config_dbs_file_path, "w+") as revised_config_dbs_file:
        json.dump(rtx_config_dbs_dict, revised_config_dbs_file)


def _upload_output_files_to_s3():
    logging.info("Uploading KG2c json and TSV files to S3..")
    tarball_path = f"{KG2C_DIR}/kg2c-tsv.tar.gz"
    json_lite_file_path = f"{KG2C_DIR}/kg2c_lite.json"
    subprocess.check_call(["tar", "-czvf", tarball_path, "nodes_c.tsv", "nodes_c_header.tsv", "edges_c.tsv", "edges_c_header.tsv"])
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2", tarball_path, "s3://rtx-kg2/"])
    subprocess.check_call(["gzip", "-f", json_lite_file_path])
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2", f"{json_lite_file_path}.gz", "s3://rtx-kg2/"])


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        handlers=[logging.FileHandler("build.log"),
                                  logging.StreamHandler()])
    start = time.time()
    # Grab any parameters passed to this script
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--test", dest="test", action='store_true', default=False)
    args = arg_parser.parse_args()
    logging.info(f"STARTING {'TEST ' if args.test else ''}KG2c BUILD")

    # Load the KG2c config file
    with open(f"{KG2C_DIR}/kg2c_config.json") as config_file:
        kg2c_config_info = json.load(config_file)
    kg2_version = kg2c_config_info["kg2pre_version"]
    kg2pre_endpoint = kg2c_config_info["kg2pre_neo4j_endpoint"]
    biolink_version = kg2c_config_info["biolink_version"]
    build_kg2c = kg2c_config_info["kg2c"]["build"]
    upload_to_s3 = kg2c_config_info["kg2c"]["upload_to_s3"]
    build_synonymizer = kg2c_config_info["synonymizer"]["build"]
    synonymizer_name = kg2c_config_info["synonymizer"]["name"]
    upload_to_arax_ncats_io = kg2c_config_info["upload_to_arax.ncats.io"]
    upload_directory = kg2c_config_info["upload_directory"]
    logging.info(f"KG2pre version to use is {kg2_version}")
    logging.info(f"KG2pre neo4j endpoint to use is {kg2pre_endpoint}")
    logging.info(f"Biolink model version to use is {biolink_version}")
    logging.info(f"Synonymizer to use is {synonymizer_name}")
    synonymizer_dir = f"{CODE_DIR}/ARAX/NodeSynonymizer"
    synonymizer_file = pathlib.Path(f"{synonymizer_dir}/{synonymizer_name}")
    # Make sure synonymizer settings are valid
    if build_synonymizer and not args.test:
        if not synonymizer_name:
            raise ValueError(f"You must specify the name to give the new synonymizer in kg2c_config.json.")
        elif synonymizer_file.exists():
            raise ValueError(f"kg2c_config.json specifies that a new synonymizer should be built, but the "
                             f"synonymizer name provided already exists in {synonymizer_dir}. You must enter a new "
                             f"synonymizer name.")
        if upload_to_arax_ncats_io and not upload_directory:
            raise ValueError(f"You must specify the path of the directory on arax.ncats.io to upload synonymizer "
                             f"artifacts to in kg2c_config.json.")
    else:
        if not synonymizer_name:
            raise ValueError(f"You must specify the name of the synonymizer to use in kg2c_config.json since you are "
                             f"not building a new synonymizer.")
        elif not synonymizer_file.exists():
            raise ValueError(f"The synonymizer specified in kg2c_config.json does not exist in {synonymizer_dir}. You "
                             f"must put a copy of it there or use a different synonymizer.")

    # Set up an RTX config_local.json file that points to the right KG2 and synonymizer
    _setup_config_dbs_file(kg2pre_endpoint, synonymizer_name)

    # Build a new node synonymizer, if we're supposed to
    if build_synonymizer and not args.test:
        logging.info("Building node synonymizer off of specified KG2..")
        subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/build-synonymizer.sh"])
        if upload_to_arax_ncats_io:
            logging.info(f"Uploading synonymizer artifacts to arax.ncats.io:{upload_directory}")
            subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/upload-synonymizer-artifacts.sh", upload_directory, synonymizer_name])
        logging.info("Done building synonymizer.")

    # Actually build KG2c
    if build_kg2c:
        logging.info("Calling create_kg2c_files.py..")
        create_kg2c_files(args.test)
        logging.info("Calling record_kg2c_meta_info.py..")
        record_meta_kg_info(args.test)
        if not args.test:
            if upload_to_s3:
                _upload_output_files_to_s3()
            if upload_to_arax_ncats_io:
                logging.info(f"Uploading KG2c artifacts to arax.ncats.io:{upload_directory}")
                subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/upload-kg2c-artifacts.sh", upload_directory])

        logging.info(f"DONE WITH {'TEST ' if args.test else ''}KG2c BUILD! Took {round(((time.time() - start) / 60) / 60, 1)} hours")

    # Undo the revisions we made to config_dbs.json
    config_dbs_file_path = f"{CODE_DIR}/config_dbs.json"
    temp_config_dbs_file_path = f"{config_dbs_file_path}_KG2CBUILDTEMP"
    temp_config_dbs_path = pathlib.Path(temp_config_dbs_file_path)
    if temp_config_dbs_path.exists():
        subprocess.check_call(["mv", temp_config_dbs_file_path, config_dbs_file_path])


if __name__ == "__main__":
    main()
