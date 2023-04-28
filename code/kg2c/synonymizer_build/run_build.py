import argparse
import subprocess


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('kg2pre_version')
    arg_parser.add_argument('--downloadfresh', dest='download_fresh', action='store_true')
    args = arg_parser.parse_args()

    subprocess.check_call(["python", "1_build_match_graph_kg2pre.py", args.kg2pre_version] + (["--downloadfresh"] if args.download_fresh else []))
    subprocess.check_call(["python", "2_build_match_graph_sri.py"])
    subprocess.check_call(["python", "3_merge_match_graphs.py"])
    subprocess.check_call(["python", "4_cluster_match_graph.py"])
    subprocess.check_call(["python", "5_build_cluster_debug_db.py"])


if __name__ == "__main__":
    main()
