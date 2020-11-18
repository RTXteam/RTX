#!/usr/bin/python3

import os
import sys
import datetime
import json
import time
import argparse

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

class ARAXDatabaseManager:
    def __init__(self, live = "Production"):
        self.RTXConfig = RTXConfiguration()
        self.RTXConfig.live = live

        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")

        pred_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
        ngd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
        cohd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        synonymizer_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NodeSynonymizer'])
        

        self.local_paths = {
            'cohd_database': f"{cohd_filepath}{os.path.sep}{self.RTXConfig.cohd_database_path.split('/')[-1]}",
            'graph_database': f"{pred_filepath}{os.path.sep}{self.RTXConfig.graph_database_path.split('/')[-1]}",
            'log_model': f"{pred_filepath}{os.path.sep}{self.RTXConfig.log_model_path.split('/')[-1]}",
            'curie_to_pmids': f"{ngd_filepath}{os.path.sep}{self.RTXConfig.curie_to_pmids_path.split('/')[-1]}",
            'node_synonymizer': f"{synonymizer_filepath}{os.path.sep}{self.RTXConfig.node_synonymizer_path.split('/')[-1]}",
            'rel_max': f"{pred_filepath}{os.path.sep}{self.RTXConfig.rel_max_path.split('/')[-1]}",
            'map_txt': f"{pred_filepath}{os.path.sep}{self.RTXConfig.map_txt_path.split('/')[-1]}"
        }
        self.remote_locations = {
            'cohd_database': f"{self.RTXConfig.cohd_database_username}@{self.RTXConfig.cohd_database_host}:{self.RTXConfig.cohd_database_path}",
            'graph_database': f"{self.RTXConfig.graph_database_username}@{self.RTXConfig.graph_database_host}:{self.RTXConfig.graph_database_path}",
            'log_model': f"{self.RTXConfig.log_model_username}@{self.RTXConfig.log_model_host}:{self.RTXConfig.log_model_path}",
            'curie_to_pmids': f"{self.RTXConfig.curie_to_pmids_username}@{self.RTXConfig.curie_to_pmids_host}:{self.RTXConfig.curie_to_pmids_path}",
            'node_synonymizer': f"{self.RTXConfig.node_synonymizer_username}@{self.RTXConfig.node_synonymizer_host}:{self.RTXConfig.node_synonymizer_path}",
            'rel_max': f"{self.RTXConfig.rel_max_username}@{self.RTXConfig.rel_max_host}:{self.RTXConfig.rel_max_path}",
            'map_txt': f"{self.RTXConfig.map_txt_username}@{self.RTXConfig.map_txt_host}:{self.RTXConfig.map_txt_path}"
        }

    def check_date(self, file_path, max_days = 31):
        if os.path.exists(file_path):
            now_time = datetime.datetime.now()
            modified_time = time.localtime(os.stat(file_path).st_mtime)
            modified_time = datetime.datetime(*modified_time[:6])
            if (now_time - modified_time).days > max_days:
                return True
            else:
                return False
        else:
            return True

    def rsync_database(self, remote_location, local_path, debug=False):
        verbose = ""
        if debug:
            verbose = "vv"
        os.system(f"rsync -hzc{verbose} {remote_location} {local_path}")

    def force_download_all(self, debug=False):
        for database_name in self.remote_locations.keys():
            if debug:
                print(f"Downloading {self.remote_locations[database_name].sep('/')[-1]}...")
            self.rsync_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], debug=debug)

    def check_all(self, max_days=31, debug=False):
        update_flag = False
        for database_name, file_path in self.local_paths.items():
            if os.path.exists(file_path):
                if debug:
                    now_time = datetime.datetime.now()
                    modified_time = time.localtime(os.stat(file_path).st_mtime)
                    modified_time = datetime.datetime(*modified_time[:6])
                    file_days = (now_time - modified_time).days
                    print(f"{database_name}: local file is {file_days} days old")
                    if file_days > max_days:
                        update_flag = True
                else:
                    if self.check_date(file_path, max_days):
                        return True
            else:
                if debug:
                    print(f"{database_name}: no file found at {file_path}")
                    update_flag = True
                else:
                    return True
        return update_flag

    def update_databases(self, max_days=31, debug=False):
        for database_name, local_path in self.local_paths.items():
            if self.check_date(local_path, max_days=max_days):
                if debug:
                    print(f"{database_name} not present or older than {max_days} days. Updating file...")
                self.rsync_database(remote_location=self.remote_locations[database_name], local_path=local_path, debug=debug)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check_local", action='store_true')
    parser.add_argument("-f", "--force_download", action='store_true')
    parser.add_argument("-l", "--live", type=str, help="Live parameter for RTXConfiguration", default="Production", required=False)
    arguments = parser.parse_args()
    DBManager = ARAXDatabaseManager(arguments.live)
    if arguments.check_local:
        DBManager.check_all(debug=True)
    elif arguments.force_download:
        DBManager.force_download_all(debug=True)
    else:
        DBManager.update_databases(debug=True)

if __name__ == "__main__":
    main()