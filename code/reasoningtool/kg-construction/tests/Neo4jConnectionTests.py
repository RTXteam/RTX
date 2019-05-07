import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration

class Neo4jConnectionTestCase(unittest.TestCase):

    rtxConfig = RTXConfiguration()

    def test_get_pathway_node(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_pathway_node("REACT:R-HSA-8866654")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "REACT:R-HSA-8866654")

        conn.close()

    def test_get_pathway_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_pathway_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_protein_node(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_protein_node("UniProtKB:P53814")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "UniProtKB:P53814")

        conn.close()

    def test_get_protein_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_protein_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_microRNA_node(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_microRNA_node("NCBIGene:100616151")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "NCBIGene:100616151")

        conn.close()

    def test_get_microRNA_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_microRNA_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_chemical_substance_node(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_chemical_substance_node("CHEMBL1350")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "CHEMBL1350")

        conn.close()

    def test_get_chemical_substance_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_chemical_substance_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))
        conn.close()

    def test_get_bio_process_node(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_bio_process_node("GO:0097289")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['id'], "GO:0097289")

        conn.close()

    def test_get_bio_process_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_bio_process_nodes()

        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_node_names(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        names = conn.get_node_names('disease')
        self.assertIsNotNone(names)
        self.assertEqual(len(names), 19573)

        names = conn.get_node_names('chemical_substance')
        self.assertIsNotNone(names)
        self.assertEqual(len(names), 2226)

        conn.close()

    def test_get_cellular_component_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_cellular_component_nodes()
        print(len(nodes))
        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_molecular_function_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_molecular_function_nodes()
        print(len(nodes))
        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    def test_get_metabolite_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_metabolite_nodes()
        print(len(nodes))
        self.assertIsNotNone(nodes)
        self.assertLess(0, len(nodes))

        conn.close()

    # def test_create_disease_has_phenotype(self):
    #     f = open('config.json', 'r')
    #     config_data = f.read()
    #     f.close()
    #     config = json.loads(config_data)
    #
    #     conn = Neo4jConnection(config['url'], config['username'], config['password'])
    #
    #     #   fake data
    #     array = [{"d_id": "OMIM:605543", "p_id": 'HP:0000726'},
    #              {"d_id": "OMIM:605543", "p_id": 'HP:0000738'},
    #              {"d_id": "OMIM:605543", "p_id": 'HP:0001278'},
    #              {"d_id": "OMIM:605543", "p_id": 'HP:0001300'},
    #              {"d_id": "DOID:3218", "p_id": 'HP:0000476'},
    #              {"d_id": "DOID:3218", "p_id": 'HP:0000952'}]
    #
    #     conn.create_disease_has_phenotype(array)
    #     conn.close()

    def test_count_has_phenotype_relation(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        result = conn.count_has_phenotype_relation({"d_id": "DOID:3218", "p_id": "HP:0002245"})
        self.assertIsNotNone(result)
        self.assertEqual(1, result)

        result = conn.count_has_phenotype_relation({"d_id": "DOID:3218", "p_id": "HP:0002244"})
        self.assertIsNotNone(result)
        self.assertEqual(0, result)

        conn.close()

    def test_get_relationship(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        result = conn.get_relationship("affects", "16364fa8-96e0-11e8-b6f4-0242ac110002",
                                       "d2cc6c24-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'disease_causes_disruption_of')

        conn.close()


if __name__ == '__main__':
    unittest.main()

