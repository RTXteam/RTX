#!/usr/bin/python3

import re
import os
import sys
import datetime
import json
import time

class RTXConfiguration:

    #### Constructor
    def __init__(self):
        self.version = "RTX 0.5.4"

        file_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'

        if not os.path.exists(file_path):
            # scp the file
            os.system("scp rtxconfig@rtx.ncats.io:/mnt/temp/config.json " + file_path)
        else:
            now_time = datetime.datetime.now()
            modified_time = time.localtime(os.stat(file_path).st_mtime)
            modified_time = datetime.datetime(*modified_time[:6])
            if (now_time - modified_time).days > 0:
                # scp the file
                os.system("scp rtxconfig@rtx.ncats.io:/mnt/temp/config.json " + file_path)

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

    #### Define attribute version
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

        if self.live not in self.config.keys():
            self.neo4j_bolt = None
            self.neo4j_database = None
            self.neo4j_username = None
            self.neo4j_password = None
            self.mysql_host = None
            self.mysql_port = None
            self.mysql_username = None
            self.mysql_password = None
        else:
            self.neo4j_bolt = self.config[self.live]["neo4j"]["bolt"]
            self.neo4j_database = self.config[self.live]["neo4j"]["database"]
            self.neo4j_username = self.config[self.live]["neo4j"]["username"]
            self.neo4j_password = self.config[self.live]["neo4j"]["password"]
            self.mysql_host = self.config[self.live]["mysql"]["host"]
            self.mysql_port = self.config[self.live]["mysql"]["port"]
            self.mysql_username = self.config[self.live]["mysql"]["username"]
            self.mysql_password = self.config[self.live]["mysql"]["password"]

        # if self.live == "Production":
        #     self.bolt = "bolt://rtx.ncats.io:7687"
        #     self.database = "rtx.ncats.io:7474/db/data"
        #
        # elif self.live == "KG2":
        #     self.bolt = "bolt://rtx.ncats.io:7787"
        #     self.database = "rtx.ncats.io:7574/db/data"
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
    def mysql_host(self) -> str:
        return self._mysql_host

    @mysql_host.setter
    def mysql_host(self, host: str):
        self._mysql_host = host

    @property
    def mysql_port(self) -> str:
        return self._mysql_port

    @mysql_port.setter
    def mysql_port(self, port: str):
        self._mysql_port = port

    @property
    def mysql_username(self) -> str:
        return self._mysql_username

    @mysql_username.setter
    def mysql_username(self, username: str):
        self._mysql_username = username

    @property
    def mysql_password(self) -> str:
        return self._mysql_password

    @mysql_password.setter
    def mysql_password(self, password: str):
        self._mysql_password = password


def main():
    rtxConfig = RTXConfiguration()
    # rtxConfig.live = "rtxdev"
    print("RTX Version string: " + rtxConfig.version)
    print("live version: %s" % rtxConfig.live)
    print("neo4j bolt: %s" % rtxConfig.neo4j_bolt)
    print("neo4j databse: %s" % rtxConfig.neo4j_database)
    print("neo4j username: %s" % rtxConfig.neo4j_username)
    print("neo4j password: %s" % rtxConfig.neo4j_password)
    print("mysql host: %s" % rtxConfig.mysql_host)
    print("mysql port: %s" % rtxConfig.mysql_port)
    print("mysql username: %s" % rtxConfig.mysql_username)
    print("mysql password: %s" % rtxConfig.mysql_password)


    # print("bolt protocol: %s" % rtxConfig.bolt)
    # print("database: %s" % rtxConfig.database)
    # print("username: %s" % rtxConfig.username)
    # print("password: %s" % rtxConfig.password)


if __name__ == "__main__":
    main()
