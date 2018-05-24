from unittest import TestCase

import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)

from QueryCOHD import QueryCOHD


class QueryCOHDTestCases(TestCase):
    def test_find_concept_ids(self):
        ids = QueryCOHD.find_concept_ids("ibuprofen", "Condition", 1)
        self.assertIsNotNone(ids)
        self.assertEqual(ids, [{'concept_class_id': 'Clinical Finding', 'concept_code': '212602006', 'concept_count': 0.0,
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
                            'domain_id': 'Condition', 'vocabulary_id': 'SNOMED'}])

        # wrong name
        ids = QueryCOHD.find_concept_ids("ibuprof1", "Condition")
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

    def test_get_xref_from_OMOP(self):
        result = QueryCOHD.get_xref_from_OMOP("192855", "UMLS", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0], {"intermediate_omop_concept_code": "92546004",
                                     "intermediate_omop_concept_id": 192855,
                                     "intermediate_omop_concept_name": "Cancer in situ of urinary bladder",
                                     "intermediate_omop_vocabulary_id": "SNOMED",
                                     "intermediate_oxo_curie": "SNOMEDCT:92546004",
                                     "intermediate_oxo_label": "Cancer in situ of urinary bladder",
                                     "omop_distance": 0,
                                     "oxo_distance": 1,
                                     "source_omop_concept_code": "92546004",
                                     "source_omop_concept_id": 192855,
                                     "source_omop_concept_name": "Cancer in situ of urinary bladder",
                                     "source_omop_vocabulary_id": "SNOMED",
                                     "target_curie": "UMLS:C0154091",
                                     "target_label": "Cancer in situ of urinary bladder",
                                     "total_distance": 1
                                     })

        #   wrong concept id
        result = QueryCOHD.get_xref_from_OMOP("1928551", "UMLS", 2)
        self.assertEqual(result, [])

        #   wrong mapping_targets
        result = QueryCOHD.get_xref_from_OMOP("1928551", "UMS", 2)
        self.assertEqual(result, [])

        #   wrong distance format
        result = QueryCOHD.get_xref_from_OMOP("1928551", "UMLS", "2")
        self.assertEqual(result, [])

    def test_get_xref_to_OMOP(self):
        result = QueryCOHD.get_xref_to_OMOP("DOID:8398", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {'intermediate_oxo_id': 'ICD9CM:715.3', 'intermediate_oxo_label': '',
                                     'omop_concept_name': 'Localized osteoarthrosis uncertain if primary OR secondary',
                                     'omop_distance': 1, 'omop_domain_id': 'Condition', 'omop_standard_concept_id': 72990,
                                     'oxo_distance': 1, 'source_oxo_id': 'DOID:8398', 'source_oxo_label': 'osteoarthritis',
                                     'total_distance': 2})

        #   default distance
        result = QueryCOHD.get_xref_to_OMOP("DOID:8398")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

        #   wrong curie id
        result = QueryCOHD.get_xref_to_OMOP("DOID:83981", 2)
        self.assertEqual(result, [])

        #   wrong distance format
        result = QueryCOHD.get_xref_to_OMOP("DOID:8398", "2")
        self.assertEqual(result, [])

    def test_get_map_from_standard_concept_id(self):
        result = QueryCOHD.get_map_from_standard_concept_id("72990", "ICD9CM")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {"concept_class_id": "4-dig nonbill code", "concept_code": "715.3",
                                     "concept_id": 44834979,
                                     "concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary",
                                     "domain_id": "Condition", "standard_concept": None, "vocabulary_id": "ICD9CM"
                                     })

        #   default vocabulary
        result = QueryCOHD.get_map_from_standard_concept_id("72990")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 12)
        self.assertEqual(result[0], {"concept_class_id": "Diagnosis", "concept_code": "116253", "concept_id": 45930832,
                                     "concept_name": "Localized Osteoarthrosis Uncertain If Primary or Secondary",
                                     "domain_id": "Condition", "standard_concept": None, "vocabulary_id": "CIEL"})

        #   wrong concept_id id
        result = QueryCOHD.get_map_from_standard_concept_id("DOID:839812", 2)
        self.assertEqual(result, [])

        #   wrong concept_id format
        result = QueryCOHD.get_map_from_standard_concept_id(8398, 2)
        self.assertEqual(result, [])

    def test_get_map_to_standard_concept_id(self):
        result = QueryCOHD.get_map_to_standard_concept_id("715.3", "ICD9CM")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {"source_concept_code": "715.3", "source_concept_id": 44834979,
                                     "source_concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary",
                                     "source_vocabulary_id": "ICD9CM", "standard_concept_id": 72990,
                                     "standard_concept_name": "Localized osteoarthrosis uncertain if primary OR secondary",
                                     "standard_domain_id": "Condition"
                                     })

        # default vocabulary
        result = QueryCOHD.get_map_to_standard_concept_id("715.3")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {"source_concept_code": "715.3", "source_concept_id": 44834979,
                                     "source_concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary",
                                     "source_vocabulary_id": "ICD9CM", "standard_concept_id": 72990,
                                     "standard_concept_name": "Localized osteoarthrosis uncertain if primary OR secondary",
                                     "standard_domain_id": "Condition"
                                     })

        #   wrong concept_code id
        result = QueryCOHD.get_map_from_standard_concept_id("725.3")
        self.assertEqual(result, [])

        #   wrong concept_code format
        result = QueryCOHD.get_map_from_standard_concept_id(725.3)
        self.assertEqual(result, [])

    def test_get_vocabularies(self):
        result = QueryCOHD.get_vocabularies()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 73)
        self.assertEqual(result[0]['vocabulary_id'], '')
        self.assertEqual(result[1]['vocabulary_id'], 'ABMS')

    def test_get_associated_concept_freq(self):
        result = QueryCOHD.get_associated_concept_freq("192855")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 768)
        self.assertEqual(result[0], {'associated_concept_id': 2213216,
                                     'associated_concept_name': 'Cytopathology, selective cellular enhancement technique with interpretation (eg, liquid based slide preparation method), except cervical or vaginal',
                                     'associated_domain_id': 'Measurement',
                                     'concept_count': 330,
                                     'concept_frequency': 0.0001843131625848748,
                                     'concept_id': 192855,
                                     'dataset_id': 1})

        result = QueryCOHD.get_associated_concept_freq("192855", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2735)
        self.assertEqual(result[0], {'associated_concept_id': 197508,
                                     'associated_concept_name': 'Malignant tumor of urinary bladder',
                                     'associated_domain_id': 'Condition',
                                     'concept_count': 1477,
                                     'concept_frequency': 0.0002753141274545969,
                                     'concept_id': 192855,
                                     'dataset_id': 2})

        #   invalid conecpt_id value
        result = QueryCOHD.get_associated_concept_freq("1928551")
        self.assertEqual(result, [])

        #   invalid dataset_id value
        result = QueryCOHD.get_associated_concept_freq("192855", 3)
        self.assertEqual(result, [])

        #   invalid concept format
        result = QueryCOHD.get_associated_concept_freq(192855)
        self.assertEqual(result, [])

        #   invalid dataset_id format
        result = QueryCOHD.get_associated_concept_freq("192855", "1")
        self.assertEqual(result, [])

    def test_get_most_frequent_concepts(self):
        #   default domain and dataset_id
        result = QueryCOHD.get_most_frequent_concepts(10)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'concept_count': 1189172,
                                     'concept_frequency': 0.6641819762950932,
                                     'concept_id': 44814653,
                                     'concept_name': 'Unknown',
                                     'dataset_id': 1,
                                     'domain_id': 'Observation'})

        #   default dataset_id
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'concept_count': 233790,
                                     'concept_frequency': 0.1305774978203572,
                                     'concept_id': 320128,
                                     'concept_name': 'Essential hypertension',
                                     'dataset_id': 1,
                                     'domain_id': 'Condition'})

        #   no default value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'concept_count': 459776,
                                     'concept_frequency': 0.08570265962394365,
                                     'concept_id': 320128,
                                     'concept_name': 'Essential hypertension',
                                     'dataset_id': 2,
                                     'domain_id': 'Condition'})

        #   wrong num value
        result = QueryCOHD.get_most_frequent_concepts(-10)
        self.assertEqual(result, [])

        #   wrong num format
        result = QueryCOHD.get_most_frequent_concepts("10")
        self.assertEqual(result, [])

        #   wrong domain value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition1")
        self.assertEqual(result, [])

        #   wrong domain format
        result = QueryCOHD.get_most_frequent_concepts(10, 1, 2)
        self.assertEqual(result, [])

        #   wrong dataset_id value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", 3)
        self.assertEqual(result, [])

        #   wrong dataset_id format
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", "2")
        self.assertEqual(result, [])

        #   num == 0
        result = QueryCOHD.get_most_frequent_concepts(0, "Condition", 2)
        self.assertEqual(result, [])

    def test_get_chi_square(self):
        #   default dataset_id
        result = QueryCOHD.get_chi_square("192855", "2008271", "Condition")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'chi_square': 306.2816108187519,
                                  'concept_id_1': 192855,
                                  'concept_id_2': 2008271,
                                  'dataset_id': 1,
                                  'p-value': 1.4101531778039801e-68}])

        #   dataset_id == 2
        result = QueryCOHD.get_chi_square("192855", "2008271", "Condition", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'chi_square': 7065.7865572100745,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 2,
                                   'p-value': 0.0}])

        #   default domain and dataset_id
        result = QueryCOHD.get_chi_square("192855", "2008271")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'chi_square': 306.2816108187519,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 1,
                                   'p-value': 1.4101531778039801e-68}])

        #   no concept_id_2, default domain and dataset_id
        result = QueryCOHD.get_chi_square("192855")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 768)

        #   no concept_id_2, default dataset_id
        result = QueryCOHD.get_chi_square("192855", "", "Condition")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 226)

        #   no concept_id_2, dataset_id == 2
        result = QueryCOHD.get_chi_square("192855", "", "Condition", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 991)

        #   no concept_id_2, dataset_id == 2, default domain
        result = QueryCOHD.get_chi_square("192855", "", "", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2735)

        #   invalid concept_id_1 type
        result = QueryCOHD.get_chi_square(192855, "", "", 1)
        self.assertEqual(result, [])

        #   invalid concept_id_2 type
        result = QueryCOHD.get_chi_square("192855", 2008271, "", 1)
        self.assertEqual(result, [])

        #   invalid dataset_id value
        result = QueryCOHD.get_chi_square("192855", "2008271", "condition", 3)
        self.assertEqual(result, [])
