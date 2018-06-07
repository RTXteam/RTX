import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryBioLink import QueryBioLink as QBL


def get_from_test_file(key):
    f = open('query_test_data.json', 'r')
    test_data = f.read()
    try:
        test_data_dict = json.loads(test_data)
        f.close()
        return test_data_dict[key]
    except ValueError:
        f.close()
        return None


class QueryBioLinkTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):
        result = QBL.get_anatomy_entity('UBERON:0004476')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertDictEqual(json.loads(result), json.loads(get_from_test_file('UBERON:0004476')))

        # invalid id, code == 500
        result = QBL.get_anatomy_entity('UBERON:000447600')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_phenotype_entity(self):
        result = QBL.get_phenotype_entity('HP:0011515')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('HP:0011515')))

        # invalid id, code == 500
        result = QBL.get_phenotype_entity('HP:00115150')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_disease_entity(self):
        result = QBL.get_disease_entity('DOID:3965')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('DOID:3965')))

        # invalid id, code == 500
        result = QBL.get_disease_entity('DOID:39650')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_bio_process_entity(self):
        result = QBL.get_bio_process_entity('GO:0097289')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('GO:0097289')))

        # invalid id, code == 500
        result = QBL.get_bio_process_entity('GO:00972890')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")


if __name__ == '__main__':
    unittest.main()