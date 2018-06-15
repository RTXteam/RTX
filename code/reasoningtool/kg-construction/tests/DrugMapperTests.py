import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from DrugMapper import DrugMapper

class DrugMapperTestCase(unittest.TestCase):

    def test_map_drug_to_hp(self):
        hp_set = DrugMapper.map_drug_to_hp('KWHRDNMACVLHCE-UHFFFAOYSA-N')
        self.assertIsNotNone(hp_set)
        self.assertEqual(56, len(hp_set))
        if 'HP:0004395' not in hp_set or 'HP:0000802' not in hp_set or 'HP:0001250' not in hp_set:
            self.assertFalse()

        hp_set = DrugMapper.map_drug_to_hp("CHEMBL521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))

        hp_set = DrugMapper.map_drug_to_hp("CHEMBL:521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))

        hp_set = DrugMapper.map_drug_to_hp("ChEMBL:521")
        self.assertIsNotNone(hp_set)
        self.assertEqual(0, len(hp_set))
