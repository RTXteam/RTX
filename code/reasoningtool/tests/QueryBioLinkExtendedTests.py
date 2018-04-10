import unittest
from QueryBioLinkExtended import QueryBioLinkExtended as QBLEx


class QueryBioLinkExtendedTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):

        extended_info_json = QBLEx.get_anatomy_entity('UBERON:0004476')
        print(extended_info_json)
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, "{'xrefs': None, 'taxon': {'id': None, 'label': None}, 'categories': ['anatomical entity'], 'types': None, 'description': None, 'replaced_by': None, 'consider': None, 'synonyms': [{'val': 'set of muscles of shoulder', 'xrefs': None, 'pred': 'synonym'}, {'val': 'muscle group of shoulder', 'xrefs': None, 'pred': 'synonym'}], 'deprecated': None, 'id': 'UBERON:0004476', 'label': 'musculature of shoulder'}")

if __name__ == '__main__':
    unittest.main()