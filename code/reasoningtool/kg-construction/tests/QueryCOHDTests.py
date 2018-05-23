from unittest import TestCase

import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)

from QueryCOHD import QueryCOHD


class QueryCOHDTestCases(TestCase):
    def test_find_concept_ids(self):
        ids = QueryCOHD.find_concept_ids("ibuprofen", "Condition", 1)
        self.assertIsNotNone(ids)
        correct_results = [{'concept_class_id': 'Clinical Finding', 'concept_code': '212602006', 'concept_count': 0.0,
                            'concept_id': 4059406, 'concept_name': 'Ibuprofen poisoning', 'domain_id': 'Condition',
                            'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '218613000', 'concept_count': 0.0,
                            'concept_id': 4329188, 'concept_name': 'Adverse reaction to ibuprofen',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '295250003', 'concept_count': 0.0,
                            'concept_id': 4170835, 'concept_name': 'Ibuprofen overdose', 'domain_id': 'Condition',
                            'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '295252006', 'concept_count': 0.0,
                            'concept_id': 4172259, 'concept_name': 'Intentional ibuprofen overdose',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '290260009', 'concept_count': 0.0,
                            'concept_id': 4156776, 'concept_name': 'Intentional ibuprofen poisoning',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '295253001', 'concept_count': 0.0,
                            'concept_id': 4170836, 'concept_name': 'Ibuprofen overdose of undetermined intent',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '216487007', 'concept_count': 0.0,
                            'concept_id': 4313103, 'concept_name': 'Accidental poisoning by ibuprofen',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '290261008', 'concept_count': 0.0,
                            'concept_id': 4156777, 'concept_name': 'Ibuprofen poisoning of undetermined intent',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                           {'concept_class_id': 'Clinical Finding', 'concept_code': '295251004', 'concept_count': 0.0,
                            'concept_id': 4172258, 'concept_name': 'Accidental ibuprofen overdose',
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'}]
        self.assertEqual(ids, correct_results)

        # wrong name
        ids = QueryCOHD.find_concept_ids("ibuprofe", "Condition")
        self.assertEqual(ids, [])

        # wrong domain
        ids = QueryCOHD.find_concept_ids("ibuprofe", "Conditi")
        self.assertEqual(ids, [])

    def test_get_paired_concept_freq(self):
        result = QueryCOHD.get_paired_concept_freq("2008271", "192855", 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.000005585247351056813)
        self.assertEqual(result['concept_count'], 10)

        # wrong IDs
        result = QueryCOHD.get_paired_concept_freq("2008271", "2008271")
        self.assertEqual(result, {})

        # wrong parameter format
        result = QueryCOHD.get_paired_concept_freq(2008271, 192855)
        self.assertEqual(result, {})

    def test_get_individual_concept_freq(self):
        result = QueryCOHD.get_individual_concept_freq("192855", 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.0002055371025188907)
        self.assertEqual(result['concept_count'], 368)

        # default dataset id
        result = QueryCOHD.get_individual_concept_freq("192855")
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.0002055371025188907)
        self.assertEqual(result['concept_count'], 368)

        # wrong ID
        result = QueryCOHD.get_individual_concept_freq("0", 1)
        self.assertEqual(result, {})

        # wrong parameter format
        result = QueryCOHD.get_individual_concept_freq(2008271, 1)
        self.assertEqual(result, {})

    def test_get_associated_concept_domain_freq(self):
        result = QueryCOHD.get_associated_concept_domain_freq('192855', 'Procedure')
        self.assertIsNotNone(result)
        self.assertEqual(result[0]['concept_frequency'], 0.00016867447000191573)
        self.assertEqual(len(result), 159)

        # wrong concept ID
        result = QueryCOHD.get_associated_concept_domain_freq("0", "drug")
        self.assertEqual(result, [])

        # wrong domain
        result = QueryCOHD.get_associated_concept_domain_freq("192855", "dru")
        self.assertEqual(result, [])

        # wrong parameter format
        result = QueryCOHD.get_associated_concept_domain_freq(192855, "drug")
        self.assertEqual(result, [])

    def test_get_concepts(self):
        result = QueryCOHD.get_concepts(["192855", "2008271"])
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result, [{'concept_class_id': 'Clinical Finding', 'concept_code': '92546004',
                                   'concept_id': 192855, 'concept_name': 'Cancer in situ of urinary bladder',
                                   'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'},
                                  {'concept_class_id': '4-dig billing code', 'concept_code': '99.25',
                                   'concept_id': 2008271, 'concept_name': 'Injection or infusion of cancer '
                                                                          'chemotherapeutic substance',
                                   'domain_id': 'Procedure', 'vocabulary_id': 'ICD9Proc'}])

        result = QueryCOHD.get_concepts(["192855"])
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_class_id': 'Clinical Finding', 'concept_code': '92546004',
                                   'concept_id': 192855, 'concept_name': 'Cancer in situ of urinary bladder',
                                   'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'}])

        # wrong concept_id type
        result = QueryCOHD.get_concepts(["192855", 2008271])
        self.assertEqual(result, [])

        # empty concept_ids
        result = QueryCOHD.get_concepts(["192855", 2008271])
        self.assertEqual(result, [])