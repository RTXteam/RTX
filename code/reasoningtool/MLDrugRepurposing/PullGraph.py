import neo4j.v1
import sys, os
import pandas as pd
import argparse as ap

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

parser = ap.ArgumentParser(description='This will take a csv containing SemMedDB predicate tuples and break them up')
# parser.add_argument('--user', type=str, nargs=1, help = 'Input the username for the neo4j instance')
# parser.add_argument('--password', type=str, nargs=1, help = 'Input the password for the neo4j instance')
# parser.add_argument('--url', type=str, nargs=1, help = 'Input the bolt url for the neo4j instance')
parser.add_argument('--live', help="The container name, which can be one of the following: Production, KG2, rtxdev, "
                                   "staging. (default: Production)", default='Production')
args = parser.parse_args()

class PullGraph():
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

    def pull_graph(self):
        """
        pulls a dataframe of all of the graph edges
        """
        res = self.neo4j_run_cypher_query('match (n)-[r]-(m) where m<>n and type(r)<>"contraindicated_for" and type(r)<>"indicated_for" with distinct n as node1, m as node2 return node1.id as source, node2.id as target')
        df = pd.DataFrame(res.data())
        return df

    def pull_nodes(self):
        """
        pulls a dataframe of all of the graph nodes
        """
        res = self.neo4j_run_cypher_query("match (n) with distinct n.id as id, n.name as name return id, name")
        df = pd.DataFrame(res.data())
        return df

    def pull_drugs(self):
        """
        pulls a dataframe of all of the graph drug nodes
        """
        res = self.neo4j_run_cypher_query("match (n:chemical_substance) with distinct n.id as id, n.name as name return id, name")
        df = pd.DataFrame(res.data())
        return df

    def pull_diseases(self):
        """
        pulls a dataframe of all of the graph disease and phenotype nodes
        """
        res = self.neo4j_run_cypher_query("match (n:phenotypic_feature) with distinct n.id as id, n.name as name return id, name union match (n:disease) with distinct n.id as id, n.name as name return id, name")
        df = pd.DataFrame(res.data())
        return df


if __name__ == '__main__':

    # create the RTXConfiguration object
    rtxConfig = RTXConfiguration()
    rtxConfig.neo4j_kg2 = "KG2c"

    pg = PullGraph(rtxConfig.neo4j_username, rtxConfig.neo4j_password, rtxConfig.neo4j_bolt)
    df = pg.pull_graph()
    df.to_csv('data/graph.csv',index=False)
    df = pg.pull_drugs()
    df.to_csv('data/drugs.csv',index=False)
    df = pg.pull_diseases()
    df.to_csv('data/diseases.csv',index=False)
