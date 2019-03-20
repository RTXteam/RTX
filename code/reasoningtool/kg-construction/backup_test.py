from neo4j.v1 import GraphDatabase
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

### BEGIN HOW TO RUN
#   Function: The script is used to test the consistency of the dumped database file
#   Instance: This python script needs to be run on both 'kgdump' container and the machine which is loaded the dumped
#             file. If the outputs on both machines are the same, the test is passed
#   how to load the dumped database file:
#               tar -zxvf xxxx.tar.gz
#               neo4j-admin load --from=xxxx.cypher --database=graph --force
#   how to run the python script:
#               python3 backup_test.py
#   output example:
#               nodes counter : 68800
#               relationships counter : 2508369
### END HOW TO RUN

### BEGIN user_pass.json format
# {
#   "username":"xxx",
#   "password":"xxx"
# }
### END user_pass.json format

class TestBackup(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def print_node_count(self):
        with self._driver.session() as session:
            counter = session.write_transaction(self._get_node_count)
            print('nodes counter : %d' % counter)

    def print_relation_count(self):
        with self._driver.session() as session:
            counter = session.write_transaction(self._get_relation_count)
            print('relationships counter : %d' % counter)

    @staticmethod
    def _get_node_count(tx):
        result = tx.run("START n=node(*) RETURN count(n)")
        return result.single()[0]

    @staticmethod
    def _get_relation_count(tx):
        result = tx.run("START r=relationship(*) RETURN count(r)")
        return result.single()[0]


if __name__ == '__main__':

    # create the RTXConfiguration object
    rtxConfig = RTXConfiguration()

    obj = TestBackup(rtxConfig.bolt, rtxConfig.username, rtxConfig.password)
    obj.print_node_count()
    obj.print_relation_count()
    obj.close()
