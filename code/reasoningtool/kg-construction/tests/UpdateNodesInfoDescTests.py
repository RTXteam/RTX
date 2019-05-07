import unittest
import json
import random

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection
from QueryEBIOLS import QueryEBIOLS
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryMyChem import QueryMyChem
from QueryReactome import QueryReactome
from QueryKEGG import QueryKEGG
from QueryPubChem import QueryPubChem
from QueryHMDB import QueryHMDB

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration


def random_int_list(start, stop, length):
    start, stop = (int(start), int(stop)) if start <= stop else (int(stop), int(start))
    length = int(abs(length)) if length else 0
    random_list = []
    for i in range(length):
        random_list.append(random.randint(start, stop))
    return random_list


class UpdateNodesInfoDescTestCase(unittest.TestCase):

    rtxConfig = RTXConfiguration()

    def test_update_anatomy_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_anatomy_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = QueryEBIOLS.get_anatomy_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_anatomy_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_phenotype_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_phenotype_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = QueryEBIOLS.get_phenotype_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_phenotype_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_microRNA_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_microRNA_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        mg = QueryMyGene()
        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = mg.get_microRNA_desc(node_id)

            # retrieve data from Neo4j
            node = conn.get_microRNA_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_pathway_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_pathway_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes) - 1, 100)

        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = QueryReactome.get_pathway_desc(node_id)

            # retrieve data from Neo4j
            node = conn.get_pathway_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_protein_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_protein_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        mg = QueryMyGene()
        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = mg.get_protein_desc(node_id)

            # retrieve data from Neo4j
            node = conn.get_protein_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_disease_nodes_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_disease_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        qo = QueryOMIM()
        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            if node_id[:4] == "OMIM":
                desc = qo.disease_mim_to_description(node_id)
            elif node_id[:4] == "DOID":
                desc = QueryEBIOLS.get_disease_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_disease_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_chemical_substance_entity(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_chemical_substance_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = QueryMyChem.get_chemical_substance_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_chemical_substance_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['rtx_name'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['rtx_name'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_bio_process_entity(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_bio_process_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from API
            node_id = nodes[i]
            desc = QueryEBIOLS.get_bio_process_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_bio_process_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_cellular_component_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_cellular_component_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from BioLink API
            node_id = nodes[i]
            desc = QueryEBIOLS.get_cellular_component_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_molecular_function_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_molecular_function_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes)-1, 100)

        for i in random_indexes:
            # retrieve data from BioLink API
            node_id = nodes[i]
            desc = QueryEBIOLS.get_molecular_function_description(node_id)

            # retrieve data from Neo4j
            node = conn.get_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

    def test_update_metabolite_desc(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_metabolite_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(nodes) - 1, 100)

        for i in random_indexes:
            # retrieve data from BioLink API
            node_id = nodes[i]
            pubchem_id = QueryKEGG.map_kegg_compound_to_pub_chem_id(node_id)
            hmdb_url = QueryPubChem.get_description_url(pubchem_id)
            desc = QueryHMDB.get_compound_desc(hmdb_url)

            # retrieve data from Neo4j
            node = conn.get_node(node_id)
            self.assertIsNotNone(node)
            self.assertIsNotNone(node['n']['id'])
            self.assertIsNotNone(node['n']['description'])
            self.assertEqual(node_id, node['n']['id'])
            if node['n']['description'] != "None":
                self.assertEqual(desc, node['n']['description'])

        conn.close()

if __name__ == '__main__':
    unittest.main()


