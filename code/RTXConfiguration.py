#!/usr/bin/python3

# NOTE: this is a singleton class. Please do not mutate class variables.
# For more information, see RTXteam/RTX issue 2121.

import os
import datetime
import json
import time
import timeit
import re
from typing import Optional

import yaml
from pygit2 import Repository, discover_repository
import pprint

DEBUG = False

class RTXConfiguration:

    _GET_FILE_CMD = "scp araxconfig@araxconfig.rtx.ai:config_secrets.json "

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._private_init()
        return cls._instance

    # ### Constructor
    def _private_init(self):
        if DEBUG:
            print("DEBUG: in private_init")
        assert self._instance is not None
        if self._initialized:
            return

        self._initialized = True

        t0 = timeit.default_timer()
        file_dir = os.path.dirname(os.path.abspath(__file__))

        # Determine current ARAX and TRAPI versions
        # YAML is super slow to ready, so refresh a JSON if necessary or read the JSON, which is much faster
        openapi_yaml_path = f"{file_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
        openapi_json_path = f"{file_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.json"
        if not os.path.exists(openapi_json_path) or os.path.getmtime(openapi_yaml_path) > os.path.getmtime(openapi_json_path):
            if DEBUG:
                t1 = timeit.default_timer()
                print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. OpenAPI JSON file is missing or stale")
            with open(openapi_yaml_path) as api_file:
                openapi_configuration = yaml.safe_load(api_file)
            if DEBUG:
                t1 = timeit.default_timer()
                print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Read OpenAPI YAML file")
            with open(openapi_json_path, 'w') as api_file:
                json.dump(openapi_configuration, api_file, default=str)
            if DEBUG:
                t1 = timeit.default_timer()
                print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Created OpenAPI JSON file")
        else:
            with open(openapi_json_path) as api_file:
                openapi_configuration = json.load(api_file)
            if DEBUG:
                t1 = timeit.default_timer()
                print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Read OpenAPI JSON file")

        self.arax_version = openapi_configuration["info"]["version"]
        self.trapi_version = openapi_configuration["info"]["x-trapi"]["version"]
        first_two_trapi_version_nums = self.trapi_version.split(".")[:2]
        self.trapi_major_version = ".".join(first_two_trapi_version_nums)
        self.version = f"ARAX {self.arax_version}"  # Not sure exactly what this is used for; legacy?

        # Grab instance/domain name info, if available
        self.instance_name = '??'
        match = re.match(r'/mnt/data/orangeboard/(.+)/RTX/code', file_dir)
        if match:
            self.instance_name = match.group(1)
        if self.instance_name == 'production':
            self.instance_name = 'ARAX'

        try:
            with open(f"{file_dir}/config.domain") as infile:
                for line in infile:
                    self.domain = line.strip()
        except:
            self.domain = '??'
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Read {file_dir}/config.domain")

        # Determine the branch we're running in
        repo_path = discover_repository(file_dir)
        try:
            repo = Repository(repo_path)
            self.current_branch_name = repo.head.name.split("/")[-1]
        except Exception:
            # TODO: Figure out why Docker container doesn't like this Git branch determination method
            # Ok to skip branch name here for now since domain name can be used instead in such cases
            self.current_branch_name = None
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Determined repo information from {repo_path}")

        # Determine our maturity
        maturity_override_value = self._read_override_file(f"{file_dir}/maturity_override.txt")
        if maturity_override_value:
            self.maturity = maturity_override_value
        else:
            # Otherwise we'll dynamically determine our maturity based on instance/domain name and/or branch
            if self.domain in ["arax.ci.transltr.io", "kg2.ci.transltr.io"]:
                self.maturity = "staging"
            elif self.domain in ["arax.test.transltr.io", "kg2.test.transltr.io"] or self.current_branch_name == "itrb-test":
                self.maturity = "testing"
            elif self.domain in ["arax.transltr.io", "kg2.transltr.io"] or self.current_branch_name == "production":
                self.maturity = "production"
            elif self.domain == "arax.ncats.io":
                if self.instance_name in ["ARAX", "kg2"] or self.current_branch_name == "production":
                    self.maturity = "production"
                else:
                    self.maturity = "development"
            else:
                self.maturity = "development"
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Determined maturity")

        # Determine if this is an ITRB instance or our CICD instance
        self.is_itrb_instance = "transltr.io" in self.domain  # Hacky, but works

        config_secrets_file_path = os.path.dirname(os.path.abspath(__file__)) + '/config_secrets.json'
        config_dbs_file_path = os.path.dirname(os.path.abspath(__file__)) + '/config_dbs.json'
        config_secrets_local_file_path = os.path.dirname(os.path.abspath(__file__)) + '/config_secrets_local.json'
        
        # Setting Jaeger Configs
        if self.is_itrb_instance:
            self.jaeger_port = 6831
            self.jaeger_endpoint = "jaeger-otel-agent.sri"
            self.telemetry_enabled = True
        else:
            self.jaeger_port = 6831
            self.jaeger_endpoint = "jaeger.rtx.ai"
            self.telemetry_enabled = True
        # Download the latest copy of config_secrets.json as appropriate (or override by local file, if present)
        if os.path.exists(config_secrets_local_file_path):
            config_secrets_file_path = config_secrets_local_file_path
        elif not os.path.exists(config_secrets_file_path):
            # scp the file
            os.system(RTXConfiguration._GET_FILE_CMD + config_secrets_file_path)
        else:
            now_time = datetime.datetime.now()
            modified_time = time.localtime(os.stat(config_secrets_file_path).st_mtime)
            modified_time = datetime.datetime(*modified_time[:6])
            if (now_time - modified_time).days > 0:
                # scp the file
                os.system(RTXConfiguration._GET_FILE_CMD + config_secrets_file_path)

        # Load the contents of the two config files (config_dbs.json lives in the repo; no need to download)
        with open(config_secrets_file_path, 'r') as config_secrets_file:
            self.config_secrets = json.load(config_secrets_file)
        with open(config_dbs_file_path, 'r') as config_dbs_file:
            self.config_dbs = json.load(config_dbs_file)
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Got secrets")

        # AG: Not sure exactly what this is doing?
        self.is_production_server = False
        if ( ( 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == '6d6766e08a31' ) or
            ( 'PWD' in os.environ and 'mnt/data/orangeboard' in os.environ['PWD'] ) ):
            self.is_production_server = True

        # Set database file paths
        self.db_host = "arax-databases.rtx.ai"
        self.db_username = "rtxconfig"
        database_downloads = self.config_dbs["database_downloads"]
        self.cohd_database_path = database_downloads["cohd_database"]
        self.cohd_database_version = self.cohd_database_path.split('/')[-1].split('_v')[-1].replace('.db', '')
        self.curie_to_pmids_path = database_downloads["curie_to_pmids"]
        self.curie_to_pmids_version = self.curie_to_pmids_path.split('/')[-1].split('_v')[-1].replace('.sqlite', '')
        self.node_synonymizer_path = database_downloads["node_synonymizer"]
        self.node_synonymizer_version = self.node_synonymizer_path.split('/')[-1].split('_v')[-1].replace('.sqlite', '')
        self.kg2c_sqlite_path = database_downloads["kg2c_sqlite"]
        self.kg2c_sqlite_version = self.kg2c_sqlite_path.split('/')[-1].split('_v')[-1].replace('.sqlite', '')
        self.kg2c_meta_kg_path = database_downloads["kg2c_meta_kg"]
        self.kg2c_meta_kg_version = self.kg2c_meta_kg_path.split('/')[-1].split('_v')[-1].replace('.json', '')
        self.fda_approved_drugs_path = database_downloads["fda_approved_drugs"]
        self.fda_approved_drugs_version = self.fda_approved_drugs_path.split('/')[-1].split('_v')[-1].replace('.pickle', '')
        self.autocomplete_path = database_downloads["autocomplete"]
        self.autocomplete_version = self.autocomplete_path.split('/')[-1].split('_v')[-1].replace('.sqlite', '')
        self.explainable_dtd_db_path = database_downloads["explainable_dtd_db"]
        self.explainable_dtd_db_version = self.explainable_dtd_db_path.split('/')[-1].split('_v')[-1].replace('.db', '')
        self.xcrg_embeddings_path = database_downloads["xcrg_embeddings"]
        self.xcrg_embeddings_version = self.xcrg_embeddings_path.split('/')[-1].split('_v')[-1].replace('.npz', '')
        self.xcrg_increase_model_path = database_downloads["xcrg_increase_model"]
        self.xcrg_increase_model_version = self.xcrg_embeddings_path.split('/')[-1].split('_v')[-1].replace('.pt', '')
        self.xcrg_decrease_model_path = database_downloads["xcrg_decrease_model"]
        self.xcrg_decrease_model_version = self.xcrg_embeddings_path.split('/')[-1].split('_v')[-1].replace('.pt', '')

        # Set up mysql feedback
        self.mysql_feedback_host = self.config_secrets["mysql_feedback"]["host"]
        self.mysql_feedback_port = self.config_secrets["mysql_feedback"]["port"]
        self.mysql_feedback_username = self.config_secrets["mysql_feedback"]["username"]
        self.mysql_feedback_password = self.config_secrets["mysql_feedback"]["password"]

        # Set up correct Plover URL (since it's not registered in SmartAPI)
        plover_url_override_value = self._read_override_file(f"{file_dir}/plover_url_override.txt")
        if plover_url_override_value:
            self.plover_url = plover_url_override_value
        elif self.maturity in {"production", "prod"}:
            self.plover_url = self.config_dbs["plover"]["prod"]
        elif self.maturity in {"testing", "test"}:
            self.plover_url = self.config_dbs["plover"]["test"]
        else:  # Includes staging, development
            self.plover_url = self.config_dbs["plover"]["dev"]
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Read override file {file_dir}/plover_url_override.txt")

        # Set KG2 url if an override was provided
        kg2_url_override_value = self._read_override_file(f"{file_dir}/kg2_url_override.txt")
        if kg2_url_override_value:
            self.rtx_kg2_url = kg2_url_override_value
        else:
            self.rtx_kg2_url = None

        # Default to KG2c neo4j
        self.neo4j_kg2 = "KG2c"
        if DEBUG:
            t1 = timeit.default_timer()
            print(f"Elapsed time: {(t1-t0)*1000:.2f} ms. Done creating RTXConfiguration object")


    @staticmethod
    def _read_override_file(file_path: str) -> Optional[str]:
        if os.path.exists(file_path):
            with open(file_path, 'r') as override_file:
                lines = override_file.readlines()
                if not lines or not lines[0]:
                    raise ValueError(f"{file_path} exists but does not contain anything! "
                                     f"It should be a single-line file containing the override value.")
                else:
                    return lines[0].strip()
        else:
            return None


    def get_neo4j_info(self, kg2_type: str) -> dict:
        if kg2_type not in self.config_dbs["neo4j"].keys():
            return {'bolt': None,
                    'database': None,
                    'username': None,
                    'password': None}
        else:
            neo4j_instance = self.config_dbs["neo4j"][kg2_type]
            config_secrets = self.config_secrets
            return {'bolt': f"bolt://{neo4j_instance}:7687",
                    'database': f"{neo4j_instance}:7474/db/data",
                    'username': config_secrets["neo4j"][kg2_type]["username"],
                    'password': config_secrets["neo4j"][kg2_type]["password"]}


def main():
    t0 = timeit.default_timer()
    rtxConfig = RTXConfiguration()
    t1 = timeit.default_timer()
    print("RTX Version string: " + rtxConfig.version)
    kg2_info = rtxConfig.get_neo4j_info("KG2c")
    pprint.pprint(kg2_info)
    print("plover url: %s" % rtxConfig.plover_url)
    print("rtx-kg2 url: %s" % rtxConfig.rtx_kg2_url)
    print("mysql feedback host: %s" % rtxConfig.mysql_feedback_host)
    print("mysql feedback port: %s" % rtxConfig.mysql_feedback_port)
    print("mysql feedback username: %s" % rtxConfig.mysql_feedback_username)
    print("mysql feedback password: %s" % rtxConfig.mysql_feedback_password)
    print(f"maturity: {rtxConfig.maturity}")
    print(f"current branch: {rtxConfig.current_branch_name}")
    print(f"is_itrb_instance: {rtxConfig.is_itrb_instance}")
    print(f"Total elapsed time: {(t1-t0)*1000:.2f} ms")
    t2 = timeit.default_timer()
    rtxConfig = RTXConfiguration()
    t3 = timeit.default_timer()
    print(rtxConfig.version)
    print(f"Total elapsed time: {(t3-t2)*1000:.2f} ms")


if __name__ == "__main__":
    main()
