from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryCOHD import QueryCOHD


class QueryCOHDTestCases(TestCase):
    def test_find_concept_ids(self):
        ids = QueryCOHD.find_concept_ids("cancer")
        self.assertIsNotNone(ids)
        self.assertEqual(ids, {"2008271", "192855"})

        # wrong label
        ids = QueryCOHD.find_concept_ids("cancers")
        self.assertIsNotNone(ids)
        self.assertEqual(ids, set())

    def test_get_paired_concept_freq(self):
        freq = QueryCOHD.get_paired_concept_freq("2008271", "192855")
        self.assertIsNotNone(freq)
        self.assertEqual(freq, 0.000005066514896398214)

        # wrong IDs
        freq = QueryCOHD.get_paired_concept_freq("2008271", "2008271")
        self.assertIsNone(freq)

        # wrong parameter format
        freq = QueryCOHD.get_paired_concept_freq(2008271, 192855)
        self.assertIsNone(freq)

    def test_get_individual_concept_freq(self):
        freq = QueryCOHD.get_individual_concept_freq("2008271")
        self.assertIsNotNone(freq)
        self.assertEqual(freq, 0.0003831786451275983)

        # wrong ID
        freq = QueryCOHD.get_individual_concept_freq("0")
        self.assertIsNone(freq)

        # wrong parameter format
        freq = QueryCOHD.get_individual_concept_freq(2008271)
        self.assertIsNone(freq)