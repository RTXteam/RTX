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
        self.assertEqual(len(ids), 1172)
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

    def test_get_protein_name(self):
        name = QueryUniprot.get_protein_name('UniProtKB:P01358')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'Gastric juice peptide 1')

        name = QueryUniprot.get_protein_name('UniProtKB:Q9Y471')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'Inactive cytidine monophosphate-N-acetylneuraminic acid hydroxylase')

        #   empty result
        name = QueryUniprot.get_protein_name('UniProtKB:Q9Y47')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'UNKNOWN')

        #   invalid parameter
        name = QueryUniprot.get_protein_name(12345)
        self.assertEqual(name, "UNKNOWN")

    def test_get_protein_gene_symbol(self):
        symbol = QueryUniprot.get_protein_gene_symbol('UniProtKB:P20848')
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol, "SERPINA2")

        #   empty result
        symbol = QueryUniprot.get_protein_gene_symbol('UniProtKB:P01358')
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol, "None")

        symbol = QueryUniprot.get_protein_gene_symbol('UniProtKB:Q96P88')
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol, "GNRHR2")

        #   invalid parameter format, 404 error
        symbol = QueryUniprot.get_protein_gene_symbol('UniProtKB:P013580')
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol, "None")