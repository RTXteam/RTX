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

        kg2c_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
        if not os.path.exists(kg2c_filepath):
            os.system(f"mkdir -p {kg2c_filepath}")

        kg2c_meta_kg_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources'])
        if not os.path.exists(kg2c_meta_kg_filepath):
            os.system(f"mkdir -p {kg2c_meta_kg_filepath}")

        fda_approved_drugs_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources'])
        if not os.path.exists(fda_approved_drugs_filepath):
            os.system(f"mkdir -p {fda_approved_drugs_filepath}")

        autocomplete_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'autocomplete'])
        if not os.path.exists(autocomplete_filepath):
            os.system(f"mkdir -p {autocomplete_filepath}")

        self.local_paths = {
            'cohd_database': f"{cohd_filepath}{os.path.sep}{self.RTXConfig.cohd_database_path.split('/')[-1]}",
            'graph_database': f"{pred_filepath}{os.path.sep}{self.RTXConfig.graph_database_path.split('/')[-1]}",
            'log_model': f"{pred_filepath}{os.path.sep}{self.RTXConfig.log_model_path.split('/')[-1]}",
            'curie_to_pmids': f"{ngd_filepath}{os.path.sep}{self.RTXConfig.curie_to_pmids_path.split('/')[-1]}",
            'node_synonymizer': f"{synonymizer_filepath}{os.path.sep}{self.RTXConfig.node_synonymizer_path.split('/')[-1]}",
            'dtd_prob': f"{pred_filepath}{os.path.sep}{self.RTXConfig.dtd_prob_path.split('/')[-1]}",
            'kg2c_sqlite': f"{kg2c_filepath}{os.path.sep}{self.RTXConfig.kg2c_sqlite_path.split('/')[-1]}",
            'kg2c_meta_kg': f"{kg2c_meta_kg_filepath}{os.path.sep}{self.RTXConfig.kg2c_meta_kg_path.split('/')[-1]}",
            'fda_approved_drugs': f"{fda_approved_drugs_filepath}{os.path.sep}{self.RTXConfig.fda_approved_drugs_path.split('/')[-1]}",
            'autocomplete': f"{autocomplete_filepath}{os.path.sep}{self.RTXConfig.autocomplete_path.split('/')[-1]}"
        }
        # user, host, and paths to databases on remote server
        self.remote_locations = {
            'cohd_database': f"{self.RTXConfig.cohd_database_username}@{self.RTXConfig.cohd_database_host}:{self.RTXConfig.cohd_database_path}",
            'graph_database': f"{self.RTXConfig.graph_database_username}@{self.RTXConfig.graph_database_host}:{self.RTXConfig.graph_database_path}",
            'log_model': f"{self.RTXConfig.log_model_username}@{self.RTXConfig.log_model_host}:{self.RTXConfig.log_model_path}",
            'curie_to_pmids': f"{self.RTXConfig.curie_to_pmids_username}@{self.RTXConfig.curie_to_pmids_host}:{self.RTXConfig.curie_to_pmids_path}",
            'node_synonymizer': f"{self.RTXConfig.node_synonymizer_username}@{self.RTXConfig.node_synonymizer_host}:{self.RTXConfig.node_synonymizer_path}",
            'dtd_prob': f"{self.RTXConfig.dtd_prob_username}@{self.RTXConfig.dtd_prob_host}:{self.RTXConfig.dtd_prob_path}",
            'kg2c_sqlite': f"{self.RTXConfig.kg2c_sqlite_username}@{self.RTXConfig.kg2c_sqlite_host}:{self.RTXConfig.kg2c_sqlite_path}",
            'kg2c_meta_kg': f"{self.RTXConfig.kg2c_meta_kg_username}@{self.RTXConfig.kg2c_meta_kg_host}:{self.RTXConfig.kg2c_meta_kg_path}",
            'fda_approved_drugs': f"{self.RTXConfig.fda_approved_drugs_username}@{self.RTXConfig.fda_approved_drugs_host}:{self.RTXConfig.fda_approved_drugs_path}",
            'autocomplete': f"{self.RTXConfig.autocomplete_username}@{self.RTXConfig.autocomplete_host}:{self.RTXConfig.autocomplete_path}"
        }
        # database locations if inside rtx1 docker container
        self.docker_paths = {
            'cohd_database': f"{self.RTXConfig.cohd_database_path.replace('/translator/','/mnt/')}",
            'graph_database': f"{self.RTXConfig.graph_database_path.replace('/translator/','/mnt/')}",
            'log_model': f"{self.RTXConfig.log_model_path.replace('/translator/','/mnt/')}",
            'curie_to_pmids': f"{self.RTXConfig.curie_to_pmids_path.replace('/translator/','/mnt/')}",
            'node_synonymizer': f"{self.RTXConfig.node_synonymizer_path.replace('/translator/','/mnt/')}",
            'dtd_prob': f"{self.RTXConfig.dtd_prob_path.replace('/translator/','/mnt/')}",
            'kg2c_sqlite': f"{self.RTXConfig.kg2c_sqlite_path.replace('/translator/', '/mnt/')}",
            'kg2c_meta_kg': f"{self.RTXConfig.kg2c_meta_kg_path.replace('/translator/', '/mnt/')}",
            'fda_approved_drugs': f"{self.RTXConfig.fda_approved_drugs_path.replace('/translator/', '/mnt/')}",
            'autocomplete': f"{self.RTXConfig.autocomplete_path.replace('/translator/', '/mnt/')}"
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
            },
            'kg2c_sqlite': {
                'path': self.local_paths['kg2c_sqlite'],
                'version': self.RTXConfig.kg2c_sqlite_version
            },
            'kg2c_meta_kg': {
                'path': self.local_paths['kg2c_meta_kg'],
                'version': self.RTXConfig.kg2c_meta_kg_version
            },
            'fda_approved_drugs': {
                'path': self.local_paths['fda_approved_drugs'],
                'version': self.RTXConfig.fda_approved_drugs_version
            },
            'autocomplete': {
                'path': self.local_paths['autocomplete'],
                'version': self.RTXConfig.autocomplete_version
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
            self.write_db_versions_file()
        else: # If database manager has never been run download all databases
            if debug:
                print("No local verson json file present. Downloading all databases...")
            if response is not None:
                response.debug(f"No local verson json file present. Downloading all databases...")
            self.force_download_all(debug=debug)
            self.write_db_versions_file()
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
        if remote_path is not None and os.path.exists(remote_path): # if on the server symlink instead of downloading
            self.symlink_database(local_path=local_path, remote_path=remote_path)
        else:
            self.rsync_database(remote_location=remote_location, local_path=local_path, debug=debug)

    def symlink_database(self, local_path, remote_path):
        os.system(f"ln -s {remote_path} {local_path}")

    def rsync_database(self, remote_location, local_path, debug=False):
        verbose = ""
        if debug:
            verbose = "vv"
        os.system(f"rsync -Lhzc{verbose} --progress {remote_location} {local_path}")

    def download_to_mnt(self, debug=False, skip_if_exists=False):
        for database_name in self.remote_locations.keys():
            database_dir = os.path.sep.join(self.docker_paths[database_name].split('/')[:-1])
            if debug:
                print(f"in download_to_mnt, for database {database_name}")
            if not os.path.exists(database_dir):
                if debug:
                    print(f"Creating directory {database_dir}...")
                os.system(f"mkdir -p {database_dir}")
            local_path = self.docker_paths[database_name]
            if not skip_if_exists or not os.path.exists(local_path):
                remote_location = self.remote_locations[database_name]
                print(f"Initiating download from location {remote_location}") if debug else None
                self.download_database(remote_location=remote_location, local_path=local_path, remote_path=None, debug=debug)
            else:
                print(f"  Database already exists, no need to download") if debug else None
                
    def force_download_all(self, debug=False):
        for database_name in self.remote_locations.keys():
            if debug:
                print(f"Downloading {self.remote_locations[database_name].split('/')[-1]}...")
            self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
    
    def download_slim(self, debug=False):
        for database_name in self.remote_locations.keys():
            if debug:
                print(f"Downloading slim {self.remote_locations[database_name].split('/')[-1]}...")
            if database_name in ["curie_to_pmids", "log_model", "kg2c_meta_kg", "fda_approved_drugs", "autocomplete"]:
                self.download_database(remote_location=self.remote_locations[database_name], local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
            elif database_name in ["node_synonymizer", "kg2c_sqlite", "cohd_database", "dtd_prob", "graph_database"]:
                self.download_database(remote_location=self.remote_locations[database_name].replace(".sqlite","_slim.sqlite").replace(".db","_slim.db"), local_path=self.local_paths[database_name], remote_path=self.docker_paths[database_name], debug=debug)
            else:
                if debug:
                    print("Making fake database...")
                os.system(f"touch {self.local_paths[database_name]}")
        #FW: Somewhat hacky solution to slow meta kg downloads from the KPs
        if debug:
                print(f"Downloading Meta KG data...")
        metakg_remote_location = f"{self.RTXConfig.node_synonymizer_username}@{self.RTXConfig.node_synonymizer_host}:/translator/data/orangeboard/production/RTX/code/ARAX/ARAXQuery/Expand/meta_map_v2.pickle"
        metakg_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Expand', 'meta_map_v2.pickle'])
        metakg_docker_path = "/mnt/data/orangeboard/production/RTX/code/ARAX/ARAXQuery/Expand/meta_map_v2.pickle"
        self.download_database(remote_location=metakg_remote_location, local_path=metakg_filepath, 
                                remote_path=metakg_docker_path, debug=debug)
        with open(versions_path,"w") as fid:
            if debug:
                print("Saving new version file...")
            json.dump(self.db_versions, fid)

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

    def write_db_versions_file(self, debug=False):
        print(f"saving new version file to {versions_path}") if debug else None
        with open(versions_path, "w") as fid:
            json.dump(self.db_versions, fid)

        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check_local", action='store_true')
    parser.add_argument("-f", "--force_download", action='store_true', help="Download all database without checking local versions")
    parser.add_argument("-m", "--mnt", action='store_true', help="Download all database files to /mnt")
    parser.add_argument("-l", "--live", type=str, help="Live parameter for RTXConfiguration", default="Production", required=False)
    parser.add_argument("-s", "--slim", action='store_true')
    parser.add_argument("-g", "--generate-versions-file", action='store_true', dest="generate_versions_file", required=False, help="just generate the db_versions.json file and do nothing else (ONLY USED IN TESTING/DEBUGGING)")
    parser.add_argument("-e", "--skip-if-exists", action='store_true', dest='skip_if_exists', required=False, help="for -m mode only, do not download a file if it already exists under /mnt/data/orangeboard/databases/KG2.X.X")
    arguments = parser.parse_args()
    DBManager = ARAXDatabaseManager(arguments.live)
    if arguments.check_local:
        if not DBManager.check_versions(debug=True):
            print("All local versions are up to date")
    elif arguments.slim:
        DBManager.download_slim(debug=True)
    elif arguments.force_download:
        DBManager.force_download_all(debug=True)
    elif arguments.mnt:
        DBManager.download_to_mnt(debug=True, skip_if_exists=arguments.skip_if_exists)
    elif arguments.generate_versions_file:
        DBManager.write_db_versions_file(debug=True)
    else:
        DBManager.update_databases(debug=True)

if __name__ == "__main__":
    main()
