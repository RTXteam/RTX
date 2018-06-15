import uuid
import itertools
import pprint
import neo4j.v1
import sys
import timeit

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

    def drop_index(self):
        """
        removes all indexes provided that apoc is installed.
        :returns: Nothing
        """
        self.neo4j_run_cypher_query('CALL apoc.schema.assert({}, {})')


    def set_index(self):
        """
        adds a hardcoded list on idexes and contraints to a neo4j instance
        :return: nothing
        """

        # This is a list of all the labels in the KG and needs to be updated when new labels are added
        node_label_list = [
            'metabolite',
            'protein',
            'anatomical_entity',
            'molecular_function',
            'disease',
            'phenotypic_feature',
            'biological_process',
            'microRNA',
            'pathway',
            'cellular_component',
            'chemical_substance'
            ]

        # These are the indexes and constraints on the base label
        index_commands = [
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.id IS UNIQUE',
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.UUID IS UNIQUE',
            'CREATE CONSTRAINT ON (n:Base) ASSERT n.uri IS UNIQUE',
            'CREATE INDEX ON :Base(name)',
            'CREATE INDEX ON :Base(seed_node_uuid)'
            ]

        # These create label specific indexes and constraints
        index_commands += ['CREATE CONSTRAINT ON (n:' + label + ') ASSERT n.id IS UNIQUE' for label in node_label_list]
        index_commands += ['CREATE INDEX ON :' + label + '(name)' for label in node_label_list]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)

    def drop_index_apocless(self, index_commands = None):
        """
        runs through a list of hardcoded commands to drop all indexes and constaints if apoc is not installed on the neo4j instance.
        :param index_commands: A list of strings containing the cypher commands for dropping the indexes/constraints. If None method will run through hardcoded list of commands. (default is None)
        :return: nothing
        """
        if index_commands is None:
            # This is a list of all the labels in the KG and needs to be updated when new labels are added
            node_label_list = [
                'metabolite',
                'protein',
                'anatomical_entity',
                'molecular_function',
                'disease',
                'phenotypic_feature',
                'biological_process',
                'microRNA',
                'pathway',
                'cellular_component',
                'chemical_substance'
                ]

            # These are the indexes and constraints on the base label
            index_commands = [
                'DROP CONSTRAINT ON (n:Base) ASSERT n.id IS UNIQUE',
                'DROP CONSTRAINT ON (n:Base) ASSERT n.UUID IS UNIQUE',
                'DROP CONSTRAINT ON (n:Base) ASSERT n.uri IS UNIQUE',
                'DROP INDEX ON :Base(name)',
                'DROP INDEX ON :Base(seed_node_uuid)'
                ]

            # These create label specific indexes and constraints
            index_commands += ['DROP CONSTRAINT ON (n:' + label + ') ASSERT n.id IS UNIQUE' for label in node_label_list]
            index_commands += ['DROP INDEX ON :' + label + '(name)' for label in node_label_list]

        for command in index_commands:
            self.neo4j_run_cypher_query(command)

    def drop_index_apocless_small(self):
        """
        Drops the small list of indexes added using orangeboard.py
        """
        index_commands = [
            'DROP INDEX ON :Base(UUID)',
            'DROP INDEX ON :Base(seed_node_uuid)'
            ]
        self.drop_index_apocless(index_commands)

