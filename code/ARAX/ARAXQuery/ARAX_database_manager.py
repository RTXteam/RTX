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

    def check_date(self, file_path, max_days = 31):
        if os.path.exists(local_path):
            now_time = datetime.datetime.now()
            modified_time = time.localtime(os.stat(file_path).st_mtime)
            modified_time = datetime.datetime(*modified_time[:6])
            if (now_time - modified_time).days > max_days:
                return True
            else:
                return False
        else:
            return True

    def scp_database(self, user, host, remote_path, local_path):
        os.system(f"scp {user}@{host}:{remote_path} {local_path}")

    def force_download_all(self):
        pass

    def check_all(self):
        pass