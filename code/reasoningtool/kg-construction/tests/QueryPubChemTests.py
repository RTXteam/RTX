import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryPubChem import QueryPubChem


class QueryPubChemTestCase(unittest.TestCase):
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