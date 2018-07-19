from unittest import TestCase

import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)

from QueryChEMBL import QueryChEMBL as QC


class QueryChEMBLTestCase(TestCase):
    def test_get_target_uniprot_ids_for_drug(self):

        ret_dict = QC.get_target_uniprot_ids_for_drug('clothiapine')
        known_dict = {'P41595': 1.0, 'P28335': 1.0, 'P28223': 1.0, 'P21917': 1.0,
                      'Q8WXA8': 1.0, 'Q70Z44': 1.0, 'A5X5Y0': 1.0, 'P46098': 1.0,
                      'O95264': 1.0, 'P21728': 0.99999999997, 'P35367': 0.99999999054,
                      'P21918': 0.9999999767, 'P08913': 0.99999695255, 'P18089': 0.99998657797,
                      'P14416': 0.99996045438, 'P25100': 0.99889195616, 'P18825': 0.9579773931,
                      'P08173': 0.93840796993, 'P08912': 0.65816349122, 'P34969': 0.28285795246,
                      'P35348': 0.28214156802, 'P04637': 0.20348218778, 'P11229': 0.17088734668,
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

        # test case CHEMBL304902
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('CHEMBL304902')
        known_dict = {'P28223': 1.0, 'P41595': 1.0, 'P28335': 1.0, 'P21917': 1.0,
                      'P46098': 1.0, 'Q8WXA8': 1.0, 'Q70Z44': 1.0, 'A5X5Y0': 1.0,
                      'O95264': 1.0, 'P21728': 0.99999999997, 'P35367': 0.99999999054,
                      'P21918': 0.9999999767, 'P08913': 0.99999695255, 'P18089': 0.99998657797,
                      'P14416': 0.99996045438, 'P25100': 0.99889195616, 'P18825': 0.9579773931,
                      'P08173': 0.93840796993, 'P08912': 0.65816349122, 'P34969': 0.28285795246,
                      'P35348': 0.28214156802, 'P04637': 0.20348218778, 'P11229': 0.17088734668,
                      'P10635': 0.14031224569, 'P06746': 0.06658649159}
        for key, value in ret_dict.items():
            self.assertLess(abs(value - known_dict[key]), 0.1)

        # test case CHEMBL521 (ibuprofen)
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('CHEMBL521')
        known_dict = {'P23219': 1.0, 'P35354': 1.0, 'P08473': 0.99980037155, 'O00763': 0.99266688751,
                      'Q04609': 0.98942916865, 'P08253': 0.94581002279, 'P17752': 0.91994871445,
                      'P03956': 0.89643421164, 'P42892': 0.87107050119, 'Q9GZN0': 0.86383549859,
                      'P12821': 0.8620779016, 'P15144': 0.85733534851, 'Q9BYF1': 0.83966001458,
                      'P22894': 0.78062167118, 'P14780': 0.65826285102, 'P08254': 0.61116303205,
                      'P37268': 0.25590346332, 'P17655': 0.1909881306, 'P07858': 0.1306186469,
                      'P06734': 0.1130695383, 'P50052': 0.111298188}
        for key, value in ret_dict.items():
            self.assertLess(abs(value - known_dict[key]), 0.1)

        #   empty string
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('')
        self.assertDictEqual(ret_dict, {})

        #   invalid parameter type
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id(0)
        self.assertDictEqual(ret_dict, {})

    def test_get_mechanisms_for_chembl_id(self):

        ret_array = QC.get_mechanisms_for_chembl_id("CHEMBL521")
        self.assertEqual(ret_array[0]['action_type'], 'INHIBITOR')
        self.assertEqual(ret_array[0]['mechanism_of_action'], 'Cyclooxygenase inhibitor')
        self.assertEqual(ret_array[0]['molecule_chembl_id'], 'CHEMBL521')
        self.assertEqual(ret_array[0]['target_chembl_id'], 'CHEMBL2094253')

        #   empty result
        ret_array = QC.get_mechanisms_for_chembl_id('CHEMBL2094253')
        self.assertEqual(ret_array, [])

        #   empty input string
        ret_array = QC.get_mechanisms_for_chembl_id('')
        self.assertEqual(ret_array, [])

        #   invalid parameter type
        ret_array = QC.get_mechanisms_for_chembl_id(0)
        self.assertEqual(ret_array, [])