from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryCOHD import QueryCOHD


class QueryCOHDTestCases(TestCase):
    def test_find_concept_ids(self):
        ids = QueryCOHD.find_concept_ids("cancer")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids[0]['concept_id'], '192855')
        self.assertEqual(ids[0]['concept_name'], 'Cancer in situ of urinary bladder')
        self.assertEqual(ids[1]['concept_id'], '2008271')
        self.assertEqual(ids[1]['concept_name'], 'Injection or infusion of cancer chemotherapeutic substance')

        # wrong label
        ids = QueryCOHD.find_concept_ids("cancers")
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 0)

    def test_get_paired_concept_freq(self):
        result = QueryCOHD.get_paired_concept_freq("2008271", "192855")
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.000005066514896398214)
        self.assertEqual(result['concept_count'], 27)

        # wrong IDs
        result = QueryCOHD.get_paired_concept_freq("2008271", "2008271")
        self.assertIsNone(result)

        # wrong parameter format
        result = QueryCOHD.get_paired_concept_freq(2008271, 192855)
        self.assertIsNone(result)

    def test_get_individual_concept_freq(self):
        result = QueryCOHD.get_individual_concept_freq("2008271")
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.0003831786451275983)
        self.assertEqual(result['concept_count'], 2042)

        # wrong ID
        result = QueryCOHD.get_individual_concept_freq("0")
        self.assertIsNone(result)

        # wrong parameter format
        result = QueryCOHD.get_individual_concept_freq(2008271)
        self.assertIsNone(result)