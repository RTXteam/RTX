import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration


class KGTestCase(unittest.TestCase):

    rtxConfig = RTXConfiguration()

    def test_anatomical_entity_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("UBERON:0001753")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "UBERON:0001753")
        self.assertEqual(nodes['n']['name'], "cementum")
        self.assertEqual(nodes['n']['description'], "Odontoid tissue that is deposited by cementoblasts onto dentine "
                                                    "tissue and functions to attach teeth, odontodes and other "
                                                    "odontogenic derivatives to bone tissue and the integument.")
        self.assertEqual(nodes['n']['category'], "anatomical_entity")
        self.assertEqual(nodes['n']['UUID'], "b0336992-9875-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_biological_process_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("GO:0048817")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "GO:0048817")
        self.assertEqual(nodes['n']['name'], "negative regulation of hair follicle maturation")
        self.assertEqual(nodes['n']['description'], "Any process that stops, prevents, or reduces the frequency, "
                                                    "rate or extent of hair follicle maturation.")
        self.assertEqual(nodes['n']['category'], "biological_process")
        self.assertEqual(nodes['n']['UUID'], "d47e7670-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_cellular_component_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("GO:0071005")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "GO:0071005")
        self.assertEqual(nodes['n']['name'], "U2-type precatalytic spliceosome")
        self.assertEqual(nodes['n']['description'], "A spliceosomal complex that is formed by the recruitment of the "
                                                    "preassembled U4/U6.U5 tri-snRNP to the prespliceosome. Although "
                                                    "all 5 snRNPs are present, the precatalytic spliceosome is "
                                                    "catalytically inactive. The precatalytic spliceosome includes "
                                                    "many proteins in addition to those found in the U1, U2 and "
                                                    "U4/U6.U5 snRNPs.")
        self.assertEqual(nodes['n']['category'], "cellular_component")
        self.assertEqual(nodes['n']['UUID'], "d5061044-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_chemical_substance_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("CHEMBL1236962")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "CHEMBL1236962")
        self.assertEqual(nodes['n']['name'], "omipalisib")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "chemical_substance")
        self.assertEqual(nodes['n']['UUID'], "d205341a-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_disease_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("DOID:6016")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "DOID:6016")
        self.assertEqual(nodes['n']['name'], "adult central nervous system mature teratoma")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "disease")
        self.assertEqual(nodes['n']['UUID'], "16301a48-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_metabolite_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("KEGG:C19630")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "KEGG:C19630")
        self.assertEqual(nodes['n']['name'], "Diketone")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "metabolite")
        self.assertEqual(nodes['n']['UUID'], "d7ad8084-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_microRNA_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("NCBIGene:100302124")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "NCBIGene:100302124")
        self.assertEqual(nodes['n']['name'], "MIR1288")
        self.assertEqual(nodes['n']['symbol'], "MIR1288")
        self.assertEqual(nodes['n']['category'], "microRNA")
        self.assertEqual(nodes['n']['UUID'], "0c04b8fa-96e3-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_molecular_function_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("GO:0030898")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "GO:0030898")
        self.assertEqual(nodes['n']['name'], "actin-dependent ATPase activity")
        self.assertEqual(nodes['n']['description'], "Catalysis of the reaction: ATP + H2O = ADP + phosphate. This "
                                                    "reaction requires the presence of an actin filament to accelerate"
                                                    " release of ADP and phosphate.")
        self.assertEqual(nodes['n']['category'], "molecular_function")
        self.assertEqual(nodes['n']['UUID'], "d36f33e6-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_pathway_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("REACT:R-HSA-69895")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "REACT:R-HSA-69895")
        self.assertEqual(nodes['n']['name'], "Transcriptional  activation of  cell cycle inhibitor p21 ")
        self.assertEqual(nodes['n']['description'], "Both p53-independent and p53-dependent mechanisms of induction of "
                                                    "p21 mRNA have been demonstrated. p21 is transcriptionally "
                                                    "activated by p53 after DNA damage (el-Deiry et al., 1993).")
        self.assertEqual(nodes['n']['category'], "pathway")
        self.assertEqual(nodes['n']['UUID'], "d80adfcc-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_phenotypic_feature_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("HP:0010559")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "HP:0010559")
        self.assertEqual(nodes['n']['name'], "Vertical clivus")
        self.assertEqual(nodes['n']['description'], "An abnormal vertical orientation of the clivus (which normally "
                                                    "forms a kind of slope from the sella turcica down to the region "
                                                    "of the foramen magnum).")
        self.assertEqual(nodes['n']['category'], "phenotypic_feature")
        self.assertEqual(nodes['n']['UUID'], "825980a8-96f2-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_protein_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        nodes = conn.get_node("Q8IWB1")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "Q8IWB1")
        self.assertEqual(nodes['n']['name'], "inositol 1,4,5-trisphosphate receptor interacting protein")
        self.assertEqual(nodes['n']['description'], "This gene encodes a membrane-associated protein that binds the "
                                                    "inositol 1,4,5-trisphosphate receptor (ITPR). The encoded protein"
                                                    " enhances the sensitivity of ITPR to intracellular calcium "
                                                    "signaling. Alternative splicing results in multiple transcript "
                                                    "variants. [provided by RefSeq, Dec 2012].")
        self.assertEqual(nodes['n']['category'], "protein")
        self.assertEqual(nodes['n']['id'], "UniProtKB:Q8IWB1")
        self.assertEqual(nodes['n']['UUID'], "741373f8-96e0-11e8-b6f4-0242ac110002")
        self.assertEqual(nodes['n']['seed_node_uuid'], "14aa4450-96e0-11e8-b6f4-0242ac110002")

        conn.close()

    def test_affects_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("affects", "16364fa8-96e0-11e8-b6f4-0242ac110002",
                                       "d2cc6c24-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'disease_causes_disruption_of')

        conn.close()

    def test_capable_of_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("capable_of", "7df5b95a-983c-11e8-b6f4-0242ac110002",
                                       "d2607de8-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'capable_of')

        conn.close()

    def test_contraindicated_for_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("contraindicated_for", "d20e9fb4-96e0-11e8-b6f4-0242ac110002",
                                       "b03d10fa-96e5-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'MyChem.info')
        self.assertEqual(result['r']['relation'], 'contraindicated_for')

        conn.close()

    def test_expressed_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("expressed_in", "80c58cd0-96e0-11e8-b6f4-0242ac110002",
                                       "dce493ee-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'BioLink')
        self.assertEqual(result['r']['relation'], 'expressed_in')

        conn.close()

    def test_gene_associated_with_condition_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("gene_associated_with_condition", "cd838018-96e0-11e8-b6f4-0242ac110002",
                                       "158d16e0-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'DisGeNet')
        self.assertEqual(result['r']['relation'], 'gene_associated_with_condition')

        conn.close()

    def test_gene_mutations_contribute_to_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("gene_mutations_contribute_to", "dbf31438-96e0-11e8-b6f4-0242ac110002",
                                       "153e59f6-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'OMIM')
        self.assertEqual(result['r']['relation'], 'gene_mutations_contribute_to')

        conn.close()

    def test_has_part_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("has_part", "dce485fc-96e0-11e8-b6f4-0242ac110002",
                                       "d293e5ca-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'has_plasma_membrane_part')

        conn.close()

    def test_has_phenotype_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("has_phenotype", "15866ade-96e0-11e8-b6f4-0242ac110002",
                                       "825980a8-96f2-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'BioLink')
        self.assertEqual(result['r']['relation'], 'has_phenotype')

        conn.close()

    def test_indicated_for_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("indicated_for", "d2121c52-96e0-11e8-b6f4-0242ac110002",
                                       "b03d1852-96e5-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'MyChem.info')
        self.assertEqual(result['r']['relation'], 'indicated_for')

        conn.close()

    def test_involved_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("involved_in", "a00eaf46-96e9-11e8-b6f4-0242ac110002",
                                       "d43b3982-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'gene_ontology')
        self.assertEqual(result['r']['relation'], 'involved_in')

        conn.close()

    def test_participates_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("participates_in", "3de31040-96e0-11e8-b6f4-0242ac110002",
                                       "d80c6e50-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'reactome')
        self.assertEqual(result['r']['relation'], 'participates_in')

        conn.close()

    def test_physically_interacts_with_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("physically_interacts_with", "9e84a81e-96e0-11e8-b6f4-0242ac110002",
                                       "d70a77ae-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'KEGG;UniProtKB')
        self.assertEqual(result['r']['relation'], 'physically_interacts_with')

        conn.close()

    def test_regulates_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("regulates", "648092c6-987b-11e8-b6f4-0242ac110002",
                                       "0c04b8fa-96e3-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'miRGate')
        self.assertEqual(result['r']['relation'], 'regulates_expression_of')

        conn.close()

    def test_subclass_of_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.bolt, self.rtxConfig.username, self.rtxConfig.password)
        result = conn.get_relationship("subclass_of", "d47e7670-96e0-11e8-b6f4-0242ac110002",
                                       "d47e8322-96e0-11e8-b6f4-0242ac110002")
        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'gene_ontology')
        self.assertEqual(result['r']['relation'], 'subclass_of')

        conn.close()


if __name__ == '__main__':
    unittest.main()