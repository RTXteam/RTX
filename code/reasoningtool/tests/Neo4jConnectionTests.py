# BEGIN user_pass.json format
# {
#   "username":"xxx",
#   "password":"xxx"
# }
# END user_pass.json format

import unittest
from Neo4jConnection import Neo4jConnection
import json


class Neo4jConnectionTestCase(unittest.TestCase):

    def test_get_protein_node(self):

        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_protein_node("P53814")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "P53814")
        self.assertEqual(nodes['n']['curie_id'], "UniProt:P53814")

        conn.close()

    def test_get_protein_nodes(self):

        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_protein_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 5)
        self.assertEqual(nodes[0], "UniProt:P53814")

        conn.close()

if __name__ == '__main__':
    unittest.main()