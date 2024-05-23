"""
This script creates a canonicalized version of KG2 stored in various file formats, including TSVs ready for import
into Neo4j. Files are created in the directory this script is in. It relies on the options you specify in
kg2c_config.json.
Usage: python build_kg2c.py TODO: update this
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
RTX_CONFIG = RTXConfiguration()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(f"{KG2C_DIR}/buildkg2c.log"),
                              logging.StreamHandler()])


def _setup_config_dbs_file(synonymizer_name: str):
    """
    This function locally modifies config_dbs.json to point to the right synonymizer.
    """
    logging.info("Creating a config_dbs.json file pointed to the right synonymizer..")
    config_dbs_file_path = f"{CODE_DIR}/config_dbs.json"

    # Save a copy of any pre-existing config_dbs.json so we don't overwrite it
    original_config_dbs_file = pathlib.Path(config_dbs_file_path)
    if original_config_dbs_file.exists():
        subprocess.check_call(["mv", config_dbs_file_path, f"{config_dbs_file_path}_KG2CBUILDTEMP"])
        subprocess.check_call(["cp", f"{config_dbs_file_path}_KG2CBUILDTEMP", config_dbs_file_path])

    RTXConfiguration()  # Regenerates config_secrets.json with the latest version
    with open(config_dbs_file_path) as config_dbs_file:
        rtx_config_dbs_dict = json.load(config_dbs_file)
    # Point to the 'right' synonymizer
    rtx_config_dbs_dict["database_downloads"]["node_synonymizer"] = f"/something/{synonymizer_name}"  # Only need name, not full path

    # Save our new config_dbs.json file
    with open(config_dbs_file_path, "w+") as revised_config_dbs_file:
        json.dump(rtx_config_dbs_dict, revised_config_dbs_file, indent=3)


def _create_kg2pre_tsv_test_files():
    logging.info(f"Creating test versions of the KG2pre TSVs...")
    # TODO: Improve this so don't have orphan edge problem..


def _upload_output_files_to_s3(is_test: bool):
    logging.info("Uploading KG2c json and TSV files to S3..")
    tarball_name = f"kg2c-tsv.tar.gz{'_TEST' if is_test else ''}"
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2", f"{KG2C_DIR}/{tarball_name}", f"s3://rtx-kg2/{tarball_name}"])

    unzipped_lite_json_name = f"kg2c_lite.json{'_TEST' if is_test else ''}"
    subprocess.check_call(["gzip", "-f", f"{KG2C_DIR}/{unzipped_lite_json_name}"])

    zipped_lite_json_name = f"{unzipped_lite_json_name}.gz"
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2",
                           f"{KG2C_DIR}/{zipped_lite_json_name}", f"s3://rtx-kg2/{zipped_lite_json_name}"])


def main():
    start = time.time()
    # Grab any parameters passed to this script
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version',
                            help="The version of KG2pre to build KG2c from (e.g., 2.9.2)")
    arg_parser.add_argument('sub_version',
                            help="The KG2c sub version (e.g., v1.0); generally should be v1.0 unless you are doing a "
                                 "KG2c rebuild for a KG2pre version that already had a KG2c built from it - then it"
                                 " should be v1.1, or etc.")
    arg_parser.add_argument('biolink_version',
                            help="The Biolink version that the given KG2pre version uses (e.g., 4.0.1")
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

    logging.info(f"KG2pre version to use is: {args.kg2pre_version}")
    logging.info(f"KG2c sub version is: {args.sub_version}")
    logging.info(f"Biolink model version to use is: {args.biolink_version}")
    # Make download/upload settings clear and check for local KG2pre TSVs as appropriate
    if args.download_kg2pre:
        logging.info(f"KG2pre TSV files from S3 WILL be DOWNLOADED.")
    else:
        logging.info(f"Local KG2pre TSV files will be used (will NOT download files from S3.")
        kg2pre_tsvs_path = f"{KG2C_DIR}/kg2pre_tsvs"
        if not pathlib.Path(kg2pre_tsvs_path).exists():
            raise ValueError(f"No local KG2pre TSVs seem to exist. You need to either put "
                             f"nodes.tsv, edges.tsv, nodes_header.tsv, and edges_header.tsv files at "
                             f"{kg2pre_tsvs_path} or use the '--downloadkg2pre' flag to download fresh copies.")
        required_kg2pre_tsv_files = ["nodes.tsv", "edges.tsv", "nodes_header.tsv", "edges_header.tsv"]
        for kg2pre_tsv_file_name in required_kg2pre_tsv_files:
            if not pathlib.Path(f"{kg2pre_tsvs_path}/{kg2pre_tsv_file_name}").exists():
                raise ValueError(f"Required KG2pre TSV file {kg2pre_tsv_file_name} does not exist in "
                                 f"{kg2pre_tsvs_path}. You need to either put it there or use the '--downloadkg2pre' "
                                 f"flag to download fresh KG2pre TSV files. "
                                 f"Required KG2pre TSV files are: {required_kg2pre_tsv_files}")
    if args.upload_artifacts:
        logging.info(f"KG2c build artifacts WILL be UPLOADED to arax-databases.rtx.ai and to S3.")
    else:
        logging.info(f"KG2c build artifacts will NOT be uploaded anywhere.")
    # Make sure synonymizer settings are valid
    if args.synonymizer_override:
        arax_synonymizer_dir = f"{CODE_DIR}/ARAX/NodeSynonymizer"
        synonymizer_override_file_path = pathlib.Path(f"{arax_synonymizer_dir}/{args.synonymizer_override}")
        if not synonymizer_override_file_path.exists():
            raise ValueError(f"The synonymizer file you specified () does not exist in {arax_synonymizer_dir}. "
                             f"You must put a copy of it there, use a different synonymizer, or opt to build a "
                             f"new synonymizer in kg2c_config.json.")
        else:
            synonymizer_name = args.synonymizer_override
            logging.info(f"Will use the USER-SPECIFIED synonymizer: {synonymizer_name}")
    else:
        synonymizer_name = f"node_synonymizer_{args.sub_version}_KG{args.kg2pre_version}.sqlite"
        logging.info(f"Will use synonymizer {synonymizer_name}")

    # Set up an RTX config_local.json file that points to the right KG2 and synonymizer
    _setup_config_dbs_file(synonymizer_name)

    # Download KG2pre TSVs as applicable
    if args.download_kg2pre_tsvs:
        logging.info(f"Downloading KG2pre TSVs from S3...")
        os.system(f"bash -x {KG2C_DIR}/download-kg2pre-tsvs.sh")

    # Create KG2pre test TSV files as applicable
    if args.test:
        _create_kg2pre_tsv_test_files()

    # Actually build KG2c
    logging.info("Calling create_kg2c_files.py..")
    create_kg2c_files(args.kg2pre_version, args.sub_version, args.biolink_version, args.test)
    logging.info("Calling record_kg2c_meta_info.py..")
    record_meta_kg_info(args.biolink_version, args.test)

    logging.info(f"Creating tarball of KG2c TSVs..")
    subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/make-kg2c-tarball.sh", "_TEST" if args.test else ""])

    # Upload artifacts to the relevant places
    if args.upload_artifacts:
        upload_directory = f"/home/rtxconfig/KG{args.kg2pre_version}"
        logging.info(f"Uploading KG2c artifacts to arax-databases.rtx.ai:{upload_directory}")
        subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/upload-kg2c-artifacts.sh", RTX_CONFIG.db_host,
                               args.sub_version, args.kg2pre_version, upload_directory, "_TEST" if args.test else ""])
        _upload_output_files_to_s3(args.test)

    logging.info(f"DONE WITH KG2c BUILD! Took {round(((time.time() - start) / 60) / 60, 1)} hours.")

    # Undo the revisions we made to config_dbs.json
    config_dbs_file_path = f"{CODE_DIR}/config_dbs.json"
    temp_config_dbs_file_path = f"{config_dbs_file_path}_KG2CBUILDTEMP"
    temp_config_dbs_path = pathlib.Path(temp_config_dbs_file_path)
    if temp_config_dbs_path.exists():
        subprocess.check_call(["mv", temp_config_dbs_file_path, config_dbs_file_path])


if __name__ == "__main__":
    main()
