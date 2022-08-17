import uuid
import itertools
import pprint
import neo4j.v1
import sys
import timeit
import argparse
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

parser = argparse.ArgumentParser()
# parser.add_argument("-u", "--user", type=str, help="The username used to connect to the neo4j instance", default='')
# parser.add_argument("-p", "--password", type=str, help="The password used to connect to the neo4j instance", default='')
# parser.add_argument("-a", "--url", type=str, help="The bolt url and port used to connect to the neo4j instance. (default:bolt://localhost:7687)", default="bolt://localhost:7687")
parser.add_argument('--live', help="The container name, which can be one of the following: Production, KG2, rtxdev, "
                                   "staging. (default: Production)", default='Production')
args = parser.parse_args()

class UpdateIndex():
    """
    This class connects to a neo4j instance with our KG in it
    then can set/drop all needed indexes

    :param url: a string containing the bolt url of the neo4j instance, ``bolt://your.neo4j.url:7687``
    :param user: a string containing the username used to access the neo4j instance
    :param password: a string containing the password used to access the neo4j instance
    :param debug: a boolian indicating weither or not to use debug mode (will print out queries sent)
    """

    def __init__(self, user, password, url ='bolt://localhost:7687', debug = False):
        self.debug = debug
        self.neo4j_url = url
        self.neo4j_user = user
        self.neo4j_password = password

        self.driver = neo4j.v1.GraphDatabase.driver(self.neo4j_url,
                                                    auth=(self.neo4j_user,
                                                          self.neo4j_password))

    def neo4j_shutdown(self):
        """
        shuts down the Orangeboard by disconnecting from the Neo4j database   
        :returns: nothing
        """
        self.driver.close()

    def neo4j_run_cypher_query(self, query, parameters=None):
        """
        runs a single cypher query in the neo4j database (without a transaction) and returns the result object
        :param query: a ``str`` object containing a single cypher query (without a semicolon)
        :param parameters: a ``dict`` object containing parameters for this query
        :returns: a `neo4j.v1.SessionResult` object resulting from executing the neo4j query
        """
        if self.debug:
            print(query)
        assert ';' not in query

        # Lazily initialize the driver
        if self.driver is None:
            self.neo4j_connect()

        session = self.driver.session()
        res = session.run(query, parameters)
        session.close()
        return res


    def set_index(self):
        """
        adds a hardcoded list on idexes and contraints to a neo4j instance
        :return: nothing
        """

        # This gets a list of all labels on the KG then removes the Base label
        res = self.neo4j_run_cypher_query('match (n) with distinct labels(n) as label_sets unwind(label_sets) as labels return distinct labels')
        label_list = res.value()
        label_list.remove('Base')


        # These are the indexes and constraints on the base label
        index_commands = [
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.id IS UNIQUE',
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.UUID IS UNIQUE',
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.uri IS UNIQUE',
            'CREATE INDEX ON :Base(name)',
            'CREATE INDEX ON :Base(seed_node_uuid)'
            ]

        # These create label specific indexes and constraints
        index_commands += ['CREATE CONSTRAINT ON (n:' + label + ') ASSERT n.id IS UNIQUE' for label in label_list]
        index_commands += ['CREATE INDEX ON :' + label + '(name)' for label in label_list]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)



    def drop_index(self):
        """
        requests lists of all contraints and idexes on the neo4j server then drops all of them.
        :return: nothing
        """


        res = self.neo4j_run_cypher_query('CALL db.constraints()')
        constraints = res.value()

        index_commands = ['DROP ' + constraint for constraint in constraints]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)

        res = self.neo4j_run_cypher_query('CALL db.indexes()')
        indexes = res.value()

        index_commands = ['DROP ' + index for index in indexes]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)

    def replace(self):
        self.drop_index()
        self.set_index()

    def set_test(self):
        """
        Sets the idexes up to test for an error
        """
        self.drop_index()
        index_commands = [
            'CREATE INDEX ON :Base(UUID)',
            'CREATE INDEX ON :Base(seed_node_uuid)',
            'CREATE CONSTRAINT ON (n:biological_process) ASSERT n.id IS UNIQUE',
            'CREATE CONSTRAINT ON (n:microRNA) ASSERT n.id IS UNIQUE',
            'CREATE CONSTRAINT ON (n:protein) ASSERT n.id IS UNIQUE'
            ]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)
        

if __name__ == '__main__':
    # create the RTXConfiguration object
    rtxConfig = RTXConfiguration()

    ui = UpdateIndex(rtxConfig.neo4j_username, rtxConfig.neo4j_password, rtxConfig.neo4j_bolt)
    ui.replace()

