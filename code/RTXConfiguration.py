#!/usr/bin/python3

import os
import datetime
import json
import time


class RTXConfiguration:

    _GET_FILE_CMD = "scp araxconfig@araxconfig.rtx.ai:configv2.json "

    # ### Constructor
    def __init__(self):
        self.version = "ARAX 0.7.0"

        file_path = os.path.dirname(os.path.abspath(__file__)) + '/configv2.json'
        local_path = os.path.dirname(os.path.abspath(__file__)) + '/config_local.json'

        if os.path.exists(local_path):
            file_path = local_path
        elif not os.path.exists(file_path):
            # scp the file
            os.system(RTXConfiguration._GET_FILE_CMD + file_path)
        else:
            now_time = datetime.datetime.now()
            modified_time = time.localtime(os.stat(file_path).st_mtime)
            modified_time = datetime.datetime(*modified_time[:6])
            if (now_time - modified_time).days > 0:
                # scp the file
                os.system(RTXConfiguration._GET_FILE_CMD + file_path)

        f = open(file_path, 'r')
        config_data = f.read()
        f.close()
        self.config = json.loads(config_data)

        # This is the flag/property to switch between the two containers
        self.live = "Production"
        # self.live = "KG2"
        # self.live = "rtxdev"
        # self.live = "staging"
        # self.live = "local"

        self.is_production_server = False
        if ( ( 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == '6d6766e08a31' ) or
            ( 'PWD' in os.environ and 'mnt/data/orangeboard' in os.environ['PWD'] ) ):
            self.is_production_server = True


    # ### Define attribute version
    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, version: str):
        self._version = version

    @property
    def live(self) -> str:
        return self._live

    @live.setter
    def live(self, live: str):
        self._live = live

        if self.live not in self.config["Contextual"].keys():
            self.neo4j_bolt = None
            self.neo4j_database = None
            self.neo4j_username = None
            self.neo4j_password = None
        else:
            self.neo4j_bolt = self.config["Contextual"][self.live]["neo4j"]["bolt"]
            self.neo4j_database = self.config["Contextual"][self.live]["neo4j"]["database"]
            self.neo4j_username = self.config["Contextual"][self.live]["neo4j"]["username"]
            self.neo4j_password = self.config["Contextual"][self.live]["neo4j"]["password"]
        
        self.cohd_database_host = self.config["Global"]["cohd_database"]["host"]
        self.cohd_database_username = self.config["Global"]["cohd_database"]["username"]
        self.cohd_database_path = self.config["Contextual"][self.live]["cohd_database"]["path"]
        self.cohd_database_version = self.config["Contextual"][self.live]["cohd_database"]["path"].split('/')[-1].split('_v')[-1].replace('.db','')

        self.graph_database_host = self.config["Global"]["graph_database"]["host"]
        self.graph_database_username = self.config["Global"]["graph_database"]["username"]
        self.graph_database_path = self.config["Contextual"][self.live]["graph_database"]["path"]
        self.graph_database_version = self.config["Contextual"][self.live]["graph_database"]["path"].split('/')[-1].split('_v')[-1].replace('.sqlite','')

        self.log_model_host = self.config["Global"]["log_model"]["host"]
        self.log_model_username = self.config["Global"]["log_model"]["username"]
        self.log_model_path = self.config["Contextual"][self.live]["log_model"]["path"]
        self.log_model_version = self.config["Contextual"][self.live]["log_model"]["path"].split('/')[-1].split('_v')[-1].replace('.pkl','')

        self.curie_to_pmids_host = self.config["Global"]["curie_to_pmids"]["host"]
        self.curie_to_pmids_username = self.config["Global"]["curie_to_pmids"]["username"]
        self.curie_to_pmids_path = self.config["Contextual"][self.live]["curie_to_pmids"]["path"]
        self.curie_to_pmids_version = self.config["Contextual"][self.live]["curie_to_pmids"]["path"].split('/')[-1].split('_v')[-1].replace('.sqlite','')

        self.node_synonymizer_host = self.config["Global"]["node_synonymizer"]["host"]
        self.node_synonymizer_username = self.config["Global"]["node_synonymizer"]["username"]
        self.node_synonymizer_path = self.config["Contextual"][self.live]["node_synonymizer"]["path"]
        self.node_synonymizer_version = self.config["Contextual"][self.live]["node_synonymizer"]["path"].split('/')[-1].split('_v')[-1].replace('.sqlite','')

        self.dtd_prob_host = self.config["Global"]["dtd_prob"]["host"]
        self.dtd_prob_username = self.config["Global"]["dtd_prob"]["username"]
        self.dtd_prob_path = self.config["Contextual"][self.live]["dtd_prob"]["path"]
        self.dtd_prob_version = self.config["Contextual"][self.live]["dtd_prob"]["path"].split('/')[-1].split('_v')[-1].replace('.db','')

        self.mysql_feedback_host = self.config["Global"]["mysql_feedback"]["host"]
        self.mysql_feedback_port = self.config["Global"]["mysql_feedback"]["port"]
        self.mysql_feedback_username = self.config["Global"]["mysql_feedback"]["username"]
        self.mysql_feedback_password = self.config["Global"]["mysql_feedback"]["password"]
        self.mysql_semmeddb_host = self.config["Global"]["mysql_semmeddb"]["host"]
        self.mysql_semmeddb_port = self.config["Global"]["mysql_semmeddb"]["port"]
        self.mysql_semmeddb_username = self.config["Global"]["mysql_semmeddb"]["username"]
        self.mysql_semmeddb_password = self.config["Global"]["mysql_semmeddb"]["password"]
        self.mysql_umls_host = self.config["Global"]["mysql_umls"]["host"]
        self.mysql_umls_port = self.config["Global"]["mysql_umls"]["port"]
        self.mysql_umls_username = self.config["Global"]["mysql_umls"]["username"]
        self.mysql_umls_password = self.config["Global"]["mysql_umls"]["password"]


        # if self.live == "Production":
        #     self.bolt = "bolt://arax.ncats.io:7687"
        #     self.database = "arax.ncats.io:7474/db/data"
        #
        # elif self.live == "KG2":
        #     self.bolt = "bolt://arax.ncats.io:7787"
        #     self.database = "arax.ncats.io:7574/db/data"
        #
        # elif self.live == "rtxdev":
        #     self.bolt = "bolt://rtxdev.saramsey.org:7887"
        #     self.database = "rtxdev.saramsey.org:7674/db/data"
        #
        # elif self.live == "staging":
        #     self.bolt = "bolt://steveneo4j.saramsey.org:7687"
        #     self.database = "steveneo4j.saramsey.org:7474/db/data"
        #
        # elif self.live == "local":
        #     self.bolt = "bolt://localhost:7687"
        #     self.database = "localhost:7474/db/data"

        # else:
        #     self.bolt = None
        #     self.database = None

    @property
    def neo4j_bolt(self) -> str:
        return self._neo4j_bolt

    @neo4j_bolt.setter
    def neo4j_bolt(self, bolt: str):
        self._neo4j_bolt = bolt

    @property
    def neo4j_database(self) -> str:
        return self._neo4j_database

    @neo4j_database.setter
    def neo4j_database(self, database: str):
        self._neo4j_database = database

    @property
    def neo4j_username(self) -> str:
        return self._neo4j_username

    @neo4j_username.setter
    def neo4j_username(self, username: str):
        self._neo4j_username = username

    @property
    def neo4j_password(self) -> str:
        return self._neo4j_password

    @neo4j_password.setter
    def neo4j_password(self, password: str):
        self._neo4j_password = password

    @property
    def mysql_feedback_host(self) -> str:
        return self._mysql_feedback_host

    @mysql_feedback_host.setter
    def mysql_feedback_host(self, host: str):
        self._mysql_feedback_host = host

    @property
    def mysql_feedback_port(self) -> str:
        return self._mysql_feedback_port

    @mysql_feedback_port.setter
    def mysql_feedback_port(self, port: str):
        self._mysql_feedback_port = port

    @property
    def mysql_feedback_username(self) -> str:
        return self._mysql_feedback_username

    @mysql_feedback_username.setter
    def mysql_feedback_username(self, username: str):
        self._mysql_feedback_username = username

    @property
    def mysql_feedback_password(self) -> str:
        return self._mysql_feedback_password

    @mysql_feedback_password.setter
    def mysql_feedback_password(self, password: str):
        self._mysql_feedback_password = password

    @property
    def mysql_semmeddb_host(self) -> str:
        return self._mysql_semmeddb_host

    @mysql_semmeddb_host.setter
    def mysql_semmeddb_host(self, host: str):
        self._mysql_semmeddb_host = host

    @property
    def mysql_semmeddb_port(self) -> str:
        return self._mysql_semmeddb_port

    @mysql_semmeddb_port.setter
    def mysql_semmeddb_port(self, port: str):
        self._mysql_semmeddb_port = port

    @property
    def mysql_semmeddb_username(self) -> str:
        return self._mysql_semmeddb_username

    @mysql_semmeddb_username.setter
    def mysql_semmeddb_username(self, username: str):
        self._mysql_semmeddb_username = username

    @property
    def mysql_semmeddb_password(self) -> str:
        return self._mysql_semmeddb_password

    @mysql_semmeddb_password.setter
    def mysql_semmeddb_password(self, password: str):
        self._mysql_semmeddb_password = password

    @property
    def mysql_umls_host(self) -> str:
        return self._mysql_umls_host

    @mysql_umls_host.setter
    def mysql_umls_host(self, host: str):
        self._mysql_umls_host = host

    @property
    def mysql_umls_port(self) -> str:
        return self._mysql_umls_port

    @mysql_umls_port.setter
    def mysql_umls_port(self, port: str):
        self._mysql_umls_port = port

    @property
    def mysql_umls_username(self) -> str:
        return self._mysql_umls_username

    @mysql_umls_username.setter
    def mysql_umls_username(self, username: str):
        self._mysql_umls_username = username

    @property
    def mysql_umls_password(self) -> str:
        return self._mysql_umls_password

    @mysql_umls_password.setter
    def mysql_umls_password(self, password: str):
        self._mysql_umls_password = password


def main():
    rtxConfig = RTXConfiguration()
    # rtxConfig.live = "rtxdev"
    print("RTX Version string: " + rtxConfig.version)
    print("live version: %s" % rtxConfig.live)
    print("neo4j bolt: %s" % rtxConfig.neo4j_bolt)
    print("neo4j databse: %s" % rtxConfig.neo4j_database)
    print("neo4j username: %s" % rtxConfig.neo4j_username)
    print("neo4j password: %s" % rtxConfig.neo4j_password)
    print("mysql feedback host: %s" % rtxConfig.mysql_feedback_host)
    print("mysql feedback port: %s" % rtxConfig.mysql_feedback_port)
    print("mysql feedback username: %s" % rtxConfig.mysql_feedback_username)
    print("mysql feedback password: %s" % rtxConfig.mysql_feedback_password)
    print("mysql semmeddb host: %s" % rtxConfig.mysql_semmeddb_host)
    print("mysql semmeddb port: %s" % rtxConfig.mysql_semmeddb_port)
    print("mysql semmeddb username: %s" % rtxConfig.mysql_semmeddb_username)
    print("mysql semmeddb password: %s" % rtxConfig.mysql_semmeddb_password)
    print("mysql umls host: %s" % rtxConfig.mysql_umls_host)
    print("mysql umls port: %s" % rtxConfig.mysql_umls_port)
    print("mysql umls username: %s" % rtxConfig.mysql_umls_username)
    print("mysql umls password: %s" % rtxConfig.mysql_umls_password)

    # print("bolt protocol: %s" % rtxConfig.bolt)
    # print("database: %s" % rtxConfig.database)
    # print("username: %s" % rtxConfig.username)
    # print("password: %s" % rtxConfig.password)


if __name__ == "__main__":
    main()
