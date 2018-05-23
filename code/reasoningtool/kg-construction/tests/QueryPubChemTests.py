import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryPubChem import QueryPubChem


class QueryPubChemTestCase(unittest.TestCase):

    def test_get_chembl_ids_for_drug(self):

        sets = QueryPubChem.get_chembl_ids_for_drug('gne-493')
        self.assertIsNotNone(sets)
        self.assertEqual(sets, {'CHEMBL1084926'})

    def test_get_pubchem_id_for_chembl_id(self):

        pubchem_id = QueryPubChem.get_pubchem_id_for_chembl_id('CHEMBL521')
        self.assertIsNotNone(pubchem_id)
        self.assertEqual(pubchem_id, '3672')

        #   empty result
        pubchem_id = QueryPubChem.get_pubchem_id_for_chembl_id('chembl521')
        self.assertIsNone(pubchem_id)

        #   wrong id
        pubchem_id = QueryPubChem.get_pubchem_id_for_chembl_id('3400')
        self.assertIsNone(pubchem_id)

    def test_get_pubmed_id_for_pubchem_id(self):

        pubmed_ids = QueryPubChem.get_pubmed_id_for_pubchem_id('3500')
        self.assertIsNotNone(pubmed_ids)
        self.assertEqual(pubmed_ids, ['10860942[uid]', '11961255[uid]'])

        #   wrong id
        pubmed_ids = QueryPubChem.get_pubmed_id_for_pubchem_id('35000')
        self.assertIsNone(pubmed_ids)

    def test_get_description_url(self):

        url = QueryPubChem.get_description_url("123689")
        self.assertIsNotNone(url)
        self.assertEqual(url, "http://www.hmdb.ca/metabolites/HMDB0060288")

        #   empty result
        url = QueryPubChem.get_description_url("3500")
        self.assertIsNone(url)

        #   wrong arg format
        url = QueryPubChem.get_description_url("GO:2342343")
        self.assertIsNone(url)

        #   wrong arg type
        url = QueryPubChem.get_description_url(3500)
        self.assertIsNone(url)