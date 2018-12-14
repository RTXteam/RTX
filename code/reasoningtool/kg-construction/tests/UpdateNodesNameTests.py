from unittest import TestCase
import json
import random
import os,sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection
from QueryUniprot import QueryUniprot
from QueryMyGene import QueryMyGene

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration


def random_int_list(start, stop, length):
    start, stop = (int(start), int(stop)) if start <= stop else (int(stop), int(start))
    length = int(abs(length)) if length else 0
    random_list = []
    for i in range(length):
        random_list.append(random.randint(start, stop))
    return random_list


class UpdateNodesNameTestCase(TestCase):

    rtxConfig = RTXConfiguration()

    def test_update_protein_names_old(self):
        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)

        protein_nodes_ids = ['UniProtKB:P01358', 'UniProtKB:P20848', 'UniProtKB:Q9Y471', 'UniProtKB:O60397',
                             'UniProtKB:Q8IZJ3', 'UniProtKB:Q7Z2Y8', 'UniProtKB:Q8IWN7', 'UniProtKB:Q156A1']

        for protein_id in protein_nodes_ids:
            node = conn.get_protein_node(protein_id)
            name = QueryUniprot.get_protein_name(protein_id)

            self.assertIsNotNone(node)
            self.assertIsNotNone(name)
            self.assertEqual(name, node['n']['name'])

    def test_update_protein_names(self):
        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_protein_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes) - 1, 10)

        mg = QueryMyGene()

        for i in random_indexes:
            # retrieve data from BioLink API
            node_id = nodes[i]
            name = mg.get_protein_name(node_id)

            # retrieve data from Neo4j
            node = conn.get_protein_node(node_id)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['name'])
            self.assertEqual(node_id, node['n']['id'])
            self.assertEqual(name, node['n']['name'])