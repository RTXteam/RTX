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
        nodes = conn.get_pathway_node("Reactome:R-HSA-8866654")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "Reactome:R-HSA-8866654")

        conn.close()

    def test_get_pathway_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_pathway_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_protein_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_protein_node("UniProt:P53814")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "UniProt:P53814")

        conn.close()

    def test_get_protein_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_protein_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_microRNA_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_microRNA_node("NCBIGene:100616151")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "NCBIGene:100616151")

        conn.close()

    def test_get_microRNA_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_microRNA_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_chemical_substance_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_chemical_substance_node("ChEMBL:1350")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "ChEMBL:1350")

        conn.close()

    def test_get_chemical_substance_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_chemical_substance_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))
        conn.close()

    def test_get_bio_process_node(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_bio_process_node("GO:0097289")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "GO:0097289")

        conn.close()

    def test_get_bio_process_nodes(self):
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_bio_process_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

if __name__ == '__main__':
    unittest.main()

