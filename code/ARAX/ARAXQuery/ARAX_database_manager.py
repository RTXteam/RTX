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

knowledge_sources_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources'])
versions_path = os.path.sep.join([knowledge_sources_filepath, 'db_versions.json'])


class ARAXDatabaseManager:
    def __init__(self, live = "Production"):
        self.RTXConfig = RTXConfiguration()
        self.RTXConfig.live = live

        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")

        pred_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
        if not  os.path.exists(pred_filepath):
            os.system(f"mkdir -p {pred_filepath}")
        
        ngd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
        if not  os.path.exists(ngd_filepath):
            os.system(f"mkdir -p {ngd_filepath}")
        
        cohd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        if not  os.path.exists(cohd_filepath):
            os.system(f"mkdir -p {cohd_filepath}")
        
        synonymizer_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer'])
        if not  os.path.exists(synonymizer_filepath):
            os.system(f"mkdir -p {synonymizer_filepath}")

        self.local_paths = {
            'cohd_database': f"{cohd_filepath}{os.path.sep}{self.RTXConfig.cohd_database_path.split('/')[-1]}",
            'graph_database': f"{pred_filepath}{os.path.sep}{self.RTXConfig.graph_database_path.split('/')[-1]}",
            'log_model': f"{pred_filepath}{os.path.sep}{self.RTXConfig.log_model_path.split('/')[-1]}",
            'curie_to_pmids': f"{ngd_filepath}{os.path.sep}{self.RTXConfig.curie_to_pmids_path.split('/')[-1]}",
            'node_synonymizer': f"{synonymizer_filepath}{os.path.sep}{self.RTXConfig.node_synonymizer_path.split('/')[-1]}",
            'dtd_prob': f"{pred_filepath}{os.path.sep}{self.RTXConfig.dtd_prob_path.split('/')[-1]}"
        }
        # user, host, and paths to databases on remote server
        self.remote_locations = {
            'cohd_database': f"{self.RTXConfig.cohd_database_username}@{self.RTXConfig.cohd_database_host}:{self.RTXConfig.cohd_database_path}",
            'graph_database': f"{self.RTXConfig.graph_database_username}@{self.RTXConfig.graph_database_host}:{self.RTXConfig.graph_database_path}",
            'log_model': f"{self.RTXConfig.log_model_username}@{self.RTXConfig.log_model_host}:{self.RTXConfig.log_model_path}",
            'curie_to_pmids': f"{self.RTXConfig.curie_to_pmids_username}@{self.RTXConfig.curie_to_pmids_host}:{self.RTXConfig.curie_to_pmids_path}",
            'node_synonymizer': f"{self.RTXConfig.node_synonymizer_username}@{self.RTXConfig.node_synonymizer_host}:{self.RTXConfig.node_synonymizer_path}",
            'dtd_prob': f"{self.RTXConfig.dtd_prob_username}@{self.RTXConfig.dtd_prob_host}:{self.RTXConfig.dtd_prob_path}"
        }
        # database locations if inside rtx1 docker container
        self.docker_paths = {
            'cohd_database': f"{self.RTXConfig.cohd_database_path.replace('/translator/','/mnt/')}",
            'graph_database': f"{self.RTXConfig.graph_database_path.replace('/translator/','/mnt/')}",
            'log_model': f"{self.RTXConfig.log_model_path.replace('/translator/','/mnt/')}",
            'curie_to_pmids': f"{self.RTXConfig.curie_to_pmids_path.replace('/translator/','/mnt/')}",
            'node_synonymizer': f"{self.RTXConfig.node_synonymizer_path.replace('/translator/','/mnt/')}",
            'dtd_prob': f"{self.RTXConfig.dtd_prob_path.replace('/translator/','/mnt/')}"
        }

        # database local paths + version numbers
        self.db_versions = {
            'cohd_database': {
                'path': self.local_paths['cohd_database'],
                'version': self.RTXConfig.cohd_database_version
            },
            'graph_database': {
                'path': self.local_paths['graph_database'],
                'version': self.RTXConfig.graph_database_version
            },
            'log_model': {
                'path': self.local_paths['log_model'],
                'version': self.RTXConfig.log_model_version
            },
            'curie_to_pmids': {
                'path': self.local_paths['curie_to_pmids'],
                'version': self.RTXConfig.curie_to_pmids_version
            },
            'node_synonymizer': {
                'path': self.local_paths['node_synonymizer'],
                'version': self.RTXConfig.node_synonymizer_version
            },
            'dtd_prob': {
                'path': self.local_paths['dtd_prob'],
                'version': self.RTXConfig.dtd_prob_version
            }
        }

    def update_databases(self, debug = False, response = None):
        if os.path.exists(versions_path): # check if the versions file exists
            with open(versions_path,"r") as fid:
                local_versions = json.load(fid)
            for database_name, local_path in self.local_paths.items(): # iterate through all databases
                if database_name not in local_versions: # if database is not present locally
                    if debug:
                        print(f"{database_name} not present locally, downloading now...")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
                elif local_versions[database_name]['version'] != self.db_versions[database_name]['version']: # If database is present but wrong version
                    if debug:
                        print(f"{database_name} has a local version, '{local_versions[database_name]['version']}', which does not match the remote version, '{self.db_versions[database_name]['version']}'.")
                        print("downloading remote version...")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
                    if os.path.exists(self.local_paths[database_name]): # check that download worked if so remove old version
                        if debug:
                            print("Download successful. Removing local version...")
                        if os.path.exists(local_versions[database_name]['path']):
                            os.system(f"rm {local_versions[database_name]['path']}") 
                    else:
                        if debug:
                            print(f"Error downloading {database_name} leaving local copy.")
                        if response is not None:
                            response.warning(f"Error downloading {database_name} reverting to using local copy.") 
                        self.db_versions[database_name] = local_versions[database_name]
                elif not os.path.exists(self.local_paths[database_name]): # If database file is missing
                    if debug:
                        print(f"{database_name} not present locally, downloading now...")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
                else:
                    if debug:
                        print(f"Local version of {database_name} matches the remote version, skipping...")
            with open(versions_path,"w") as fid:
                if debug:
                    print("Saving new version file...")
                json.dump(self.db_versions, fid)
        else: # If database manager has never been run download all databases
            if debug:
                print("No local verson json file present. Downloading all databases...")
            if response is not None:
                response.debug(f"No local verson json file present. Downloading all databases...")
            self.force_download_all(debug=debug)
            with open(versions_path,"w") as fid:
                if debug:
                    print("Saving new version file...")
                json.dump(self.db_versions, fid)
        return response

    def check_versions(self, debug=False):
        download_flag = False
        if os.path.exists(versions_path):
            with open(versions_path,"r") as fid:
                local_versions = json.load(fid)
            for database_name, local_path in self.local_paths.items():
                if database_name not in local_versions:
                    if debug:
                        print(f"{database_name} not present locally")
                    download_flag = True
                elif local_versions[database_name]['version'] != self.db_versions[database_name]['version']:
                    if debug:
                        print(f"{database_name} has a local version, '{local_versions[database_name]['version']}', which does not match the remote version, '{self.db_versions[database_name]['version']}'.")
                    download_flag = True
                elif not os.path.exists(local_path):
                    if debug:
                        print(f"{database_name} not present locally")
                    download_flag = True
                else:
                    if debug:
                        print(f"Local version of {database_name} matches the remote version")
        else:
            if debug:
                print("No local verson json file present")
            download_flag = True
        return download_flag


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

    def download_database(self, remote_location, local_path, remote_path, debug=False):
        if os.path.exists(remote_path): # if on the server symlink instead of downloading
            self.symlink_database(local_path=local_path, remote_path=remote_path)
        else:
            self.rsync_database(remote_location=remote_location, local_path=local_path, debug=debug)

    def symlink_database(self, local_path, remote_path):
        os.system(f"ln -s {remote_path} {local_path}")

    def rsync_database(self, remote_location, local_path, debug=False):
        verbose = ""
        if debug:
            verbose = "vv"
        os.system(f"rsync -hzc{verbose} --progress {remote_location} {local_path}")

    def force_download_all(self, debug=False):
        for database_name in self.remote_locations.keys():
            if debug:
                print(f"Downloading {self.remote_locations[database_name].split('/')[-1]}...")
            self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)

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

    def update_databases_by_date(self, max_days=31, debug=False):
        for database_name, local_path in self.local_paths.items():
            if self.check_date(local_path, max_days=max_days):
                if debug:
                    print(f"{database_name} not present or older than {max_days} days. Updating file...")
                self.download_database(remote_location=self.remote_locations[database_name], local_path=local_path, remote_path=self.docker_paths[database_name], debug=debug)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check_local", action='store_true')
    parser.add_argument("-f", "--force_download", action='store_true')
    parser.add_argument("-l", "--live", type=str, help="Live parameter for RTXConfiguration", default="Production", required=False)
    arguments = parser.parse_args()
    DBManager = ARAXDatabaseManager(arguments.live)
    if arguments.check_local:
        if not DBManager.check_versions(debug=True):
            print("All local versions are up to date")
    elif arguments.force_download:
        DBManager.force_download_all(debug=True)
    else:
        DBManager.update_databases(debug=True)

if __name__ == "__main__":
    main()