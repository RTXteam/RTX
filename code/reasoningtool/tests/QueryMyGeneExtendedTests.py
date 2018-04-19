import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryMyGeneExtended import QueryMyGeneExtended


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


class QueryProteinEntityTestCase(unittest.TestCase):

    def test_get_protein_entity(self):

        extended_info_json = QueryMyGeneExtended.get_protein_entity("UniProt:O60884")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('UniProt:O60884'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('UniProt:O60884')))

    def test_get_microRNA_entity(self):

        extended_info_json = QueryMyGeneExtended.get_microRNA_entity("NCBIGene: 100847086")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('NCBIGene: 100847086'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('NCBIGene: 100847086')))


if __name__ == '__main__':
    unittest.main()