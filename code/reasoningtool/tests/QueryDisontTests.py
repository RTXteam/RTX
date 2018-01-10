import unittest
from QueryDisont import QueryDisont as QD


class QueryDisontTestCase(unittest.TestCase):
    def test_query_disont_to_child_disonts(self):
        ret_set = QD.query_disont_to_child_disonts('DOID:9352')
        known_set = {11712, 1837, 10182}
        self.assertSetEqual(ret_set, known_set)

    def test_query_disont_to_label(self):
        ret_label = QD.query_disont_to_label("DOID:0050741")
        self.assertEqual(ret_label, "alcohol dependence")

    def test_query_disont_to_child_disonts_desc(self):
        ret_dict = QD.query_disont_to_child_disonts_desc("DOID:9352")  # type 2 diabetes mellitus
        known_dict = {'DOID:1837': 'diabetic ketoacidosis',
                      'DOID:10182': 'diabetic peripheral angiopathy',
                      'DOID:11712': 'lipoatrophic diabetes'}

        self.assertDictEqual(ret_dict, known_dict)


if __name__ == '__main__':
    unittest.main()
