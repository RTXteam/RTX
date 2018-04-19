import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryMyChem import QueryMyChem as QMC

def get_from_test_file(key):
    f = open('test_data.json', 'r')
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
        extended_info_json = QMC.get_chemical_substance_entity('CHEMBL1201217')
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('CHEMBL1201217'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('CHEMBL1201217')))

if __name__ == '__main__':
    unittest.main()