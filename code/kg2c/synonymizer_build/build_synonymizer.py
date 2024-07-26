import argparse
import logging
import os
import subprocess
import sys
import time

# NOTE: Importing these files this way because their names begin with a number (normal 'import __' doesn't work)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
build_match_graph_kg2pre = __import__("1_build_match_graph_kg2pre")
build_match_graph_sri = __import__("2_build_match_graph_sri")
merge_match_graphs = __import__("3_merge_match_graphs")
cluster_match_graph = __import__("4_cluster_match_graph")
create_synonymizer_sqlite = __import__("5_create_synonymizer_sqlite")

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # RTX code directory
from RTXConfiguration import RTXConfiguration
RTX_CONFIG = RTXConfiguration()
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # KG2c directory
import file_manager

SYNONYMIZER_BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
KG2C_DIR = f"{SYNONYMIZER_BUILD_DIR}/.."
RTX_CODE_DIR = f"{KG2C_DIR}/.."
ARAX_DIR = f"{RTX_CODE_DIR}/ARAX"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(f"{SYNONYMIZER_BUILD_DIR}/buildsynonymizer.log")])


# Include uncaught exceptions in build log - thank you: https://stackoverflow.com/a/16993115
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def main():
    start = time.time()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version',
                            help="The version of KG2pre to build this synonymizer from (e.g., 2.10.0).")
    arg_parser.add_argument('sub_version',
                            help="The sub-version for this KG2c build (e.g., v1.0); we always use v1.0 the first "
                                 "time we are building KG2c from a given KG2pre version; if we do a second build of"
                                 " KG2c from that *same* KG2pre version, we would use v1.1, and so on.")
    arg_parser.add_argument('start_at', nargs='?', default='1',
                            help="Optional parameter that specifies the step in the synonymizer build to begin at "
                                 "(default is 1; valid values are 1-5). Allows partial builds of "
                                 "the synonymizer; used only for development purposes. Step 1 is building the KG2pre "
                                 "match graph, 2 is building the SRI NodeNormalizer match graph, 3 is merging the "
                                 "match graphs, 4 is clustering the merged match graph, and 5 is creating the "
                                 "final synonymizer sqlite and build reports.")
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
        build_match_graph_kg2pre.run(kg2pre_version=args.kg2pre_version,
                                     download_fresh=args.download_kg2pre)
    if step_num_to_start_at <= 2:
        build_match_graph_sri.run()
    if step_num_to_start_at <= 3:
        merge_match_graphs.run()
    if step_num_to_start_at <= 4:
        cluster_match_graph.run()
    if step_num_to_start_at <= 5:
        create_synonymizer_sqlite.run()
    logging.info(f"Done building node_synonymizer.sqlite. Took "
                 f"{round(((time.time() - start) / 60) / 60, 1)} hours.")

    logging.info(f"Regenerating autocomplete database..")
    subprocess.check_call(["python", f"{SYNONYMIZER_BUILD_DIR}/dump_autocomplete_node_info.py", args.kg2pre_version])
    subprocess.check_call(["python", f"{RTX_CODE_DIR}/autocomplete/create_load_db.py",
                           "--input", f"{SYNONYMIZER_BUILD_DIR}/autocomplete_node_info.tsv",
                           "--output", f"{SYNONYMIZER_BUILD_DIR}/autocomplete.sqlite"])

    if args.upload_artifacts:
        file_manager.upload_synonymizer_files_to_arax_databases_server(args.kg2pre_version, args.sub_version)

    # Move the new synonymizer into the ARAX NodeSynonymizer directory so it can be queried properly
    logging.info(f"Moving the new synonymizer into the ARAX NodeSynonymizer directory")
    final_synonymizer_name = f"node_synonymizer_{args.sub_version}_KG{args.kg2pre_version}.sqlite"
    subprocess.check_call(["mv", f"{SYNONYMIZER_BUILD_DIR}/node_synonymizer.sqlite",
                           f"{ARAX_DIR}/NodeSynonymizer/{final_synonymizer_name}"])

    logging.info(f"Done with synonymizer build. Took {round(((time.time() - start) / 60) / 60, 1)} hours.")

    # Run automated tests
    os.system(f"pytest -v {SYNONYMIZER_BUILD_DIR}/test_synonymizer.py --synonymizername {final_synonymizer_name}")


if __name__ == "__main__":
    main()
