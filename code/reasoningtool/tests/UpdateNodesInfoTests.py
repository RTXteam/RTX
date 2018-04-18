"""
    Run this module outside `tests` folder.
        $ cd [git repo]/code/reasoningtool/
        $ python3 -m unittest tests/UpdateNodesInfoTests.py
"""


import unittest
from UpdateNodesInfo import Neo4jConnection
from QueryBioLinkExtended import QueryBioLinkExtended
from QueryMyGene import QueryMyGene
from QueryReactomeExtended import QueryReactomeExtended
from QueryMyChem import QueryMyChem
import json
import random


def random_int_list(start, stop, length):
    start, stop = (int(start), int(stop)) if start <= stop else (int(stop), int(start))
    length = int(abs(length)) if length else 0
    random_list = []
    for i in range(length):
        random_list.append(random.randint(start, stop))
    return random_list


class UpdateNodesInfoTestCase(unittest.TestCase):

    def test_update_anatomy_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_anatomy_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryBioLinkExtended.get_anatomy_entity(node_id)

            # retrieve anatomy entities from BioLink API
            node = conn.get_anatomy_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_phenotype_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_phenotype_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryBioLinkExtended.get_phenotype_entity(node_id)

            # retrieve phenotype entities from BioLink API
            node = conn.get_phenotype_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_microRNA_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_microRNA_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryMyGene.get_microRNA_entity(node_id)

            # retrieve phenotype entities from MyGene API
            node = conn.get_microRNA_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_pathway_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_pathway_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryReactomeExtended.get_pathway_entity(node_id)

            # retrieve phenotype entities from Reactome API
            node = conn.get_pathway_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_protein_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_protein_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryMyGene.get_protein_entity(node_id)

            # retrieve phenotype entities from MyGene API
            node = conn.get_protein_node(node_id)
            self.maxDiff = None
            self.assertIsNotNone(node['n']['curie_id'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['curie_id'])
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_disease_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_disease_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryBioLinkExtended.get_disease_entity(node_id)

            # retrieve phenotype entities from BioLink API
            node = conn.get_disease_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_chemical_substance_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_chemical_substance_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 10)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryMyChem.get_chemical_substance_entity(node_id)

            # retrieve phenotype entities from BioLink API
            node = conn.get_chemical_substance_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

    def test_update_bio_process_entity(self):
        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        nodes = conn.get_bio_process_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 10)

        for i in random_indexes:
            #   retrieve data from Neo4j
            node_id = nodes[i]
            extended_info_json_from_api = QueryBioLinkExtended.get_bio_process_entity(node_id)

            # retrieve phenotype entities from BioLink API
            node = conn.get_bio_process_node(node_id)
            self.assertIsNotNone(node['n']['name'])
            self.assertIsNotNone(node['n']['extended_info_json'])
            self.assertEqual(node_id, node['n']['name'])
            self.maxDiff = None
            self.assertEqual(extended_info_json_from_api, node['n']['extended_info_json'])
            if node['n']['extended_info_json'] != "UNKNOWN":
                self.assertEqual(json.loads(extended_info_json_from_api), json.loads(node['n']['extended_info_json']))

        conn.close()

if __name__ == '__main__':
    unittest.main()


