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
    rtxConfig.neo4j_kg2 = 'KG2pre'

    def test_anatomical_entity_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("UBERON:0001753")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "UBERON:0001753")
        self.assertEqual(nodes['n']['name'], "cementum")
        self.assertEqual(nodes['n']['description'], "Odontoid tissue that is deposited by cementoblasts onto dentine "
                                                    "tissue and functions to attach teeth, odontodes and other "
                                                    "odontogenic derivatives to bone tissue and the integument.")
        self.assertEqual(nodes['n']['category'], "anatomical_entity")

        conn.close()

    def test_biological_process_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("GO:0048817")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "GO:0048817")
        self.assertEqual(nodes['n']['name'], "negative regulation of hair follicle maturation")
        self.assertEqual(nodes['n']['description'], "Any process that stops, prevents, or reduces the frequency, "
                                                    "rate or extent of hair follicle maturation.")
        self.assertEqual(nodes['n']['category'], "biological_process")

        conn.close()

    def test_cellular_component_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
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

        conn.close()

    def test_chemical_substance_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("CHEMBL1236962")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "CHEMBL1236962")
        self.assertEqual(nodes['n']['name'], "omipalisib")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "chemical_substance")

        conn.close()

    def test_disease_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("DOID:6016")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "DOID:6016")
        self.assertEqual(nodes['n']['name'], "adult central nervous system mature teratoma")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "disease")

        conn.close()

    def test_metabolite_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("KEGG:C19630")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "KEGG:C19630")
        self.assertEqual(nodes['n']['name'], "Diketone")
        self.assertEqual(nodes['n']['description'], "None")
        self.assertEqual(nodes['n']['category'], "metabolite")

        conn.close()

    def test_microRNA_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("NCBIGene:100302124")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "NCBIGene:100302124")
        self.assertEqual(nodes['n']['name'], "MIR1288")
        self.assertEqual(nodes['n']['symbol'], "MIR1288")
        self.assertEqual(nodes['n']['category'], "microRNA")

        conn.close()

    def test_molecular_function_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("GO:0030898")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "GO:0030898")
        self.assertEqual(nodes['n']['name'], "actin-dependent ATPase activity")
        self.assertEqual(nodes['n']['description'], "Catalysis of the reaction: ATP + H2O = ADP + phosphate. This "
                                                    "reaction requires the presence of an actin filament to accelerate"
                                                    " release of ADP and phosphate.")
        self.assertEqual(nodes['n']['category'], "molecular_function")

        conn.close()

    def test_pathway_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("REACT:R-HSA-69895")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "REACT:R-HSA-69895")
        self.assertEqual(nodes['n']['name'], "Transcriptional  activation of  cell cycle inhibitor p21 ")
        self.assertEqual(nodes['n']['description'], "Both p53-independent and p53-dependent mechanisms of induction of "
                                                    "p21 mRNA have been demonstrated. p21 is transcriptionally "
                                                    "activated by p53 after DNA damage (el-Deiry et al., 1993).")
        self.assertEqual(nodes['n']['category'], "pathway")

        conn.close()

    def test_phenotypic_feature_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
        nodes = conn.get_node("HP:0010559")

        self.assertIsNotNone(nodes)
        self.assertEqual(nodes['n']['rtx_name'], "HP:0010559")
        self.assertEqual(nodes['n']['name'], "Vertical clivus")
        self.assertEqual(nodes['n']['description'], "An abnormal vertical orientation of the clivus (which normally "
                                                    "forms a kind of slope from the sella turcica down to the region "
                                                    "of the foramen magnum).")
        self.assertEqual(nodes['n']['category'], "phenotypic_feature")

        conn.close()

    def test_protein_nodes(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)
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

        conn.close()

    def test_affects_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("DOID:653")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("GO:0009117")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("affects", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'disease_causes_disruption_of')

        conn.close()

    def test_capable_of_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("UBERON:0001004")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("GO:0003016")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("capable_of", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'capable_of')

        conn.close()

    def test_causes_or_contributes_to_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("CHEMBL601719")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("HP:0000975")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("causes_or_contributes_to", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'SIDER')
        self.assertEqual(result['r']['relation'], 'causes_or_contributes_to')

        conn.close()

    def test_contraindicated_for_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("CHEMBL945")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("HP:0011106")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("contraindicated_for", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'MyChem.info')
        self.assertEqual(result['r']['relation'], 'contraindicated_for')

        conn.close()

    def test_expressed_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("Q6VY07")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("UBERON:0002082")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("expressed_in", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'BioLink')
        self.assertEqual(result['r']['relation'], 'expressed_in')

        conn.close()

    def test_gene_associated_with_condition_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("P21397")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("DOID:0060693")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("gene_associated_with_condition", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'DisGeNet')
        self.assertEqual(result['r']['relation'], 'gene_associated_with_condition')

        conn.close()

    def test_gene_mutations_contribute_to_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("Q7Z6L0")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("OMIM:128200")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("gene_mutations_contribute_to", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'OMIM')
        self.assertEqual(result['r']['relation'], 'gene_mutations_contribute_to')

        conn.close()

    def test_has_part_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("UBERON:0001037")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("GO:0045095")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("has_part", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'Monarch_SciGraph')
        self.assertEqual(result['r']['relation'], 'has_part')

        conn.close()

    def test_has_phenotype_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("DOID:0050177")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("HP:0011447")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("has_phenotype", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'BioLink')
        self.assertEqual(result['r']['relation'], 'has_phenotype')

        conn.close()

    def test_indicated_for_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("CHEMBL1200979")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("HP:0002590")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("indicated_for", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'MyChem.info')
        self.assertEqual(result['r']['relation'], 'indicated_for')

        conn.close()

    def test_involved_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("Q9UQ53")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("GO:0006491")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("involved_in", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'gene_ontology')
        self.assertEqual(result['r']['relation'], 'involved_in')

        conn.close()

    def test_negatively_regulates_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("CHEMBL449158")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("Q7Z6L0")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("negatively_regulates", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'DGIdb;MyCancerGenomeClinicalTrial')
        self.assertEqual(result['r']['relation'], 'inhibitor')

        conn.close()

    def test_participates_in_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("Q9UJX3")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("REACT:R-HSA-400253")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("participates_in", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'reactome')
        self.assertEqual(result['r']['relation'], 'participates_in')

        conn.close()

    def test_physically_interacts_with_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("P41235")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("Q9UQ53")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("physically_interacts_with", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'PC2')
        self.assertEqual(result['r']['relation'], 'physically_interacts_with')

        conn.close()

    def test_positively_regulates_with_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("CHEMBL1451")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("P04150")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("positively_regulates", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'DGIdb;GuideToPharmacologyInteractions')
        self.assertEqual(result['r']['relation'], 'agonist')

        conn.close()

    def test_regulates_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("Q03052")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("Q9UQ53")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("regulates", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'PC2')
        self.assertEqual(result['r']['relation'], 'regulates_expression_of')

        conn.close()

    def test_subclass_of_relationships(self):

        conn = Neo4jConnection(self.rtxConfig.neo4j_bolt, self.rtxConfig.neo4j_username, self.rtxConfig.neo4j_password)

        # get the source node
        nodes = conn.get_node("GO:1901515")
        s_uuid = nodes['n']['UUID']

        # get the target node
        nodes = conn.get_node("GO:0022857")
        t_uuid = nodes['n']['UUID']

        result = conn.get_relationship("subclass_of", s_uuid, t_uuid)

        self.assertIsNotNone(result)
        self.assertEqual(result['r']['provided_by'], 'gene_ontology')
        self.assertEqual(result['r']['relation'], 'subclass_of')

        conn.close()


if __name__ == '__main__':
    unittest.main()