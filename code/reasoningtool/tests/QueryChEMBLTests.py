import unittest
from QueryChEMBL import QueryChEMBL as QC


class QueryChEMBLTestCase(unittest.TestCase):
    def test_get_target_uniprot_ids_for_drug(self):
        ret_dict = QC.get_target_uniprot_ids_for_drug('clothiapine')

        known_dict = {'P21728': 0.99999999997, 'P21918': 0.9999999824,
                      'P14416': 0.99996980427, 'P35367': 0.99996179618,
                      'P08913': 0.99973447457, 'P18089': 0.99638618971,
                      'P21917': 0.99500274146, 'P28335': 0.98581821496,
                      'P18825': 0.97356918354, 'P28223': 0.96867458111,
                      'Q9H3N8': 0.83028164473, 'P34969': 0.39141293908,
                      'P41595': 0.31891025293, 'P08173': 0.18274693348,
                      'P11229': 0.16526971365, 'P04637': 0.12499267788,
                      'P35462': 0.11109632984, 'P10635': 0.09162534744,
                      'P25100': 0.0855003718, 'P06746': 0.04246537619}
        self.assertDictEqual(ret_dict, known_dict)

    def test_get_chembl_ids_for_drug(self):
        ret_set = QC.get_chembl_ids_for_drug('clothiapine')

        known_set = {'CHEMBL304902'}

        self.assertSetEqual(ret_set, known_set)

    def test_get_target_uniprot_ids_for_chembl_id(self):
        ret_dict = QC.get_target_uniprot_ids_for_chembl_id('CHEMBL304902')

        known_dict = {'P21728': 0.99999999997, 'P21918': 0.9999999824,
                      'P14416': 0.99996980427, 'P35367': 0.99996179618,
                      'P08913': 0.99973447457, 'P18089': 0.99638618971,
                      'P21917': 0.99500274146, 'P28335': 0.98581821496,
                      'P18825': 0.97356918354, 'P28223': 0.96867458111,
                      'Q9H3N8': 0.83028164473, 'P34969': 0.39141293908,
                      'P41595': 0.31891025293, 'P08173': 0.18274693348,
                      'P11229': 0.16526971365, 'P04637': 0.12499267788,
                      'P35462': 0.11109632984, 'P10635': 0.09162534744,
                      'P25100': 0.0855003718, 'P06746': 0.04246537619}

        self.assertDictEqual(ret_dict, known_dict)


if __name__ == '__main__':
    unittest.main()
