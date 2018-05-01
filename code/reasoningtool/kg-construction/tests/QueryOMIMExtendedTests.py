import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryOMIMExtended import QueryOMIM


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


class QueryOMIMExtendedTestCase(unittest.TestCase):
    def test_get_disease_entity(self):
        desc = QueryOMIM().disease_mim_to_description('OMIM:100100')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'OMIM:100100'))

        desc = QueryOMIM().disease_mim_to_description('OMIM:614747')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'OMIM:614747'))

        desc = QueryOMIM().disease_mim_to_description('OMIM:61447')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'OMIM:61447'))


if __name__ == '__main__':
    unittest.main()