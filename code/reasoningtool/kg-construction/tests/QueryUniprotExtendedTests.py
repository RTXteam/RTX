from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryUniprotExtended import QueryUniprotExtended as QUEx


class QueryUniprotExtendedTestCase(TestCase):
    def test_get_protein_name(self):
        name = QUEx.get_protein_name('UniProt:P01358')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'Gastric juice peptide 1')

        name = QUEx.get_protein_name('UniProt:Q9Y471')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'Inactive cytidine monophosphate-N-acetylneuraminic acid hydroxylase')

        name = QUEx.get_protein_name('UniProt:Q9Y47')
        self.assertIsNotNone(name)
        self.assertEqual(name, 'UNKNOWN')
