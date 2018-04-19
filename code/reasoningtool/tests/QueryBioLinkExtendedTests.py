import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryBioLinkExtended import QueryBioLinkExtended as QBLEx


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


class QueryBioLinkExtendedTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):
        extended_info_json = QBLEx.get_anatomy_entity('UBERON:0004476')
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('UBERON:0004476'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('UBERON:0004476')))

    def test_get_phenotype_entity(self):
        extended_info_json = QBLEx.get_phenotype_entity('HP:0011515')
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('HP:0011515'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('HP:0011515')))

    def test_get_disease_entity(self):
        extended_info_json = QBLEx.get_disease_entity('DOID:3965')
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('DOID:3965'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('DOID:3965')))

    def test_get_bio_process_entity(self):
        extended_info_json = QBLEx.get_bio_process_entity('GO:0097289')
        self.assertIsNotNone(extended_info_json)
        # self.assertEqual(extended_info_json, get_from_test_file('GO:0097289'))
        if extended_info_json != "UNKNOWN":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('GO:0097289')))

if __name__ == '__main__':
    unittest.main()