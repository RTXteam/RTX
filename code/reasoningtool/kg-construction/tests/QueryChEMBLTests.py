from unittest import TestCase

import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)

from QueryChEMBL import QueryChEMBL as QC


class QueryChEMBLTestCase(TestCase):
    def test_get_target_uniprot_ids_for_drug(self):
        ret_dict = QC.get_target_uniprot_ids_for_drug('clothiapine')
        known_dict = {'P21728': 0.99999999997, 'P35367': 0.99999999054,
                      'P21918': 0.9999999767, 'P08913': 0.99999695255,
                      'P18089': 0.99998657797, 'P14416': 0.99996045438,
                      'P28335': 0.99952615973, 'P25100': 0.99889195616,
                      'P21917': 0.99620734915, 'P18825': 0.9579773931,
                      'P08173': 0.93840796993, 'P41595': 0.87085390914,
                      'P08912': 0.65816349122, 'P28223': 0.6120003276,
                      'P34969': 0.28285795246, 'P35348': 0.28214156802,
                      'P04637': 0.20348218778, 'P11229': 0.17088734668,
                      'P10635': 0.14031224569, 'P06746': 0.06658649159}
        for key, value in ret_dict.items():
            self.assertLess(abs(value - known_dict[key]), 0.1)

        #   empty string
        ret_dict = QC.get_target_uniprot_ids_for_drug('')
        self.assertDictEqual(ret_dict, {})

        #   invalid parameter type
        ret_dict = QC.get_target_uniprot_ids_for_drug(0)
        self.assertDictEqual(ret_dict, {})


    def test_get_chembl_ids_for_drug(self):
        ret_set = QC.get_chembl_ids_for_drug('clothiapine')
        known_set = {'CHEMBL304902'}
        self.assertSetEqual(ret_set, known_set)

        #   empty string
        ret_set = QC.get_chembl_ids_for_drug('')
        self.assertEqual(ret_set, set())

        #   invalid parameter type
        ret_set = QC.get_chembl_ids_for_drug(0)
        self.assertEqual(ret_set, set())

    def test_get_target_uniprot_ids_for_chembl_id(self):
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('CHEMBL304902')

        known_dict = {'P21728': 0.99999999997, 'P35367': 0.99999999054,
                      'P21918': 0.9999999767, 'P08913': 0.99999695255,
                      'P18089': 0.99998657797, 'P14416': 0.99996045438,
                      'P28335': 0.99952615973, 'P25100': 0.99889195616,
                      'P21917': 0.99620734915, 'P18825': 0.9579773931,
                      'P08173': 0.93840796993, 'P41595': 0.87085390914,
                      'P08912': 0.65816349122, 'P28223': 0.6120003276,
                      'P34969': 0.28285795246, 'P35348': 0.28214156802,
                      'P04637': 0.20348218778, 'P11229': 0.17088734668,
                      'P10635': 0.14031224569, 'P06746': 0.06658649159}

        for key, value in ret_dict.items():
            self.assertLess(abs(value - known_dict[key]), 0.1)

        #   empty string
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('')
        self.assertDictEqual(ret_dict, {})

        #   invalid parameter type
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id(0)
        self.assertDictEqual(ret_dict, {})