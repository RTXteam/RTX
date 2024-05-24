import argparse
import logging
import os
import subprocess
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import a_build_match_graph_kg2pre, b_build_match_graph_sri, c_merge_match_graphs, d_cluster_match_graph, e_create_synonymizer_sqlite

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # RTX code directory
from RTXConfiguration import RTXConfiguration
RTX_CONFIG = RTXConfiguration()

SYNONYMIZER_BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SYNONYMIZER_BUILD_DIR}/.."
RTX_CODE_DIR = f"{KG2C_DIR}/.."
ARAX_DIR = f"{RTX_CODE_DIR}/ARAX"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(f"{SYNONYMIZER_BUILD_DIR}/buildsynonymizer.log")])


def main():
    start = time.time()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version',
                            help="The version of KG2pre to build this synonymizer from (e.g., 2.9.2).")
    arg_parser.add_argument('sub_version',
                            help="The synonymizer sub version (e.g., v1.0); generally should be v1.0 unless you are "
                                 "doing a synonymizer rebuild for a KG2 version that already has a synonymizer - then "
                                 "it should be v1.1, or etc.")
    arg_parser.add_argument('start_at', nargs='?', default='1',
                            help="The step in the synonymizer build to begin at. Used only for development purposes.")
    arg_parser.add_argument('-d', '--downloadkg2pre', dest='download_kg2pre', action='store_true',
                            help="Specifies that the KG2pre TSV files should be downloaded from S3. If this flag is not "
                                 "set, local KG2pre TSVs will be used.")
    arg_parser.add_argument('-u', '--uploadartifacts', dest='upload_artifacts', action='store_true',
                            help="Specifies that artifacts of the build should be uploaded to the ARAX "
                                 "databases server.")
    args = arg_parser.parse_args()
    logging.info(f"Starting synonymizer build. kg2pre_version={args.kg2pre_version}, sub_version={args.sub_version}, "
                 f"--downloadkg2pre={args.download_kg2pre}, --uploadartifacts={args.upload_artifacts}")

    # Run the requested steps (default is all steps)
    step_num_to_start_at = int(args.start_at)
    if step_num_to_start_at <= 1:
        a_build_match_graph_kg2pre.run(kg2pre_version=args.kg2pre_version,
                                       download_fresh=args.download_kg2pre)
    if step_num_to_start_at <= 2:
        b_build_match_graph_sri.run()
    if step_num_to_start_at <= 3:
        c_merge_match_graphs.run()
    if step_num_to_start_at <= 4:
        d_cluster_match_graph.run()
    if step_num_to_start_at <= 5:
        e_create_synonymizer_sqlite.run()
    logging.info(f"Done building node_synonymizer.sqlite. Took "
                 f"{round(((time.time() - start) / 60) / 60, 1)} hours.")

    logging.info(f"Regenerating autocomplete database..")
    subprocess.check_call(["python", f"{SYNONYMIZER_BUILD_DIR}/dump_autocomplete_node_info.py", args.kg2pre_version])
    subprocess.check_call(["python", f"{RTX_CODE_DIR}/autocomplete/create_load_db.py",
                           "--input", f"{SYNONYMIZER_BUILD_DIR}/autocomplete_node_info.tsv",
                           "--output", f"{SYNONYMIZER_BUILD_DIR}/autocomplete.sqlite"])

    if args.upload_artifacts:
        upload_directory = f"/home/rtxconfig/KG{args.kg2pre_version}"
        logging.info(f"Uploading synonymizer artifacts to arax-databases.rtx.ai:{upload_directory}")
        subprocess.check_call(["bash", "-x", f"{SYNONYMIZER_BUILD_DIR}/upload-synonymizer-artifacts.sh",
                               RTX_CONFIG.db_host, upload_directory, args.sub_version, args.kg2pre_version])

    # Move the new synonymizer into the ARAX NodeSynonymizer directory so it can be queried properly
    logging.info(f"Moving the new synonymizer into the ARAX NodeSynonymizer directory")
    final_synonymizer_name = f"node_synonymizer_{args.sub_version}_KG{args.kg2pre_version}.sqlite"
    subprocess.check_call(["mv", f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite",
                           f"{ARAX_DIR}/NodeSynonymizer/{final_synonymizer_name}"])

    logging.info(f"Done with synonymizer build. Took {round(((time.time() - start) / 60) / 60, 1)} hours.")

    # TODO: Add some automated testing..


if __name__ == "__main__":
    main()
