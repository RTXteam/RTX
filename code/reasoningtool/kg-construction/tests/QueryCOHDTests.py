from unittest import TestCase

import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)

from QueryCOHD import QueryCOHD


class QueryCOHDTestCases(TestCase):
    def test_find_concept_ids(self):
        # result = QueryCOHD.find_concept_ids("cancer", "Condition", dataset_id=1, min_count=0)
        # self.assertIsNotNone(result)
        # self.assertEqual(len(result), 84)
        # self.assertEqual(result[0], {'concept_class_id': 'Clinical Finding',
        #                              'concept_code': '92546004',
        #                              'concept_count': 368.0,
        #                              'concept_id': 192855,
        #                              'concept_name': 'Cancer in situ of urinary bladder', 'domain_id': 'Condition',
        #                              'vocabulary_id': 'SNOMED'})

        #   default dataset_id and min_count
        result = QueryCOHD.find_concept_ids("cancer", "Condition")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {'concept_class_id': 'Clinical Finding',
                                     'concept_code': '92546004',
                                     'concept_count': 368.0,
                                     'concept_id': 192855,
                                     'concept_name': 'Cancer in situ of urinary bladder', 'domain_id': 'Condition',
                                     'vocabulary_id': 'SNOMED'})

        #   default dataset_id and domain
        result = QueryCOHD.find_concept_ids("cancer")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 37)
        self.assertEqual(result[0], {'concept_class_id': 'Procedure',
                                     'concept_code': '15886004',
                                     'concept_count': 4195.0,
                                     'concept_id': 4048727,
                                     'concept_name': 'Screening for cancer',
                                     'domain_id': 'Procedure',
                                     'vocabulary_id': 'SNOMED'})

        #   invalid name value
        result = QueryCOHD.find_concept_ids("cancer1", "Condition")
        self.assertEqual(result, [])

        #   invalid domain value
        result = QueryCOHD.find_concept_ids("cancer", "Conditi")
        self.assertEqual(result, [])

        #   timeout case (backend timeout issue has been fixed)
        result = QueryCOHD.find_concept_ids("ibuprofen", "Drug", dataset_id=1, min_count=0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1000)
        self.assertEqual(result[0], {'concept_class_id': 'Clinical Drug',
                                     'concept_code': '197806',
                                     'concept_count': 115101,
                                     'concept_id': 19019073,
                                     'concept_name': 'Ibuprofen 600 MG Oral Tablet',
                                     'domain_id': 'Drug',
                                     'vocabulary_id': 'RxNorm'})

    def test_get_paired_concept_freq(self):
        result = QueryCOHD.get_paired_concept_freq("2008271", "192855", 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.000005585247351056813)
        self.assertEqual(result['concept_count'], 10)

        #   default dataset_id
        result = QueryCOHD.get_paired_concept_freq("2008271", "192855")
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.000005585247351056813)
        self.assertEqual(result['concept_count'], 10)

        #   invalid ID value
        result = QueryCOHD.get_paired_concept_freq("2008271", "2008271")
        self.assertEqual(result, {})

        #   invalid parameter type
        result = QueryCOHD.get_paired_concept_freq(2008271, 192855)
        self.assertEqual(result, {})

    def test_get_individual_concept_freq(self):
        result = QueryCOHD.get_individual_concept_freq("192855", 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.0002055371025188907)
        self.assertEqual(result['concept_count'], 368)

        #   default dataset id
        result = QueryCOHD.get_individual_concept_freq("192855")
        self.assertIsNotNone(result)
        self.assertEqual(result['concept_frequency'], 0.0002055371025188907)
        self.assertEqual(result['concept_count'], 368)

        #   invalid ID value
        result = QueryCOHD.get_individual_concept_freq("0", 1)
        self.assertEqual(result, {})

        #   invalid concept_id type
        result = QueryCOHD.get_individual_concept_freq(2008271, 1)
        self.assertEqual(result, {})

    def test_get_associated_concept_domain_freq(self):
        result = QueryCOHD.get_associated_concept_domain_freq('192855', 'Procedure', 2)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]['concept_frequency'], 0.0002508956097182718)
        self.assertEqual(len(result), 655)

        #   default dataset_id
        result = QueryCOHD.get_associated_concept_domain_freq('192855', 'Procedure')
        self.assertIsNotNone(result)
        self.assertEqual(result[0]['concept_frequency'], 0.00016867447000191573)
        self.assertEqual(len(result), 159)

        #   invalid concept ID value
        result = QueryCOHD.get_associated_concept_domain_freq("0", "drug")
        self.assertEqual(result, [])

        #   invalid domain value
        result = QueryCOHD.get_associated_concept_domain_freq("192855", "dru")
        self.assertEqual(result, [])

        #   invalid concept type
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

        #   invalid concept_id type
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

        #   default distance
        result = QueryCOHD.get_xref_from_OMOP("192855", "UMLS")
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

        #   invalid concept id
        result = QueryCOHD.get_xref_from_OMOP("1928551", "UMLS", 2)
        self.assertEqual(result, [])

        #   invalid mapping_targets
        result = QueryCOHD.get_xref_from_OMOP("1928551", "UMS", 2)
        self.assertEqual(result, [])

        #   invalid distance format
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
        self.assertEqual(result[0], {'intermediate_oxo_id': 'ICD9CM:715.3', 'intermediate_oxo_label': '',
                                     'omop_concept_name': 'Localized osteoarthrosis uncertain if primary OR secondary',
                                     'omop_distance': 1, 'omop_domain_id': 'Condition',
                                     'omop_standard_concept_id': 72990,
                                     'oxo_distance': 1, 'source_oxo_id': 'DOID:8398',
                                     'source_oxo_label': 'osteoarthritis',
                                     'total_distance': 2})

        #   default distance
        result = QueryCOHD.get_xref_to_OMOP("DOID:8398")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

        #   invalid curie id
        result = QueryCOHD.get_xref_to_OMOP("DOID:83981", 2)
        self.assertEqual(result, [])

        #   invalid distance format
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

        #   invalid concept_id id
        result = QueryCOHD.get_map_from_standard_concept_id("DOID:839812", 2)
        self.assertEqual(result, [])

        #   invalid concept_id format
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

        #   invalid concept_code id
        result = QueryCOHD.get_map_from_standard_concept_id("725.3")
        self.assertEqual(result, [])

        #   invalid concept_code format
        result = QueryCOHD.get_map_from_standard_concept_id(725.3)
        self.assertEqual(result, [])

    def test_get_vocabularies(self):
        result = QueryCOHD.get_vocabularies()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 73)
        self.assertEqual(result[0]['vocabulary_id'], 'ABMS')
        self.assertEqual(result[1]['vocabulary_id'], 'AMT')

    def test_get_associated_concept_freq(self):
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

        #   default dataset_id
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

        #   invalid conecpt_id value
        result = QueryCOHD.get_associated_concept_freq("1928551")
        self.assertEqual(result, [])

        #   invalid dataset_id value
        result = QueryCOHD.get_associated_concept_freq("192855", 10)
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
        self.assertEqual(result[0], {'concept_class_id': 'Undefined',
                                     'concept_count': 1189172,
                                     'concept_frequency': 0.6641819762950932,
                                     'concept_id': 44814653,
                                     'concept_name': 'Unknown',
                                     'dataset_id': 1,
                                     'domain_id': 'Observation',
                                     'vocabulary_id': 'PCORNet'})

        #   default dataset_id
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {
                                     'concept_class_id': 'Clinical Finding',
                                     'concept_count': 233790,
                                     'concept_frequency': 0.1305774978203572,
                                     'concept_id': 320128,
                                     'concept_name': 'Essential hypertension',
                                     'dataset_id': 1,
                                     'domain_id': 'Condition',
                                     'vocabulary_id': 'SNOMED'})

        #   no default value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'concept_class_id': 'Clinical Finding',
                                     'concept_count': 459776,
                                     'concept_frequency': 0.08570265962394365,
                                     'concept_id': 320128,
                                     'concept_name': 'Essential hypertension',
                                     'dataset_id': 2,
                                     'domain_id': 'Condition',
                                     'vocabulary_id': 'SNOMED'})

        #   invalid num value
        result = QueryCOHD.get_most_frequent_concepts(-10)
        self.assertEqual(result, [])

        #   invalid num type
        result = QueryCOHD.get_most_frequent_concepts("10")
        self.assertEqual(result, [])

        #   invalid domain value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition1")
        self.assertEqual(result, [])

        #   invalid domain type
        result = QueryCOHD.get_most_frequent_concepts(10, 1, 2)
        self.assertEqual(result, [])

        #   invalid dataset_id value
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", 10)
        self.assertEqual(result, [])

        #   invalid dataset_id type
        result = QueryCOHD.get_most_frequent_concepts(10, "Condition", "2")
        self.assertEqual(result, [])

        # #   num == 0
        # result = QueryCOHD.get_most_frequent_concepts(0, "Condition", 2)
        # self.assertEqual(result, [])

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
        result = QueryCOHD.get_chi_square("192855", "2008271", "condition", 10)
        self.assertEqual(result, [])

    def test_get_obs_exp_ratio(self):
        #   default dataset_id
        result = QueryCOHD.get_obs_exp_ratio("192855", "2008271", "Procedure")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 1,
                                   'expected_count': 0.3070724311632227,
                                   'ln_ratio': 3.483256720088832,
                                   'observed_count': 10}])

        #   dataset_id == 2
        result = QueryCOHD.get_obs_exp_ratio("192855", "2008271", "Procedure", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 2,
                                   'expected_count': 5.171830872499735,
                                   'ln_ratio': 3.634887899455015,
                                   'observed_count': 196}])
        #   default domain
        result = QueryCOHD.get_obs_exp_ratio("192855", "2008271")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 1,
                                   'expected_count': 0.3070724311632227,
                                   'ln_ratio': 3.483256720088832,
                                   'observed_count': 10}])

        #   default domain, dataset_id == 2
        result = QueryCOHD.get_obs_exp_ratio("192855", "2008271", "", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'dataset_id': 2,
                                   'expected_count': 5.171830872499735,
                                   'ln_ratio': 3.634887899455015,
                                   'observed_count': 196}])

        #   default concept_id_2, domain and dataset_id
        result = QueryCOHD.get_obs_exp_ratio("192855")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 768)

        #   default concept_id_2 and domain, dataset_id == 2
        result = QueryCOHD.get_obs_exp_ratio("192855", "", "", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2735)

        #   default concept_id_2 and dataset_id
        result = QueryCOHD.get_obs_exp_ratio("192855", "", "Procedure")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 159)

        #   default concept_id_2
        result = QueryCOHD.get_obs_exp_ratio("192855", "", "Procedure", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 655)

        #   invalid concept_id_1 type
        result = QueryCOHD.get_obs_exp_ratio(192855, "2008271", "", 2)
        self.assertEqual(result, [])

        #   invalid concept_id_2 type
        result = QueryCOHD.get_obs_exp_ratio("192855", 2008271, "", 2)
        self.assertEqual(result, [])

        #   invalid dataset_id type
        result = QueryCOHD.get_obs_exp_ratio("192855", "2008271", "", "2")
        self.assertEqual(result, [])

    def test_get_relative_frequency(self):
        #   default dataset_id
        result = QueryCOHD.get_relative_frequency("192855", "2008271", "Procedure")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_2_count': 1494,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'concept_pair_count': 10,
                                   'dataset_id': 1,
                                   'relative_frequency': 0.006693440428380187}])

        #   dataset_id == 2
        result = QueryCOHD.get_relative_frequency("192855", "2008271", "Procedure", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_2_count': 17127,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'concept_pair_count': 196,
                                   'dataset_id': 2,
                                   'relative_frequency': 0.011443918958369825}])

        #   default domain
        result = QueryCOHD.get_relative_frequency("192855", "2008271")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_2_count': 1494,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'concept_pair_count': 10,
                                   'dataset_id': 1,
                                   'relative_frequency': 0.006693440428380187}])

        #   default domain, dataset_id == 2
        result = QueryCOHD.get_relative_frequency("192855", "2008271", "", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'concept_2_count': 17127,
                                   'concept_id_1': 192855,
                                   'concept_id_2': 2008271,
                                   'concept_pair_count': 196,
                                   'dataset_id': 2,
                                   'relative_frequency': 0.011443918958369825}])

        #   default concept_id_2, domain and dataset_id
        result = QueryCOHD.get_relative_frequency("192855")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 768)

        #   default concept_id_2 and domain, dataset_id == 2
        result = QueryCOHD.get_relative_frequency("192855", "", "", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2735)

        #   default concept_id_2 and dataset_id
        result = QueryCOHD.get_relative_frequency("192855", "", "Procedure")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 159)

        #   default concept_id_2
        result = QueryCOHD.get_relative_frequency("192855", "", "Procedure", 2)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 655)

        #   invalid concept_id_1 type
        result = QueryCOHD.get_relative_frequency(192855, "2008271", "", 2)
        self.assertEqual(result, [])

        #   invalid concept_id_2 type
        result = QueryCOHD.get_relative_frequency("192855", 2008271, "", 2)
        self.assertEqual(result, [])

        #   invalid dataset_id type
        result = QueryCOHD.get_relative_frequency("192855", "2008271", "", "2")
        self.assertEqual(result, [])

    def test_get_datasets(self):
        result = QueryCOHD.get_datasets()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result, [{'dataset_description': "Clinical data from 2013-2017. Each concept's count reflects "
                                                          "the use of that specific concept.",
                                   'dataset_id': 1,
                                   'dataset_name': "5-year non-hierarchical"},
                                  {'dataset_description': "Clinical data from all years in the database. Each concept's"
                                                          " count reflects the use of that specific concept.",
                                   'dataset_id': 2,
                                   'dataset_name': "Lifetime non-hierarchical"},
                                  {
                                    "dataset_description": "Clinical data from 2013-2017. Each concept's count includes"
                                                           " use of that concept and descendant concepts.",
                                    "dataset_id": 3,
                                    "dataset_name": "5-year hierarchical"}
                                  ])

    def test_get_domain_counts(self):
        result = QueryCOHD.get_domain_counts(1)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'count': 10159,
                                     'dataset_id': 1,
                                     'domain_id': 'Condition'})

        #   default dataset_id
        result = QueryCOHD.get_domain_counts()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {'count': 10159,
                                     'dataset_id': 1,
                                     'domain_id': 'Condition'})

        #   invalid dataset_id value
        result = QueryCOHD.get_domain_counts(-1)
        self.assertEqual(result, [])

        #   invalid dataset_id type
        result = QueryCOHD.get_domain_counts("1")
        self.assertEqual(result, [])

    def test_get_domain_pair_counts(self):
        result = QueryCOHD.get_domain_pair_counts(1)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 50)
        self.assertEqual(result[0], {'count': 1933917,
                                     'dataset_id': 1,
                                     'domain_id_1': 'Condition',
                                     'domain_id_2': 'Condition'})

        #   default dataset_id
        result = QueryCOHD.get_domain_pair_counts()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 50)
        self.assertEqual(result[0], {'count': 1933917,
                                     'dataset_id': 1,
                                     'domain_id_1': 'Condition',
                                     'domain_id_2': 'Condition'})

        #   invalid dataset_id value
        result = QueryCOHD.get_domain_pair_counts(-1)
        self.assertEqual(result, [])

        #   invalid dataset_id type
        result = QueryCOHD.get_domain_pair_counts('1')
        self.assertEqual(result, [])

    def test_get_patient_count(self):
        result = QueryCOHD.get_patient_count(2)
        self.assertIsNotNone(result)
        self.assertEqual(result, {'count': 5364781.0, 'dataset_id': 2})

        #   default dataset_id
        result = QueryCOHD.get_patient_count()
        self.assertIsNotNone(result)
        self.assertEqual(result, {'count': 1790431.0, 'dataset_id': 1})

        #   invalid dataset_id value
        result = QueryCOHD.get_patient_count(-1)
        self.assertEqual(result, {})

        #   invalid dataset_id type
        result = QueryCOHD.get_patient_count('1')
        self.assertEqual(result, {})

    def test_get_concept_ancestors(self):
        result = QueryCOHD.get_concept_ancestors('19019073', 'RxNorm', 'Ingredient', 1)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {'ancestor_concept_id': 1177480,
                                     'concept_class_id': 'Ingredient',
                                     'concept_code': '5640',
                                     'concept_count': 174,
                                     'concept_name': 'Ibuprofen',
                                     'domain_id': 'Drug',
                                     'max_levels_of_separation': 2,
                                     'min_levels_of_separation': 2,
                                     'standard_concept': 'S',
                                     'vocabulary_id': 'RxNorm'})

        # default dataset_id
        result = QueryCOHD.get_concept_ancestors('19019073', 'RxNorm', 'Ingredient')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {'ancestor_concept_id': 1177480,
                                     'concept_class_id': 'Ingredient',
                                     'concept_code': '5640',
                                     'concept_count': 233514,
                                     'concept_name': 'Ibuprofen',
                                     'domain_id': 'Drug',
                                     'max_levels_of_separation': 2,
                                     'min_levels_of_separation': 2,
                                     'standard_concept': 'S',
                                     'vocabulary_id': 'RxNorm'})

        # default concept_class_id
        result = QueryCOHD.get_concept_ancestors('19019073', 'RxNorm')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], {
                                      "ancestor_concept_id": 19019073,
                                      "concept_class_id": "Clinical Drug",
                                      "concept_code": "197806",
                                      "concept_count": 121104,
                                      "concept_name": "Ibuprofen 600 MG Oral Tablet",
                                      "domain_id": "Drug",
                                      "max_levels_of_separation": 0,
                                      "min_levels_of_separation": 0,
                                      "standard_concept": "S",
                                      "vocabulary_id": "RxNorm"})

        # default vocabulary_id
        result = QueryCOHD.get_concept_ancestors('19019073')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 8)
        self.assertEqual(result[0], {
            "ancestor_concept_id": 19019073,
            "concept_class_id": "Clinical Drug",
            "concept_code": "197806",
            "concept_count": 121104,
            "concept_name": "Ibuprofen 600 MG Oral Tablet",
            "domain_id": "Drug",
            "max_levels_of_separation": 0,
            "min_levels_of_separation": 0,
            "standard_concept": "S",
            "vocabulary_id": "RxNorm"})

    def test_get_concept_descendants(self):
        result = QueryCOHD.get_concept_descendants('19019073', 'RxNorm', 'Branded Drug', 1)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {
                                      "concept_class_id": "Branded Drug",
                                      "concept_code": "206913",
                                      "concept_count": 14744,
                                      "concept_name": "Ibuprofen 600 MG Oral Tablet [Ibu]",
                                      "descendant_concept_id": 19033921,
                                      "domain_id": "Drug",
                                      "max_levels_of_separation": 0,
                                      "min_levels_of_separation": 0,
                                      "standard_concept": "S",
                                      "vocabulary_id": "RxNorm"})

        # default dataset_id
        result = QueryCOHD.get_concept_descendants('19019073', 'RxNorm', 'Branded Drug')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {
                                      "concept_class_id": "Branded Drug",
                                      "concept_code": "206913",
                                      "concept_count": 14853,
                                      "concept_name": "Ibuprofen 600 MG Oral Tablet [Ibu]",
                                      "descendant_concept_id": 19033921,
                                      "domain_id": "Drug",
                                      "max_levels_of_separation": 0,
                                      "min_levels_of_separation": 0,
                                      "standard_concept": "S",
                                      "vocabulary_id": "RxNorm"})

        # default concept_class_id
        result = QueryCOHD.get_concept_descendants('19019073', 'RxNorm')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], {
                                      "concept_class_id": "Clinical Drug",
                                      "concept_code": "197806",
                                      "concept_count": 121104,
                                      "concept_name": "Ibuprofen 600 MG Oral Tablet",
                                      "descendant_concept_id": 19019073,
                                      "domain_id": "Drug",
                                      "max_levels_of_separation": 0,
                                      "min_levels_of_separation": 0,
                                      "standard_concept": "S",
                                      "vocabulary_id": "RxNorm"})

        # default vocabulary_id
        result = QueryCOHD.get_concept_descendants('19019073')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], {
                                      "concept_class_id": "Clinical Drug",
                                      "concept_code": "197806",
                                      "concept_count": 121104,
                                      "concept_name": "Ibuprofen 600 MG Oral Tablet",
                                      "descendant_concept_id": 19019073,
                                      "domain_id": "Drug",
                                      "max_levels_of_separation": 0,
                                      "min_levels_of_separation": 0,
                                      "standard_concept": "S",
                                      "vocabulary_id": "RxNorm"})

