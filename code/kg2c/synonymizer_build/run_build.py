import argparse
import subprocess


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('start_at', nargs='?', default='1')
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    args = arg_parser.parse_args()

    step_1_command = ["python", "1_build_match_graph_kg2pre.py", args.kg2pre_version] + (["--downloadfresh"] if args.download_fresh else [])
    step_2_command = ["python", "2_build_match_graph_sri.py"]
    step_3_command = ["python", "3_merge_match_graphs.py"]
    step_4_command = ["python", "4_cluster_match_graph.py"]
    step_5_command = ["python", "5_build_cluster_debug_db.py"]
    all_steps = [step_1_command, step_2_command, step_3_command, step_4_command, step_5_command]

    # Run the requested steps (default is all steps)
    step_num_to_start_at = int(args.start_at)
    steps_to_run = all_steps[step_num_to_start_at - 1:]
    for step_to_run in steps_to_run:
        subprocess.check_call(step_to_run)


if __name__ == "__main__":
    main()
