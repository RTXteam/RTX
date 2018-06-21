import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryMyChem import QueryMyChem as QMC


def get_from_test_file(filename, key):
    f = open(filename, 'r')
    test_data = f.read()
    try:
        test_data_dict = json.loads(test_data)
        f.close()
        return test_data_dict[key]
    except ValueError:
        f.close()
        return None


class QueryMyChemTestCase(unittest.TestCase):

    def test_get_chemical_substance_entity(self):
        extended_info_json = QMC.get_chemical_substance_entity('ChEMBL:1200766')
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "None":
            self.assertEqual(json.loads(extended_info_json),
                             json.loads(get_from_test_file('query_test_data.json', 'ChEMBL:1200766')))

    def test_get_chemical_substance_description(self):
        desc = QMC.get_chemical_substance_description('ChEMBL:154')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'ChEMBL:154'))

        desc = QMC.get_chemical_substance_description('ChEMBL:20883')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'ChEMBL:20883'))

        desc = QMC.get_chemical_substance_description('ChEMBL:110101020')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'ChEMBL:110101020'))

    def test_get_drug_side_effects(self):
        side_effects_set = QMC.get_drug_side_effects('KWHRDNMACVLHCE-UHFFFAOYSA-N')
        self.assertIsNotNone(side_effects_set)
        self.assertEqual(122, len(side_effects_set))
        if 'UMLS:C0013378' not in side_effects_set:
            self.assertFalse()
        if 'UMLS:C0022660' not in side_effects_set:
            self.assertFalse()

        side_effects_set = QMC.get_drug_side_effects('CHEMBL:521')
        self.assertIsNotNone(side_effects_set)
        self.assertEqual(0, len(side_effects_set))

        side_effects_set = QMC.get_drug_side_effects('ChEMBL:521')
        self.assertIsNotNone(side_effects_set)
        self.assertEqual(0, len(side_effects_set))

    def test_get_drug_use(self):
        #   test case for ibuprofen
        drug_use = QMC.get_drug_use("CHEMBL:521")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(11, len(drug_use['indications']))
        self.assertEqual(83, len(drug_use['contraindications']))
        self.assertDictEqual({'relation': 'indication',
                              'snomed_id': '315642008',
                              'snomed_name': 'Influenza-like symptoms'},
                             drug_use['indications'][0])
        self.assertDictEqual({'relation': 'contraindication',
                              'snomed_id': '24526004',
                              'snomed_name': 'Inflammatory bowel disease'},
                             drug_use['contraindications'][0])

        #   test CHEMBL ID with no colon
        drug_use = QMC.get_drug_use("CHEMBL521")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(11, len(drug_use['indications']))
        self.assertEqual(83, len(drug_use['contraindications']))

        #   test CHEMBL ID with a lower h
        drug_use = QMC.get_drug_use("ChEMBL:521")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(11, len(drug_use['indications']))
        self.assertEqual(83, len(drug_use['contraindications']))

        #   test case for Penicillin V
        drug_use = QMC.get_drug_use("CHEMBL615")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(12, len(drug_use['indications']))
        self.assertEqual(3, len(drug_use['contraindications']))

        #   test case for Cetirizine
        drug_use = QMC.get_drug_use("CHEMBL1000")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(9, len(drug_use['indications']))
        self.assertEqual(13, len(drug_use['contraindications']))

        #   test case for Amoxicillin
        drug_use = QMC.get_drug_use("CHEMBL1082")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(25, len(drug_use['indications']))
        self.assertEqual(17, len(drug_use['contraindications']))

        #   test case for CHEMBL2107884
        drug_use = QMC.get_drug_use("CHEMBL2107884")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(1, len(drug_use['indications']))
        self.assertEqual(0, len(drug_use['contraindications']))

        #   test case for CHEMBL250270
        drug_use = QMC.get_drug_use("CHEMBL250270")
        self.assertIsNotNone(drug_use)
        self.assertIsNotNone(drug_use['indications'])
        self.assertIsNotNone(drug_use['contraindications'])
        self.assertEqual(1, len(drug_use['indications']))
        self.assertEqual(0, len(drug_use['contraindications']))

if __name__ == '__main__':
    unittest.main()