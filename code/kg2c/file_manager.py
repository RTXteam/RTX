import csv
import logging
import os
import pathlib
import subprocess
import argparse
import sys
from typing import Optional

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # code directory
from RTXConfiguration import RTXConfiguration

KG2C_DIR = os.path.dirname(os.path.abspath(__file__))
KG2PRE_TSVS_DIR = f"{KG2C_DIR}/kg2pre_tsvs"


def download_kg2pre_tsvs(kg2pre_version: str):
    kg2pre_tarball_name = "kg2-tsv-for-neo4j.tar.gz"
    kg2pre_tsv_version_dir = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    if not pathlib.Path(kg2pre_tsv_version_dir).exists():
        os.system(f"mkdir -p {kg2pre_tsv_version_dir}")
    logging.info(f"Downloading {kg2pre_tarball_name} from the rtx-kg2 S3 bucket into {kg2pre_tsv_version_dir}")
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2",
                           f"s3://rtx-kg2/{kg2pre_tarball_name}", kg2pre_tsv_version_dir])
    logging.info(f"Unpacking {kg2pre_tarball_name}..")
    subprocess.check_call(["tar", "-xvzf", f"{kg2pre_tsv_version_dir}/{kg2pre_tarball_name}"])


def ensure_kg2pre_tsvs_exist(kg2pre_version: str):
    kg2pre_tsv_version_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    logging.info(f"Ensuring that KG2pre TSVs exist in {kg2pre_tsv_version_path}")
    if not pathlib.Path(kg2pre_tsv_version_path).exists():
        raise ValueError(f"The {kg2pre_version} KG2pre TSVs directory does not exist locally; "
                         f"it should be at {kg2pre_tsv_version_path}. You need to either put "
                         f"nodes.tsv, edges.tsv, nodes_header.tsv, and edges_header.tsv files into "
                         f"{kg2pre_tsv_version_path} or choose to download fresh copies of the KG2pre TSVs from S3.")
    required_kg2pre_tsv_files = ["nodes.tsv", "edges.tsv", "nodes_header.tsv", "edges_header.tsv"]
    for kg2pre_tsv_file_name in required_kg2pre_tsv_files:
        if not pathlib.Path(f"{kg2pre_tsv_version_path}/{kg2pre_tsv_file_name}").exists():
            raise ValueError(f"Required KG2pre TSV file {kg2pre_tsv_file_name} does not exist in "
                             f"{kg2pre_tsv_version_path}. You need to either put it there or opt to download fresh "
                             f"KG2pre TSV files. Required KG2pre TSV files are: {required_kg2pre_tsv_files}")
    logging.info(f"Confirmed KG2pre TSVs exist in {kg2pre_tsv_version_path}")


def check_kg2pre_tsvs_version(kg2pre_version: str, biolink_version: Optional[str] = None, is_test: Optional[bool] = None):
    # First ensure that the files actually exist
    ensure_kg2pre_tsvs_exist(kg2pre_version)

    # Load KG2pre nodes data, including only the columns relevant to us (to locate the build node)
    kg2pre_tsv_version_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    logging.info(f"Confirming that local KG2pre TSVs in {kg2pre_tsv_version_path} are for the "
                 f"requested KG2pre version ({kg2pre_version})..")
    logging.info(f"Loading nodes into dataframe to extract KG2pre build node..")
    nodes_tsv_path = f"{kg2pre_tsv_version_path}/nodes.tsv"
    nodes_tsv_header_path = f"{kg2pre_tsv_version_path}/nodes_header.tsv"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id", "name"]
    nodes_df = pd.read_table(nodes_tsv_path,
                             names=node_column_names,
                             usecols=columns_to_keep,
                             index_col="id",
                             dtype={
                                 "id": str,
                                 "name": str,
                                 "iri": str
                             })

    # Make sure this is actually the KG2pre version we are supposed to be using
    kg2pre_build_node_id = "RTX:KG2"
    if kg2pre_build_node_id in nodes_df.index:
        kg2pre_build_node = nodes_df.loc[kg2pre_build_node_id]
        # Note: For below line, using '.name' accessor returns node ID for some reason...
        kg2pre_build_node_name_chunks = kg2pre_build_node["name"].split("-")
        kg2pre_build_node_version = kg2pre_build_node_name_chunks[1].replace("KG", "")
        if kg2pre_build_node_version == kg2pre_version:
            logging.info(f"Confirmed local KG2pre TSVs version matches the requested version ({kg2pre_version})")
        else:
            raise ValueError(f"Wrong KG2pre TSVs! You requested KG2pre version {kg2pre_version},"
                             f" but the build node in the KG2pre TSVs at {kg2pre_tsv_version_path} says the version is "
                             f"{kg2pre_build_node_version}. You need to either put the true {kg2pre_version} TSVs in "
                             f"{kg2pre_tsv_version_path} or use a different KG2pre version.")
    else:
        if is_test:
            logging.warning(f"No RTX-KG2pre build node was found in the local KG2pre TSVs. "
                            f"This is ok since this is just a test.")
        else:
            raise ValueError(f"No build node exists in the KG2pre TSVs! Cannot verify we have the correct KG2pre TSVs.")

    # Verify the Biolink version requested matches that on the KG2pre Biolink node
    if biolink_version:
        biolink_build_node_id = "biolink_download_source:"
        if biolink_build_node_id in nodes_df.index:
            biolink_build_node = nodes_df.loc[biolink_build_node_id]
            biolink_build_node_version = biolink_build_node["iri"].split("/")[-4].replace("v", "")
            if biolink_build_node_version == biolink_version:
                logging.info(f"Confirmed that the version on the Biolink node in the local KG2pre TSVs matches "
                             f"the requested Biolink version ({biolink_version}).")
            else:
                raise ValueError(f"The Biolink node in the local KG2pre TSVs is {biolink_build_node_version}, "
                                 f"but you requested Biolink version {biolink_version}! "
                                 f"This needs to be reconciled to proceed.")
        else:
            if is_test:
                logging.warning(f"No Biolink build node was found in the local KG2pre TSVs. "
                                f"This is ok since this is just a test.")
            else:
                raise ValueError(f"No Biolink build node (i.e., node with id '{biolink_build_node_id}' was "
                                 f"found in the local KG2pre TSV files in {kg2pre_tsv_version_path}. This needs to "
                                 f"be fixed so that we can verify the correct Biolink version is being used.")


def create_kg2pre_tsv_test_files(kg2pre_version: str):
    logging.info(f"Creating test versions of the KG2pre TSVs...")
    kg2pre_tsv_version_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"

    # First grab all node IDs in our nodes file
    logging.info(f"Loading all nodes into a dataframe..")
    test_nodes_file_path = f"{kg2pre_tsv_version_path}/nodes.tsv_TEST"
    nodes_file_path = f"{kg2pre_tsv_version_path}/nodes.tsv"
    nodes_tsv_header_path = f"{kg2pre_tsv_version_path}/nodes_header.tsv"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id"]
    nodes_df = pd.read_table(nodes_file_path,
                             names=node_column_names,
                             usecols=columns_to_keep,
                             index_col="id",
                             dtype={
                                 "id": str
                             })
    node_ids = set(nodes_df.index)
    logging.info(f"Loaded all {len(node_ids)} node IDs in nodes.tsv.")

    # Then look for X edges that use only nodes we have
    logging.info(f"Looking for edges that use only node IDs present.")
    edges_tsv_header_path = f"{kg2pre_tsv_version_path}/edges_header.tsv"
    edges_header_df = pd.read_table(edges_tsv_header_path)
    edge_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in edges_header_df.columns]
    test_edge_count = 0
    nodes_used_by_test_edges = set()
    with open(f"{kg2pre_tsv_version_path}/edges.tsv_TEST", "w+") as kg2pre_test_edges_file:
        writer = csv.writer(kg2pre_test_edges_file, delimiter="\t")
        with open(f"{kg2pre_tsv_version_path}/edges.tsv", "r") as kg2pre_edges_file:
            reader = csv.reader(kg2pre_edges_file, delimiter="\t")
            subject_id_col = edge_column_names.index("subject")
            object_id_col = edge_column_names.index("object")
            for row in reader:
                if test_edge_count < 1000000:
                    subject_id = row[subject_id_col]
                    object_id = row[object_id_col]
                    # Save this edge as a test edge if we have both of its nodes
                    if subject_id in node_ids and object_id in node_ids:
                        writer.writerow(row)
                        nodes_used_by_test_edges.add(subject_id)
                        nodes_used_by_test_edges.add(object_id)
                        test_edge_count += 1
                else:
                    logging.info(f"Found enough test edges; won't look for more")
                    break
    logging.info(f"Kept a total of {test_edge_count} test edges that use {len(nodes_used_by_test_edges)} "
                 f"different test nodes.")

    # Then narrow down our nodes to only those used by our saved test edges (plus the build node)
    logging.info(f"Creating test nodes file (will contain only those nodes used by the test edges)..")
    with open(f"{kg2pre_tsv_version_path}/nodes.tsv_TEST", "w+") as kg2pre_test_nodes_file:
        writer = csv.writer(kg2pre_test_nodes_file, delimiter="\t")
        with open(f"{kg2pre_tsv_version_path}/nodes.tsv", "r") as kg2pre_nodes_file:
            reader = csv.reader(kg2pre_nodes_file, delimiter="\t")
            node_id_col = node_column_names.index("id")
            for row in reader:
                node_id = row[node_id_col]
                if node_id in nodes_used_by_test_edges or node_id == "RTX:KG2":
                    writer.writerow(row)

    # Then copy headers to test versions
    logging.info(f"Creating test versions of headers (same as originals)..")
    subprocess.check_call(["cp", f"{kg2pre_tsv_version_path}/nodes_header.tsv",
                           f"{kg2pre_tsv_version_path}/nodes_header.tsv_TEST"])
    subprocess.check_call(["cp", f"{kg2pre_tsv_version_path}/edges_header.tsv",
                           f"{kg2pre_tsv_version_path}/edges_header.tsv_TEST"])

    logging.info(f"Done creating KG2pre test TSV files. They are in {kg2pre_tsv_version_path}")


def make_kg2c_tarball(is_test: bool):
    logging.info(f"Creating tarball of KG2c TSVs..")
    subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/make-kg2c-tarball.sh", "_TEST" if is_test else ""])


def upload_kg2c_files_to_s3(is_test: bool):
    logging.info("Uploading KG2c json and TSV files to S3..")
    tarball_name = f"kg2c-tsv.tar.gz{'_TEST' if is_test else ''}"
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2",
                           f"{KG2C_DIR}/{tarball_name}", "s3://rtx-kg2/"])

    unzipped_lite_json_name = f"kg2c_lite.json{'_TEST' if is_test else ''}"
    subprocess.check_call(["gzip", "-f", f"{KG2C_DIR}/{unzipped_lite_json_name}"])
    zipped_lite_json_name = f"{unzipped_lite_json_name}.gz"
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2",
                           f"{KG2C_DIR}/{zipped_lite_json_name}", "s3://rtx-kg2/"])


def upload_kg2c_files_to_arax_databases_server(kg2pre_version: str, sub_version: str, is_test: bool):
    rtx_config = RTXConfiguration()
    upload_directory = f"/home/rtxconfig/KG{kg2pre_version}"
    logging.info(f"Uploading KG2c artifacts to arax-databases.rtx.ai:{upload_directory}")
    subprocess.check_call(["bash", "-x", f"{KG2C_DIR}/upload-kg2c-artifacts.sh", rtx_config.db_host,
                           sub_version, kg2pre_version, upload_directory, "_TEST" if is_test else ""])


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=[logging.StreamHandler()])
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("kg2pre_version")
    arg_parser.add_argument("sub_version")
    arg_parser.add_argument("-t", "--test", dest="test", action="store_true")
    arg_parser.add_argument("-d", "--download", dest="download", action="store_true")
    arg_parser.add_argument("-e", "--ensureexist", dest="ensure_exist", action="store_true")
    arg_parser.add_argument("-c", "--checkversion", dest="check_version", action="store_true")
    arg_parser.add_argument("-f", "--testfiles", dest="test_files", action="store_true")
    arg_parser.add_argument("-m", "--maketarball", dest="make_tarball", action="store_true")
    arg_parser.add_argument("-s", "--uploads3", dest="upload_s3", action="store_true")
    arg_parser.add_argument("-u", "--uploaddatabases", dest="upload_databases", action="store_true")
    args = arg_parser.parse_args()
    if args.download:
        download_kg2pre_tsvs(args.kg2pre_version)
    if args.ensure_exist:
        ensure_kg2pre_tsvs_exist(args.kg2pre_version)
    if args.check_version:
        check_kg2pre_tsvs_version(args.kg2pre_version)
    if args.test_files:
        create_kg2pre_tsv_test_files(args.kg2pre_version)
    if args.make_tarball:
        make_kg2c_tarball(args.test)
    if args.upload_s3:
        upload_kg2c_files_to_s3(args.test)
    if args.upload_databases:
        upload_kg2c_files_to_arax_databases_server(args.kg2pre_version, args.sub_version, args.test)


if __name__ == "__main__":
    main()
