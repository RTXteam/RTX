from unittest import TestCase
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection
from QueryUniprot import QueryUniprot


class UpdateNodesNameTestCase(TestCase):
    def test_update_protein_names(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)
        conn = Neo4jConnection(config['url'], config['username'], config['password'])

        protein_nodes_ids = ['UniProtKB:P01358', 'UniProtKB:P20848', 'UniProtKB:Q9Y471', 'UniProtKB:O60397',
                             'UniProtKB:Q8IZJ3', 'UniProtKB:Q7Z2Y8', 'UniProtKB:Q8IWN7', 'UniProtKB:Q156A1']

        for protein_id in protein_nodes_ids:
            node = conn.get_protein_node(protein_id)
            name = QueryUniprot.get_protein_name(protein_id)

            self.assertIsNotNone(node)
            self.assertIsNotNone(name)
            self.assertEqual(name, node['n']['name'])
