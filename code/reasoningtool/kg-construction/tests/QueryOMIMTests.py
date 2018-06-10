import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryOMIM import QueryOMIM


class QueryOMIMExtendedTestCase(unittest.TestCase):

    def test_disease_mim_to_gene_symbols_and_uniprot_ids(self):
        qo = QueryOMIM()

        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603903')
        self.assertIsNotNone(res)
        self.assertEqual(res, {'gene_symbols': set(), 'uniprot_ids': {'P68871'}})

        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:613074')
        self.assertIsNotNone(res)
        self.assertEqual(res, {'gene_symbols': {'MIR96'}, 'uniprot_ids': set()})

        #   test issue 1
        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603918')
        self.assertIsNotNone(res)
        self.assertEqual(res, {'gene_symbols': set(), 'uniprot_ids': set()})

        #   empty result
        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:129905')
        self.assertIsNotNone(res)
        self.assertEqual(res, {'gene_symbols': set(), 'uniprot_ids': set()})

        #   invalid parameter
        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids(603903)
        self.assertIsNotNone(res)
        self.assertEqual(res, {'gene_symbols': set(), 'uniprot_ids': set()})


    def test_disease_mim_to_description(self):
        qo = QueryOMIM()
        desc = qo.disease_mim_to_description('OMIM:100100')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, "In its rare complete form, 'prune belly' syndrome comprises megacystis (massively "
                               "enlarged bladder) with disorganized detrusor muscle, cryptorchidism, and thin abdominal"
                               " musculature with overlying lax skin (summary by {23:Weber et al., 2011}).")

        desc = qo.disease_mim_to_description('OMIM:614747')
        self.assertEqual(desc, "None")

        desc = qo.disease_mim_to_description('OMIM:61447')
        self.assertEqual(desc, 'None')

        desc = qo.disease_mim_to_description(614747)
        self.assertEqual(desc, 'None')

if __name__ == '__main__':
    unittest.main()