import csv
import gzip
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
SYNONYMIZER_BUILD_DIR = f"{KG2C_DIR}/synonymizer_build"


def download_kg2pre_tsvs(kg2pre_version: str):
    kg2pre_tarball_name = "kg2-tsv-for-neo4j.tar.gz"
    kg2pre_tsv_version_dir = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    if not pathlib.Path(kg2pre_tsv_version_dir).exists():
        os.system(f"mkdir -p {kg2pre_tsv_version_dir}")
    logging.info(f"Downloading {kg2pre_tarball_name} from the rtx-kg2 S3 bucket into {kg2pre_tsv_version_dir}")
    subprocess.check_call(["aws", "s3", "cp", "--no-progress", "--region", "us-west-2",
                           f"s3://rtx-kg2/{kg2pre_tarball_name}", kg2pre_tsv_version_dir])
    logging.info(f"Unpacking {kg2pre_tarball_name}..")
    subprocess.check_call(["tar", "-xvzf", f"{kg2pre_tsv_version_dir}/{kg2pre_tarball_name}",
                           "-C", kg2pre_tsv_version_dir])


def ensure_kg2pre_tsvs_exist(kg2pre_version: str, is_test: Optional[bool] = None):
    kg2pre_tsv_version_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    logging.info(f"Ensuring that KG2pre TSVs exist in {kg2pre_tsv_version_path}")
    if not pathlib.Path(kg2pre_tsv_version_path).exists():
        raise ValueError(f"The {kg2pre_version} KG2pre TSVs directory does not exist locally; "
                         f"it should be at {kg2pre_tsv_version_path}. You need to either put "
                         f"nodes.tsv, edges.tsv, nodes_header.tsv, and edges_header.tsv files into "
                         f"{kg2pre_tsv_version_path} or choose to download fresh copies of the KG2pre TSVs from S3.")
    required_kg2pre_tsv_files = [f"nodes.tsv{'_TEST' if is_test else ''}",
                                 f"edges.tsv{'_TEST' if is_test else ''}",
                                 f"nodes_header.tsv{'_TEST' if is_test else ''}",
                                 f"edges_header.tsv{'_TEST' if is_test else ''}"]
    for kg2pre_tsv_file_name in required_kg2pre_tsv_files:
        if not pathlib.Path(f"{kg2pre_tsv_version_path}/{kg2pre_tsv_file_name}").exists():
            raise ValueError(f"Required KG2pre TSV file {kg2pre_tsv_file_name} does not exist in "
                             f"{kg2pre_tsv_version_path}. You need to either put it there or opt to download fresh "
                             f"KG2pre TSV files. Required KG2pre TSV files are: {required_kg2pre_tsv_files}")
    logging.info(f"Confirmed KG2pre TSVs exist in {kg2pre_tsv_version_path}")


def check_kg2pre_tsvs_version(kg2pre_version: str, biolink_version: Optional[str] = None, is_test: Optional[bool] = None):
    # First ensure that the files actually exist
    ensure_kg2pre_tsvs_exist(kg2pre_version, is_test)

    # Load KG2pre nodes data, including only the columns relevant to us (to locate the build node)
    kg2pre_tsv_version_path = f"{KG2PRE_TSVS_DIR}/{kg2pre_version}"
    logging.info(f"Confirming that local KG2pre TSVs in {kg2pre_tsv_version_path} are for the "
                 f"requested KG2pre version ({kg2pre_version})..")
    logging.info(f"Loading nodes into dataframe to extract KG2pre build node..")
    nodes_tsv_path = f"{kg2pre_tsv_version_path}/nodes.tsv{'_TEST' if is_test else ''}"
    nodes_tsv_header_path = f"{kg2pre_tsv_version_path}/nodes_header.tsv{'_TEST' if is_test else ''}"
    nodes_header_df = pd.read_table(nodes_tsv_header_path)
    node_column_names = [column_name.split(":")[0] if not column_name.startswith(":") else column_name
                         for column_name in nodes_header_df.columns]
    columns_to_keep = ["id", "name", "iri"]
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
    test_suffix = "_TEST" if is_test else ""
    subprocess.check_call(["tar", "-czvf", f"{KG2C_DIR}/kg2c-tsv.tar.gz{test_suffix}", "-C", KG2C_DIR,
                           f"nodes_c.tsv{test_suffix}", f"nodes_c_header.tsv{test_suffix}",
                           f"edges_c.tsv{test_suffix}", f"edges_c_header.tsv{test_suffix}"])


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


def upload_file_to_arax_databases_server(local_file_path: str, remote_file_name: str, kg2pre_version: str,
                                         is_extra_file: bool = False):
    # First make sure the specified remote directory exists on arax-databases.rtx.ai (will not hurt if already does)
    rtx_config = RTXConfiguration()
    remote_dir_path = f"/home/rtxconfig/KG{kg2pre_version}{'/extra_files' if is_extra_file else ''}"
    os.system(f'ssh rtxconfig@{rtx_config.db_host} "mkdir -p {remote_dir_path}"')
    logging.info(f"Uploading {local_file_path} to arax-databases server..")
    os.system(f"scp {local_file_path} rtxconfig@{rtx_config.db_host}:{remote_dir_path}/{remote_file_name}")


def gzip_file(file_path: str):
    logging.info(f"Gzipping {file_path}..")
    with open(file_path, "rb") as unzipped_file:
        with gzip.open(f"{file_path}.gz", "wb") as zipped_file:
            zipped_file.writelines(unzipped_file)
    # Delete the unzipped version
    subprocess.check_call(["rm", "-f", file_path])


def upload_kg2c_files_to_arax_databases_server(kg2pre_version: str, sub_version: str, is_test: bool):
    logging.info(f"Uploading KG2c artifacts to arax-databases server")

    # First upload required files
    test_suffix = "_TEST" if is_test else ""
    upload_file_to_arax_databases_server(local_file_path=f"{KG2C_DIR}/kg2c.sqlite{test_suffix}",
                                         remote_file_name=f"kg2c_{sub_version}_KG{kg2pre_version}.sqlite{test_suffix}",
                                         kg2pre_version=kg2pre_version)
    upload_file_to_arax_databases_server(local_file_path=f"{KG2C_DIR}/meta_kg.json{test_suffix}",
                                         remote_file_name=f"meta_kg_{sub_version}_KG{kg2pre_version}c.json{test_suffix}",
                                         kg2pre_version=kg2pre_version)
    upload_file_to_arax_databases_server(local_file_path=f"{KG2C_DIR}/fda_approved_drugs.pickle{test_suffix}",
                                         remote_file_name=f"fda_approved_drugs_{sub_version}_KG{kg2pre_version}c.pickle{test_suffix}",
                                         kg2pre_version=kg2pre_version)

    # Then upload files not actually needed for running ARAX code
    upload_file_to_arax_databases_server(local_file_path=f"{KG2C_DIR}/kg2c-tsv.tar.gz{test_suffix}",
                                         remote_file_name=f"kg2c-tsv.tar.gz{test_suffix}",
                                         kg2pre_version=kg2pre_version,
                                         is_extra_file=True)


def upload_synonymizer_files_to_arax_databases_server(kg2pre_version: str, sub_version: str):
    logging.info(f"Uploading synonymizer artifacts to arax-databases server")

    # Upload required databases
    upload_file_to_arax_databases_server(local_file_path=f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite",
                                         remote_file_name=f"node_synonymizer_{sub_version}_KG{kg2pre_version}.sqlite",
                                         kg2pre_version=kg2pre_version)
    upload_file_to_arax_databases_server(local_file_path=f"{SYNONYMIZER_BUILD_DIR}/autocomplete.sqlite",
                                         remote_file_name=f"autocomplete_{sub_version}_KG{kg2pre_version}.sqlite",
                                         kg2pre_version=kg2pre_version)

    # Upload 'extra files' (nice for debugging; not needed by running ARAX code)
    file_names = ["3_merged_match_nodes.tsv", "3_merged_match_edges.tsv", "4_match_nodes_preprocessed.tsv",
                  "4_match_edges_preprocessed.tsv", "5_report_category_counts.tsv", "5_report_cluster_sizes.tsv",
                  "5_report_cluster_sizes_non_sri_nodes.tsv", "5_report_major_branch_counts.tsv",
                  "5_report_oversized_clusters.tsv", "5_report_predicate_counts.tsv",
                  "5_report_primary_knowledge_source_counts.tsv", "5_report_upstream_resource_counts.tsv",
                  "kg2_nodes_not_in_sri_nn.tsv"]
    for file_name in file_names:
        upload_file_to_arax_databases_server(local_file_path=f"{SYNONYMIZER_BUILD_DIR}/{file_name}",
                                             remote_file_name=file_name,
                                             kg2pre_version=kg2pre_version,
                                             is_extra_file=True)
    logging.info(f"Done uploading synonymizer artifacts to arax databases server.")


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
