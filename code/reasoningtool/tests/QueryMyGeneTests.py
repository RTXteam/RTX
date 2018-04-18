import unittest
from QueryMyGene import QueryMyGene
import json


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

        extended_info_json = QueryMyGene.get_protein_entity("UniProt:O60884")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, get_from_test_file('UniProt:O60884'))

    def test_get_microRNA_entity(self):

        extended_info_json = QueryMyGene.get_microRNA_entity("NCBIGene: 100847086")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, get_from_test_file('NCBIGene: 100847086'))


if __name__ == '__main__':
    unittest.main()