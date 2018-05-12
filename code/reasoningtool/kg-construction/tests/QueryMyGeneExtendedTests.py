import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryMyGeneExtended import QueryMyGeneExtended


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


class QueryMyGeneExtendedTestCase(unittest.TestCase):

    def test_get_protein_entity(self):

        extended_info_json = QueryMyGeneExtended.get_protein_entity("UniProt:O60884")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "UNKNOWN":
            self.assertEqual(len(json.loads(extended_info_json)),
                             len(json.loads(get_from_test_file('query_test_data.json', 'UniProt:O60884'))))

    def test_get_microRNA_entity(self):

        extended_info_json = QueryMyGeneExtended.get_microRNA_entity("NCBIGene: 100847086")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "UNKNOWN":
            self.assertEqual(len(json.loads(extended_info_json)),
                             len(json.loads(get_from_test_file('query_test_data.json', 'NCBIGene: 100847086'))))

    def test_get_protein_desc(self):

        desc = QueryMyGeneExtended.get_protein_desc("UniProt:O60884")
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json','UniProt:O60884'))

        desc = QueryMyGeneExtended.get_protein_desc("UniProt:O608840")
        self.assertEqual(desc, 'None')

    def test_get_microRNA_desc(self):

        desc = QueryMyGeneExtended.get_microRNA_desc("NCBIGene: 100847086")
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'NCBIGene: 100847086'))

        desc = QueryMyGeneExtended.get_microRNA_desc("NCBIGene: 1008470860")
        self.assertEqual(desc, 'None')

if __name__ == '__main__':
    unittest.main()