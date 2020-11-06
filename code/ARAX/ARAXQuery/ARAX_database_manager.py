#!/usr/bin/python3

import os
import datetime
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
from RTXConfiguration import RTXConfiguration

class ARAXDatabaseManager:
    def __init__(self, live = "Production"):
        self.RTXConfig = RTXConfiguration()
        self.RTXConfig.live = live

        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")

        predict_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'predictor','retrain_data'])
        ngd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay'])
        cohd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        cohd_name = self.RTXConfig.cohd_database_path.split('/')[-1]
        synonymizer_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer'])
        prob_sqlite_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'predictor', 'retrain_data'])

        self.local_paths = {
            'cohd_database': f"{cohd_filepath}/{cohd_name}",
            'graph_database': f"{predict_filepath}/GRAPH.sqlite",
            'log_model': f"{predict_filepath}/LogModel.pkl",
            'curie_to_pmids': f"{ngd_filepath}/ngd/curie_to_pmids.sqlite",
            'node_synonymizer': f"{synonymizer_filepath}/node_synonymizer.sqlite",
            'rel_max': f"{prob_sqlite_filepath}/rel_max.emb.gz",
            'map_txt': f"{prob_sqlite_filepath}/map.txt"
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

    def scp_database(self, remote_location, local_path):
        os.system(f"scp {remote_location} {local_path}")

    def force_download_all(self):
        for database_name in self.remote_locations.keys():
            scp_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name])

    def check_all(self):
        for database_name, file_path in self.local_paths.items():
            if os.path.exists(file_path):
                now_time = datetime.datetime.now()
                modified_time = time.localtime(os.stat(file_path).st_mtime)
                modified_time = datetime.datetime(*modified_time[:6])
                print(f"{database_name}: local file is {(now_time - modified_time).days} days old")
            else:
                print(f"{database_name}: no file found at {file_path}")

    def update_databases(self, max_days=31, debug=False):
        for database_name, local_path in self.local_paths.items():
            if check_date(local_path, max_days=max_days):
                if debug:
                    print(f"{database_name} not present or older than {max_days} days. Updating file...")
                scp_database(remote_location=self.remote_locations[database_name], local_path=local_path)


def main():
    DBManager = ARAXDatabaseManager("Production")
    DBManager.update_databases(debug=True)

if __name__ == "__main__":
    main()