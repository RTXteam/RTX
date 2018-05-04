from unittest import TestCase
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection
from QueryUniprotExtended import QueryUniprotExtended


class UpdateNodesNameTestCase(TestCase):
    def test_update_protein_names(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)
        conn = Neo4jConnection(config['url'], config['username'], config['password'])

        protein_nodes_ids = ['UniProt:P01358', 'UniProt:P20848', 'UniProt:Q9Y471', 'UniProt:O60397',
                             'UniProt:Q8IZJ3', 'UniProt:Q7Z2Y8', 'UniProt:Q8IWN7', 'UniProt:Q156A1']

        for protein_id in protein_nodes_ids:
            node = conn.get_protein_node(protein_id)
            name = QueryUniprotExtended.get_protein_name(protein_id)

            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(name)
            self.assertEqual(name, node['n']['name'])
