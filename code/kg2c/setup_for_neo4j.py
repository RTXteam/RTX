#!/bin/env python3
"""
This script sets up your environment so that it can be used to host KG2c in Neo4j. It uses a script from the
RTX-KG2 repo.

Usage: python3 setup_for_neo4j.py
"""
import logging
import os
import subprocess

KG2C_DIR = f"{os.path.dirname(os.path.abspath(__file__))}"


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        handlers=[logging.FileHandler("build.log"),
                                  logging.StreamHandler()])
    logging.info("SETTING UP FOR NEO4J")

    # Get master-config.shinc from the KG2 repo
    shinc_file_name = "master-config.shinc"
    logging.info(f"Getting {shinc_file_name} from KG2pre repo")
    rtx_kg2_repo_url = "https://github.com/RTXteam/RTX-KG2/blob/master"
    subprocess.check_call(["curl", "-L", f"{rtx_kg2_repo_url}/{shinc_file_name}?raw=true", "-o", f"{KG2C_DIR}/{shinc_file_name}"])

    # Get the system memory script from the KG2 repo
    mem_file_name = "get-system-memory-gb.sh"
    logging.info(f"Getting {mem_file_name} from KG2pre repo")
    subprocess.check_call(["curl", "-L", f"{rtx_kg2_repo_url}/{mem_file_name}?raw=true", "-o", f"{KG2C_DIR}/{mem_file_name}"])

    # Get the Neo4j setup script from the KG2 repo
    setup_script_name = "setup-kg2-neo4j.sh"
    logging.info(f"Getting {setup_script_name} from KG2pre repo")
    subprocess.check_call(["curl", "-L", f"{rtx_kg2_repo_url}/{setup_script_name}?raw=true", "-o", f"{KG2C_DIR}/{setup_script_name}"])

    # Now run the Neo4j setup script
    logging.info(f"Running {setup_script_name}")
    subprocess.check_call(["cd", KG2C_DIR])
    subprocess.check_call(["bash", "-x", setup_script_name])

    logging.info("DONE SETTING UP FOR NEO4J")


if __name__ == "__main__":
    main()
