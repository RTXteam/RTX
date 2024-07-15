"""
This script creates a canonicalized version of KG2 stored in various file formats, including TSVs ready for import
into Neo4j. Files are created in the directory this script is in. It relies on the options you specify in
kg2c_config.json.
Usage: python build_kg2c.py <kg2pre version> <subversion, e.g., v1.0> <biolink version>
                            [synonymizer filename override] [--downloadkg2pre] [--uploadartifacts] [--test]
"""
import argparse
import csv
import logging
import pathlib
import json
import os
import subprocess
import sys
import time

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from create_kg2c_files import create_kg2c_files
from record_kg2c_meta_info import record_meta_kg_info
import file_manager

KG2C_DIR = f"{os.path.dirname(os.path.abspath(__file__))}"
CODE_DIR = f"{KG2C_DIR}/.."

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(f"{KG2C_DIR}/buildkg2c.log"),
                              logging.StreamHandler()])


def main():
    start = time.time()
    # Grab any parameters passed to this script
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version',
                            help="The version of KG2pre to build KG2c from (e.g., 2.9.2).")
    arg_parser.add_argument('sub_version',
                            help="The KG2c sub version (e.g., v1.0); generally should be v1.0 unless you are doing a "
                                 "KG2c rebuild for a KG2pre version that already had a KG2c built from it - then it"
                                 " should be v1.1, or etc.")
    arg_parser.add_argument('biolink_version',
                            help="The Biolink version that the given KG2pre version uses (e.g., 4.0.1).")
    arg_parser.add_argument('synonymizer_override', nargs='?', default=None,
                            help="The file name of the synonymizer you want to force this KG2c build "
                                 "to use (e.g., node_synonymizer_v1.0_KG2.9.0.sqlite). The file you specify must be "
                                 "present in the RTX/code/ARAX/NodeSynonymizer subdir locally. By default, the build "
                                 "will determine the synonymizer file name based on the KG2pre version and sub version "
                                 "parameters, but you can override that with this optional parameter.")
    arg_parser.add_argument('-d', '--downloadkg2pre', dest='download_kg2pre', action='store_true',
                            help="Specifies that the KG2pre TSV files should be downloaded from S3. If this flag is not "
                                 "set, local KG2pre TSVs will be used.")
    arg_parser.add_argument('-u', '--uploadartifacts', dest='upload_artifacts', action='store_true',
                            help="Specifies that artifacts of the build should be uploaded to the ARAX databases server"
                                 " and to S3.")
    arg_parser.add_argument('-t', '--test', dest='test', action='store_true',
                            help="Specifies whether to do a test build. Test builds create a smaller version of the "
                                 "KG2pre TSVs and do a KG2c build off of those. They ensure that the test graph "
                                 "does not include any orphan edges. All output files are named with a "
                                 "'_TEST' suffix.")
    args = arg_parser.parse_args()
    logging.info(f"STARTING KG2c BUILD")

    # Validate download/upload/synonymizer settings and make them clear to the user
    logging.info(f"KG2pre version to use is: {args.kg2pre_version}")
    logging.info(f"KG2c sub version is: {args.sub_version}")
    logging.info(f"Biolink model version to use is: {args.biolink_version}")
    if args.download_kg2pre:
        logging.info(f"KG2pre TSV files from S3 WILL be DOWNLOADED.")
    else:
        logging.info(f"Local KG2pre TSV files will be used (will NOT download files from S3).")
    if args.upload_artifacts:
        logging.info(f"KG2c build artifacts WILL be UPLOADED to arax-databases.rtx.ai and to S3.")
    else:
        logging.info(f"KG2c build artifacts will NOT be uploaded anywhere.")
    if args.synonymizer_override:
        arax_synonymizer_dir = f"{CODE_DIR}/ARAX/NodeSynonymizer"
        synonymizer_override_file_path = pathlib.Path(f"{arax_synonymizer_dir}/{args.synonymizer_override}")
        if not synonymizer_override_file_path.exists():
            raise ValueError(f"The synonymizer file you specified ({args.synonymizer_override}) does not exist in "
                             f"{arax_synonymizer_dir}. You must either put a copy of it there or use a different "
                             f"synonymizer.")
        else:
            synonymizer_name = args.synonymizer_override
            logging.info(f"Will use the USER-SPECIFIED synonymizer: {synonymizer_name}")
    else:
        synonymizer_name = f"node_synonymizer_{args.sub_version}_KG{args.kg2pre_version}.sqlite"
        logging.info(f"Will use synonymizer {synonymizer_name}")

    # Download KG2pre TSVs as applicable
    if args.download_kg2pre:
        file_manager.download_kg2pre_tsvs(args.kg2pre_version)

    # Validate local KG2pre TSV files
    file_manager.check_kg2pre_tsvs_version(args.kg2pre_version)

    # Create KG2pre test TSV files as applicable
    if args.test:
        file_manager.create_kg2pre_tsv_test_files(args.kg2pre_version)

    # Actually build KG2c
    logging.info("Calling create_kg2c_files.py..")
    create_kg2c_files(args.kg2pre_version, args.sub_version, args.biolink_version, synonymizer_name, args.test)
    logging.info("Calling record_kg2c_meta_info.py..")
    record_meta_kg_info(args.biolink_version, args.test)

    # Upload artifacts to the relevant places
    file_manager.make_kg2c_tarball(args.test)
    if args.upload_artifacts:
        file_manager.upload_kg2c_files_to_arax_databases_server(args.kg2pre_version, args.sub_version, args.test)
        file_manager.upload_kg2c_files_to_s3(args.test)

    logging.info(f"DONE WITH KG2c {'TEST ' if args.test else ''}BUILD! Took {round(((time.time() - start) / 60) / 60, 1)} hours.")


if __name__ == "__main__":
    main()
