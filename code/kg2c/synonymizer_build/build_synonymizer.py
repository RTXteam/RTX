import argparse
import logging
import os
import subprocess
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # RTX code directory
from RTXConfiguration import RTXConfiguration
RTX_CONFIG = RTXConfiguration()

SYNONYMIZER_BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SYNONYMIZER_BUILD_DIR}/.."
RTX_CODE_DIR = f"{KG2C_DIR}/.."

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(f"{SYNONYMIZER_BUILD_DIR}/buildsynonymizer.log"),
                              logging.StreamHandler()])


def main():
    start = time.time()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('sub_version', nargs='?', default='v1.0')
    arg_parser.add_argument('start_at', nargs='?', default='1')
    arg_parser.add_argument('-d', '--downloadkg2pre', dest='download_kg2pre', action='store_true')
    arg_parser.add_argument('-u', '--uploadartifacts', dest='upload_artifacts', action='store_true')
    args = arg_parser.parse_args()

    step_1_command = ["python", f"{SYNONYMIZER_BUILD_DIR}/1_build_match_graph_kg2pre.py", args.kg2pre_version] + (["--downloadfresh"] if args.download_kg2pre else [])
    step_2_command = ["python", f"{SYNONYMIZER_BUILD_DIR}/2_build_match_graph_sri.py"]
    step_3_command = ["python", f"{SYNONYMIZER_BUILD_DIR}/3_merge_match_graphs.py"]
    step_4_command = ["python", f"{SYNONYMIZER_BUILD_DIR}/4_cluster_match_graph.py"]
    step_5_command = ["python", f"{SYNONYMIZER_BUILD_DIR}/5_create_synonymizer_sqlite.py"]
    all_steps = [step_1_command, step_2_command, step_3_command, step_4_command, step_5_command]

    # Run the requested steps (default is all steps)
    step_num_to_start_at = int(args.start_at)
    steps_to_run = all_steps[step_num_to_start_at - 1:]
    for step_to_run in steps_to_run:
        subprocess.check_call(step_to_run)
    logging.info(f"Done building core synonymizer (node_synonymizer.sqlite).")

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
    subprocess.check_call(["mv", f"{KG2C_DIR}/synonymizer_build/node_synonymizer.sqlite",
                           f"{RTX_CODE_DIR}/ARAX/NodeSynonymizer/{final_synonymizer_name}"])

    logging.info(f"Done with synonymizer build. Took {round(((time.time() - start) / 60) / 60, 1)} hours.")


if __name__ == "__main__":
    main()
