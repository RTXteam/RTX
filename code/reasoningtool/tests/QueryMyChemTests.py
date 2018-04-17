from unittest import TestCase
from QueryMyChem import QueryMyChem as QMC
import json

class QueryMyChemTestCase(TestCase):

    def test_get_chemical_substance_entity(self):
        extended_info_json = QMC.get_chemical_substance_entity('CHEMBL1201217')
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        #   The string is too long and I can only read the string from a file now
        f = open('mychem.json', 'r')
        data = f.read()
        f.close()
        self.assertEqual(extended_info_json, data)