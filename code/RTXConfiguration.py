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

        # This is the flag/property to switch between the two containers
        self.live = "Production"
        # self.live = "KG2"
        # self.live = "rtxdev"
        # self.live = "staging"

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
        config = json.loads(config_data)

        self.username = config['username']
        self.password = config['password']

    #### Define attribute version
    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, version: str):
        self._version = version

    @property
    def bolt(self) -> str:
        return self._bolt

    @property
    def live(self) -> str:
        return self._live

    @live.setter
    def live(self, live: str):
        self._live = live
        if self.live == "Production":
            self.bolt = "bolt://rtx.ncats.io:7687"
            self.database = "rtx.ncats.io:7474/db/data"

        elif self.live == "KG2":
            self.bolt = "bolt://rtx.ncats.io:7787"
            self.database = "rtx.ncats.io:7574/db/data"

        elif self.live == "rtxdev":
            self.bolt = "bolt://rtxdev.saramsey.org:7887"
            self.database = "rtxdev.saramsey.org:7674/db/data"

        elif self.live == "staging":
            self.bolt = "bolt://steveneo4j.saramsey.org:7687"
            self.database = "steveneo4j.saramsey.org:7474/db/data"

        else:
            self.bolt = None
            self.database = None

    @bolt.setter
    def bolt(self, bolt: str):
        self._bolt = bolt

    @property
    def database(self) -> str:
        return self._database

    @database.setter
    def database(self, database: str):
        self._database = database


def main():
    rtxConfig = RTXConfiguration()
    # rtxConfig.live = "rtxdev"
    print("RTX Version string: " + rtxConfig.version)
    print("live version: %s" % rtxConfig.live)
    print("bolt protocol: %s" % rtxConfig.bolt)
    print("database: %s" % rtxConfig.database)
    print("username: %s" % rtxConfig.username)
    print("password: %s" % rtxConfig.password)


if __name__ == "__main__":
    main()
