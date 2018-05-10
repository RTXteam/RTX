from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryUniprot import QueryUniprot


class QueryUniprotTestCase(TestCase):
    def test_map_enzyme_commission_id_to_uniprot_ids(self):
        # short results
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.4.1.17")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, {'Q5FB93', 'Q4U331', 'G8Q0U6'})

        # empty result
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.3.1.110")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 0)

        # long results
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.2.1.22")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 882)
        self.assertTrue('A0A1R4INE8' in ids)

        # fake id
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:4.4.1.xx")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 0)

        # wrong arg format
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("R-HSA-1912422")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 0)

        # wrong arg type
        ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids(1912422)
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 0)