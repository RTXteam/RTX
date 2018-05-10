from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryKEGG import QueryKEGG


class QueryKEGGTestCases(TestCase):
    def test_map_kegg_compound_to_enzyme_commission_ids(self):

        ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00022')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 146)
        self.assertEqual('ec:1.3.1.110', ids[0])

        ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00100')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 26)
        self.assertEqual(ids, ['ec:3.13.1.4', 'ec:2.1.3.1', 'ec:4.1.1.9', 'ec:4.1.1.41', 'ec:6.4.1.3', 'ec:6.2.1.13',
                               'ec:6.2.1.17', 'ec:6.2.1.1', 'ec:2.3.3.5', 'ec:2.3.3.11', 'ec:2.3.1.9', 'ec:2.3.1.94',
                               'ec:2.3.1.8', 'ec:2.3.1.54', 'ec:2.3.1.222', 'ec:2.3.1.176', 'ec:2.3.1.168',
                               'ec:2.3.1.16', 'ec:2.8.3.1', 'ec:1.3.1.84', 'ec:1.3.1.95', 'ec:1.2.7.1', 'ec:1.2.1.87',
                               'ec:1.2.1.27', 'ec:1.3.8.7', 'ec:4.1.3.24'])

        #   retrieve 0 id
        ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00200')
        self.assertIsNotNone(ids)
        self.assertEqual(ids, [])

        #   wrong arg format
        ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('GO:2342343')
        self.assertIsNotNone(ids)
        self.assertEqual(ids, [])

        #   wrong arg type
        ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids(1000)
        self.assertIsNotNone(ids)
        self.assertEqual(ids, [])



