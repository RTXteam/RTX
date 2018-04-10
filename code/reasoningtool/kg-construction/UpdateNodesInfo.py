
''' This module defines the class Neo4jConnection. Neo4jConnection class is designed
to connect to Neo4j database and perform operations on a graphic model object. (e.g.,
retrieve node and update node)
'''

# BEGIN user_pass.json format
# {
#   "username":"xxx",
#   "password":"xxx"
# }
# END user_pass.json format

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

from neo4j.v1 import GraphDatabase
import json
from QueryBioLinkExtended import QueryBioLinkExtended

class Neo4jConnection:

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def get_anatomical_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_anatomical_nodes)

    def update_anatomical_node(self, n_id, extended_info_json):
        with self._driver.session() as session:
            return session.write_transaction(self._update_anatomical_node, n_id, extended_info_json)

    @staticmethod
    def _get_anatomical_nodes(tx):
        result = tx.run("MATCH (n:anatomical_entity) RETURN n.name")
        return [record["n.name"] for record in result]

    @staticmethod
    def _update_anatomical_node(tx, n_id, extended_info_json):
        result = tx.run('MATCH (n:anatomical_entity{name:"%s"}) set n.extended_info_json="%s"' % (n_id, extended_info_json))
        return result


def update_anatomy_nodes():

    f = open('user_pass.json', 'r')
    user_data = f.read()
    f.close()
    user = json.loads(user_data)

    conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
    nodes = conn.get_anatomical_nodes()

    for i, node_id in enumerate(nodes):
        extended_info_json = QueryBioLinkExtended.get_anatomy_entity(node_id)
        conn.update_anatomical_node(node_id, extended_info_json)

    conn.close()

if __name__ == '__main__':

    update_anatomy_nodes()
