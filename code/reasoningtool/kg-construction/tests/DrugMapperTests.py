import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from DrugMapper import DrugMapper

class DrugMapperTestCase(unittest.TestCase):

    def test_map_drug_to_hp_with_side_effects(self):
        hp_set = DrugMapper.map_drug_to_hp_with_side_effects('KWHRDNMACVLHCE-UHFFFAOYSA-N')
        self.assertIsNotNone(hp_set)
        self.assertEqual(56, len(hp_set))
        if 'HP:0004395' not in hp_set or 'HP:0000802' not in hp_set or 'HP:0001250' not in hp_set:
            self.assertFalse()

        hp_set = DrugMapper.map_drug_to_hp_with_side_effects("CHEMBL521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))

        hp_set = DrugMapper.map_drug_to_hp_with_side_effects("CHEMBL:521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))

        hp_set = DrugMapper.map_drug_to_hp_with_side_effects("ChEMBL:521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))

    def test_map_drug_to_UMLS(self):
        #   test case for ibuprofen
        umls_results = DrugMapper.map_drug_to_UMLS("ChEMBL:521")
        self.assertIsNotNone(umls_results)
        self.assertIsNotNone(umls_results['indications'])
        self.assertIsNotNone(umls_results['contraindications'])
        self.assertEqual(11, len(umls_results['indications']))
        self.assertEqual(83, len(umls_results['contraindications']))

        #   test case for Penicillin V
        umls_results = DrugMapper.map_drug_to_UMLS("CHEMBL615")
        self.assertIsNotNone(umls_results)
        self.assertIsNotNone(umls_results['indications'])
        self.assertIsNotNone(umls_results['contraindications'])
        self.assertEqual(12, len(umls_results['indications']))
        self.assertEqual(3, len(umls_results['contraindications']))

        #   test case for Cetirizine
        umls_results = DrugMapper.map_drug_to_UMLS("CHEMBL1000")
        self.assertIsNotNone(umls_results)
        self.assertIsNotNone(umls_results['indications'])
        self.assertIsNotNone(umls_results['contraindications'])
        self.assertEqual(9, len(umls_results['indications']))
        self.assertEqual(13, len(umls_results['contraindications']))

        #   test case for Amoxicillin
        umls_results = DrugMapper.map_drug_to_UMLS("CHEMBL1082")
        self.assertIsNotNone(umls_results)
        self.assertIsNotNone(umls_results['indications'])
        self.assertIsNotNone(umls_results['contraindications'])
        self.assertEqual(24, len(umls_results['indications']))
        self.assertEqual(17, len(umls_results['contraindications']))

    def test_map_drug_to_ontology(self):
        #   test case for ibuprofen
        onto_results = DrugMapper.map_drug_to_ontology("ChEMBL:521")
        self.assertIsNotNone(onto_results)
        self.assertIsNotNone(onto_results['indications'])
        self.assertIsNotNone(onto_results['contraindications'])
        self.assertEqual(8, len(onto_results['indications']))
        self.assertEqual(89, len(onto_results['contraindications']))

        #   test case for Penicillin V
        onto_results = DrugMapper.map_drug_to_ontology("CHEMBL615")
        self.assertIsNotNone(onto_results)
        self.assertIsNotNone(onto_results['indications'])
        self.assertIsNotNone(onto_results['contraindications'])
        self.assertEqual(7, len(onto_results['indications']))
        self.assertEqual(6, len(onto_results['contraindications']))

        #   test case for Cetirizine
        onto_results = DrugMapper.map_drug_to_ontology("CHEMBL1000")
        self.assertIsNotNone(onto_results)
        self.assertIsNotNone(onto_results['indications'])
        self.assertIsNotNone(onto_results['contraindications'])
        self.assertEqual(8, len(onto_results['indications']))
        self.assertEqual(23, len(onto_results['contraindications']))

        #   test case for Amoxicillin
        onto_results = DrugMapper.map_drug_to_ontology("CHEMBL1082")
        self.assertIsNotNone(onto_results)
        self.assertIsNotNone(onto_results['indications'])
        self.assertIsNotNone(onto_results['contraindications'])
        self.assertEqual(6, len(onto_results['indications']))
        self.assertEqual(21, len(onto_results['contraindications']))