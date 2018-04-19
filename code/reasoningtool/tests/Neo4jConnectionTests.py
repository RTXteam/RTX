# BEGIN user_pass.json format
# {
#   "username":"xxx",
#   "password":"xxx"
# }
# END config.json format

import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection


class Neo4jConnectionTestCase(unittest.TestCase):
    def test_get_pathway_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_pathway_node("R-HSA-8866654")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "R-HSA-8866654")
        self.assertEqual(nodes['n']['curie_id'], "Reactome:R-HSA-8866654")

        conn.close()

    def test_get_pathway_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_pathway_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 705)
        self.assertEqual(nodes[0], "R-HSA-5619104")

        conn.close()

    def test_get_protein_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_protein_node("UniProt:P53814")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "P53814")
        self.assertEqual(nodes['n']['curie_id'], "UniProt:P53814")

        conn.close()

    def test_get_protein_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_protein_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 18954)
        self.assertEqual(nodes[0], "UniProt:O60884")

        conn.close()

    def test_get_microRNA_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_microRNA_node("NCBIGene:100616151")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "NCBIGene:100616151")
        self.assertEqual(nodes['n']['curie_id'], "NCBIGene:100616151")

        conn.close()

    def test_get_microRNA_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_microRNA_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 1695)
        self.assertEqual(nodes[0], "NCBIGene:100847086")

        conn.close()

    def test_get_chemical_substance_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_chemical_substance_node("CHEMBL1350")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "CHEMBL1350")
        self.assertEqual(nodes['n']['curie_id'], "ChEMBL:1350")

        conn.close()

    def test_get_chemical_substance_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_chemical_substance_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 2075)
        self.assertEqual(nodes[0], "CHEMBL1350")

        conn.close()

    def test_get_bio_process_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_bio_process_node("GO:0097289")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['name'], "GO:0097289")
        self.assertEqual(nodes['n']['curie_id'], "GO:0097289")

        conn.close()

    def test_get_bio_process_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_bio_process_nodes()

        self.assertIsNotNone(nodes)
        self.assertEqual(len(nodes), 21130)
        self.assertEqual(nodes[0], "GO:0097289")

        conn.close()

if __name__ == '__main__':
    unittest.main()

