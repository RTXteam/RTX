import argparse
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('start_at', nargs='?', default='1')
    arg_parser.add_argument('--downloadkg2pre', dest='download_kg2pre', action='store_true')
    arg_parser.add_argument('--downloadsri', dest='download_sri', action='store_true')
    arg_parser.add_argument('--useconfigname', dest='use_config_name', action='store_true')
    args = arg_parser.parse_args()

    step_1_command = ["python", f"{SCRIPT_DIR}/1_build_match_graph_kg2pre.py", args.kg2pre_version] + (["--downloadfresh"] if args.download_kg2pre else [])
    step_2_command = ["python", f"{SCRIPT_DIR}/2_build_match_graph_sri.py"] + (["--downloadfresh"] if args.download_sri else [])
    step_3_command = ["python", f"{SCRIPT_DIR}/3_merge_match_graphs.py"]
    step_4_command = ["python", f"{SCRIPT_DIR}/4_cluster_match_graph.py"]
    step_5_command = ["python", f"{SCRIPT_DIR}/5_create_synonymizer_sqlite.py"] + (["--useconfigname"] if args.use_config_name else [])
    all_steps = [step_1_command, step_2_command, step_3_command, step_4_command, step_5_command]

    # Run the requested steps (default is all steps)
    step_num_to_start_at = int(args.start_at)
    steps_to_run = all_steps[step_num_to_start_at - 1:]
    for step_to_run in steps_to_run:
        subprocess.check_call(step_to_run)


if __name__ == "__main__":
    main()
