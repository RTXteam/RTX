import unittest
from QueryBioLinkExtended import QueryBioLinkExtended as QBLEx


class QueryBioLinkExtendedTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):
        extended_info_json = QBLEx.get_anatomy_entity('UBERON:0004476')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, "{'xrefs': None, 'taxon': {'id': None, 'label': None}, 'categories': ['anatomical entity'], 'types': None, 'description': None, 'replaced_by': None, 'consider': None, 'synonyms': [{'val': 'set of muscles of shoulder', 'xrefs': None, 'pred': 'synonym'}, {'val': 'muscle group of shoulder', 'xrefs': None, 'pred': 'synonym'}], 'deprecated': None, 'id': 'UBERON:0004476', 'label': 'musculature of shoulder'}")

    def test_get_phenotype_entity(self):
        extended_info_json = QBLEx.get_phenotype_entity('HP:0011515')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, "{'xrefs': None, 'taxon': {'id': None, 'label': None}, 'categories': ['Phenotype'], 'types': None, 'description': None, 'replaced_by': None, 'consider': None, 'synonyms': None, 'deprecated': None, 'id': 'HP:0011515', 'label': 'Abnormal stereopsis'}")

    def test_get_disease_entity(self):
        extended_info_json = QBLEx.get_disease_entity('DOID:3965')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, "{'xrefs': None, 'taxon': {'id': None, 'label': None}, 'categories': ['disease', 'quality'], 'types': None, 'description': None, 'replaced_by': None, 'consider': None, 'synonyms': None, 'deprecated': None, 'id': 'DOID:3965', 'label': None}")

if __name__ == '__main__':
    unittest.main()