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
    def __init__(self):
        self.RTXConfig = RTXConfiguration()

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

        explainable_dtd_db_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
        if not os.path.exists(explainable_dtd_db_filepath):
            os.system(f"mkdir -p {explainable_dtd_db_filepath}")

        xcrg_embeddings_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data', 'xCRG_data'])
        if not os.path.exists(xcrg_embeddings_filepath):
            os.system(f"mkdir -p {xcrg_embeddings_filepath}")        

        xcrg_increase_model_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data', 'xCRG_data'])
        if not os.path.exists(xcrg_increase_model_filepath):
            os.system(f"mkdir -p {xcrg_increase_model_filepath}")       

        xcrg_decrease_model_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data', 'xCRG_data'])
        if not os.path.exists(xcrg_decrease_model_filepath):
            os.system(f"mkdir -p {xcrg_decrease_model_filepath}")


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
            'autocomplete': f"{autocomplete_filepath}{os.path.sep}{self.RTXConfig.autocomplete_path.split('/')[-1]}",
            'explainable_dtd_db': f"{explainable_dtd_db_filepath}{os.path.sep}{self.RTXConfig.explainable_dtd_db_path.split('/')[-1]}",
            'xcrg_embeddings': f"{xcrg_embeddings_filepath}{os.path.sep}{self.RTXConfig.xcrg_embeddings_path.split('/')[-1]}",
            "xcrg_increase_model": f"{xcrg_increase_model_filepath}{os.path.sep}{self.RTXConfig.xcrg_increase_model_path.split('/')[-1]}",
            "xcrg_decrease_model": f"{xcrg_decrease_model_filepath}{os.path.sep}{self.RTXConfig.xcrg_decrease_model_path.split('/')[-1]}"
        }

        # Stores the "/KG2.X.Y/some_database_v1.0_KG2.X.Y.sqlite" portion of each database's path
        # This portion of the db path is the same on arax-databases.rtx.ai as it is on the ARAX docker instance
        self.database_subpaths = {
            'cohd_database': self.get_database_subpath(self.RTXConfig.cohd_database_path),
            'graph_database': self.get_database_subpath(self.RTXConfig.graph_database_path),
            'log_model': self.get_database_subpath(self.RTXConfig.log_model_path),
            'curie_to_pmids': self.get_database_subpath(self.RTXConfig.curie_to_pmids_path),
            'node_synonymizer': self.get_database_subpath(self.RTXConfig.node_synonymizer_path),
            'dtd_prob': self.get_database_subpath(self.RTXConfig.dtd_prob_path),
            'kg2c_sqlite': self.get_database_subpath(self.RTXConfig.kg2c_sqlite_path),
            'kg2c_meta_kg': self.get_database_subpath(self.RTXConfig.kg2c_meta_kg_path),
            'fda_approved_drugs': self.get_database_subpath(self.RTXConfig.fda_approved_drugs_path),
            'autocomplete': self.get_database_subpath(self.RTXConfig.autocomplete_path),
            'explainable_dtd_db': self.get_database_subpath(self.RTXConfig.explainable_dtd_db_path),
            'xcrg_embeddings': self.get_database_subpath(self.RTXConfig.xcrg_embeddings_path),
            "xcrg_increase_model": self.get_database_subpath(self.RTXConfig.xcrg_increase_model_path),
            "xcrg_decrease_model": self.get_database_subpath(self.RTXConfig.xcrg_decrease_model_path)

        }
        # user, host, and paths to databases on remote server dbs are downloaded from (arax-databases.rtx.ai)
        self.databases_server_dir_path = '/home/rtxconfig'
        self.remote_locations = {
            'cohd_database': self.get_remote_location('cohd_database'),
            'graph_database': self.get_remote_location('graph_database'),
            'log_model': self.get_remote_location('log_model'),
            'curie_to_pmids': self.get_remote_location('curie_to_pmids'),
            'node_synonymizer': self.get_remote_location('node_synonymizer'),
            'dtd_prob': self.get_remote_location('dtd_prob'),
            'kg2c_sqlite': self.get_remote_location('kg2c_sqlite'),
            'kg2c_meta_kg': self.get_remote_location('kg2c_meta_kg'),
            'fda_approved_drugs': self.get_remote_location('fda_approved_drugs'),
            'autocomplete': self.get_remote_location('autocomplete'),
            'explainable_dtd_db': self.get_remote_location('explainable_dtd_db'),
            'xcrg_embeddings': self.get_remote_location('xcrg_embeddings'),
            'xcrg_increase_model': self.get_remote_location('xcrg_increase_model'),
            'xcrg_decrease_model': self.get_remote_location('xcrg_decrease_model')    
        }
        # database locations if inside rtx1 docker container
        self.docker_databases_dir_path = '/mnt/data/orangeboard/databases'
        self.docker_central_paths = {
            'cohd_database': self.get_docker_path('cohd_database'),
            'graph_database': self.get_docker_path('graph_database'),
            'log_model': self.get_docker_path('log_model'),
            'curie_to_pmids': self.get_docker_path('curie_to_pmids'),
            'node_synonymizer': self.get_docker_path('node_synonymizer'),
            'dtd_prob': self.get_docker_path('dtd_prob'),
            'kg2c_sqlite': self.get_docker_path('kg2c_sqlite'),
            'kg2c_meta_kg': self.get_docker_path('kg2c_meta_kg'),
            'fda_approved_drugs': self.get_docker_path('fda_approved_drugs'),
            'autocomplete': self.get_docker_path('autocomplete'),
            'explainable_dtd_db': self.get_docker_path('explainable_dtd_db'),
            'xcrg_embeddings': self.get_docker_path('xcrg_embeddings'),
            'xcrg_increase_model': self.get_docker_path('xcrg_increase_model'),
            'xcrg_decrease_model': self.get_docker_path('xcrg_decrease_model') 
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
            },
            'explainable_dtd_db': {
                'path': self.local_paths['explainable_dtd_db'],
                'version': self.RTXConfig.explainable_dtd_db_version
            },
            'xcrg_embeddings': {
                'path': self.local_paths['xcrg_embeddings'],
                'version': self.RTXConfig.xcrg_embeddings_version
            },
            'xcrg_increase_model': {
                'path': self.local_paths['xcrg_increase_model'],
                'version': self.RTXConfig.xcrg_increase_model_version
            },
            'xcrg_decrease_model': {
                'path': self.local_paths['xcrg_decrease_model'],
                'version': self.RTXConfig.xcrg_decrease_model_version
            }
        }

    def update_databases(self, debug = False, response = None):
        # First ensure we have a db versions file if we're in a docker container (since host has dbs predownloaded)
        if os.path.exists(self.docker_databases_dir_path) and not os.path.exists(versions_path):
            self.write_db_versions_file(debug=True)

        # Then ensure each database/symlink is up to date
        if os.path.exists(versions_path):
            with open(versions_path, "r") as fid:
                local_versions = json.load(fid)

            # Download databases to a persistent central location if this is a docker instance (like arax.ncats.io)
            if os.path.exists(self.docker_databases_dir_path):
                print(f"Downloading any missing databases from arax-databases.rtx.ai to {self.docker_databases_dir_path}")
                self.download_to_mnt(debug=debug, skip_if_exists=True, remove_unused=False)

            # Check that each database exists locally (or a symlink to it does, in the case of a docker host machine)
            for database_name, local_path in self.local_paths.items(): # iterate through all databases
                if database_name not in local_versions: # if database is not present locally
                    if debug:
                        print(f"{database_name} not present locally, downloading or symlinking now...")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name],
                                           local_destination_path=self.local_paths[database_name],
                                           local_symlink_target_path=self.docker_central_paths[database_name],
                                           debug=debug)
                elif local_versions[database_name]['version'] != self.db_versions[database_name]['version']: # If database is present but wrong version
                    if debug:
                        print(f"{database_name} has a local version, '{local_versions[database_name]['version']}', which does not match the remote version, '{self.db_versions[database_name]['version']}'.")
                        print("downloading remote version...")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name],
                                           local_destination_path=self.local_paths[database_name],
                                           local_symlink_target_path=self.docker_central_paths[database_name],
                                           debug=debug)
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
                        print(f"{database_name} not present locally, downloading or symlinking now......")
                    if response is not None:
                        response.debug(f"Updating the local file for {database_name}...")
                    self.download_database(remote_location=self.remote_locations[database_name], local_destination_path=self.local_paths[database_name], local_symlink_target_path=self.docker_central_paths[database_name], debug=debug)
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

    @staticmethod
    def get_database_subpath(path: str) -> str:
        path_chunks = path.split("/")
        last_two_chunks = path_chunks[-2:]
        return "/".join(last_two_chunks)

    def get_remote_location(self, database_shortname: str) -> str:
        database_subpath = self.database_subpaths[database_shortname]
        return f"{self.RTXConfig.db_username}@{self.RTXConfig.db_host}:{self.databases_server_dir_path}/{database_subpath}"

    def get_docker_path(self, database_shortname: str) -> str:
        database_subpath = self.database_subpaths[database_shortname]
        return f"{self.docker_databases_dir_path}/{database_subpath}"

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

    def download_database(self, remote_location, local_destination_path, local_symlink_target_path, debug=False):
        if local_symlink_target_path is not None and os.path.exists(local_symlink_target_path): # if on the server symlink instead of downloading
            self.symlink_database(symlink_path=local_destination_path, target_path=local_symlink_target_path)
        else:
            self.rsync_database(remote_location=remote_location, local_path=local_destination_path, debug=debug)

    def symlink_database(self, symlink_path, target_path):
        os.system(f"ln -s {target_path} {symlink_path}")

    def rsync_database(self, remote_location, local_path, debug=False):
        verbose = ""
        if debug:
            verbose = "vv"
        os.system(f"rsync -Lhzc{verbose} --progress {remote_location} {local_path}")

    def download_to_mnt(self, debug=False, skip_if_exists=False, remove_unused=False):
        """
        This method downloads databases to the docker host machine in a central location.
        """
        if remove_unused:  # Do this first to ensure we don't run out of space on the server
            self.remove_unused_mnt_dbs()
        for database_name in self.remote_locations.keys():
            database_dir = os.path.sep.join(self.docker_central_paths[database_name].split('/')[:-1])
            if debug:
                print(f"On database {database_name} in download_to_mnt()")
            if not os.path.exists(database_dir):
                if debug:
                    print(f"Creating directory {database_dir}...")
                os.system(f"mkdir -p {database_dir}")
            docker_host_local_path = self.docker_central_paths[database_name]
            if not skip_if_exists or not os.path.exists(docker_host_local_path):
                remote_location = self.remote_locations[database_name]
                if debug:
                    print(f"Initiating download from location {remote_location}; "
                          f"saving to {docker_host_local_path}")
                self.download_database(remote_location=remote_location,
                                       local_destination_path=docker_host_local_path,
                                       local_symlink_target_path=None,
                                       debug=debug)
            else:
                print(f"  Database already exists, no need to download") if debug else None
                
    def force_download_all(self, debug=False):
        for database_name in self.remote_locations.keys():
            if debug:
                print(f"Downloading {self.remote_locations[database_name].split('/')[-1]}...")
            self.download_database(remote_location=self.remote_locations[database_name], local_destination_path=self.local_paths[database_name], local_symlink_target_path=self.docker_central_paths[database_name], debug=debug)

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
                self.download_database(remote_location=self.remote_locations[database_name], local_destination_path=local_path, local_symlink_target_path=self.docker_central_paths[database_name], debug=debug)

    def write_db_versions_file(self, debug=False):
        print(f"saving new version file to {versions_path}") if debug else None
        with open(versions_path, "w") as fid:
            json.dump(self.db_versions, fid)

    def remove_unused_mnt_dbs(self):
        # Grab our current database names (used in config_dbs.json)
        db_names = {db_info["path"].split("/")[-1] for db_info in self.db_versions.values()}
        # Loop through all dbs within the /mnt/ databases directory and delete any not in db_names
        databases_dir_path = self.docker_databases_dir_path
        if os.path.exists(databases_dir_path):
            kg2_dir_names = [dir_name for dir_name in os.listdir(databases_dir_path)
                             if dir_name.upper().startswith("KG2") and os.path.isdir(f"{databases_dir_path}/{dir_name}")]
            for kg2_dir_name in kg2_dir_names:
                kg2_dir_path = f"{databases_dir_path}/{kg2_dir_name}"
                for db_file_name in os.listdir(kg2_dir_path):
                    db_file_path = f"{kg2_dir_path}/{db_file_name}"
                    if os.path.isfile(db_file_path) and db_file_name not in db_names:
                        print(f"Removing unused db file {db_file_path}")
                        os.system(f"rm -f {db_file_path}")

        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check_local", action='store_true')
    parser.add_argument("-f", "--force_download", action='store_true', help="Download all database without checking local versions")
    parser.add_argument("-m", "--mnt", action='store_true', help="Download all database files to /mnt databases directory")
    parser.add_argument("-g", "--generate-versions-file", action='store_true', dest="generate_versions_file", required=False, help="just generate the db_versions.json file and do nothing else (ONLY USED IN TESTING/DEBUGGING)")
    parser.add_argument("-e", "--skip-if-exists", action='store_true', dest='skip_if_exists', required=False, help="for -m mode only, do not download a file if it already exists under /mnt databases directory")
    parser.add_argument("-r", "--remove_unused", action='store_true', dest='remove_unused', required=False, help="for -m mode only, remove database files under /mnt databases directory that are NOT used in config_dbs.json")

    arguments = parser.parse_args()
    DBManager = ARAXDatabaseManager()

    print(f"Local paths:")
    for db_name, path in DBManager.local_paths.items():
        print(f"  {db_name}: {path}")
    print(f"Remote locations:")
    for db_name, path in DBManager.remote_locations.items():
        print(f"  {db_name}: {path}")
    print(f"Docker paths:")
    for db_name, path in DBManager.docker_central_paths.items():
        print(f"  {db_name}: {path}")

    if arguments.check_local:
        if not DBManager.check_versions(debug=True):
            print("All local versions are up to date")
    elif arguments.force_download:
        DBManager.force_download_all(debug=True)
    elif arguments.mnt:
        DBManager.download_to_mnt(debug=True, skip_if_exists=arguments.skip_if_exists, remove_unused=arguments.remove_unused)
    elif arguments.generate_versions_file:
        DBManager.write_db_versions_file(debug=True)
    else:
        DBManager.update_databases(debug=True)


if __name__ == "__main__":
    main()
