import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryReactomeExtended import QueryReactomeExtended as QREx

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


class QueryReactomeExtendedTestCase(unittest.TestCase):
    def test_get_pathway_entity(self):
        extended_info_json = QREx.get_pathway_entity('REACT:R-HSA-70326')
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('query_test_data.json', 'REACT:R-HSA-70326')))

    def test_get_pathway_desc(self):
        desc = QREx.get_pathway_desc('REACT:R-HSA-70326')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'REACT:R-HSA-70326'))

        desc = QREx.get_pathway_desc('REACT:R-HSA-703260')
        self.assertEqual(desc, 'None')

if __name__ == '__main__':
    unittest.main()