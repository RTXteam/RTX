import unittest
from QueryMiRBase import QueryMiRBase as QMB


class QueryMiRBaseTestCase(unittest.TestCase):
    def test_convert_mirbase_id_to_mir_gene_symbol(self):
        res_symbol = QMB.convert_mirbase_id_to_mir_gene_symbol('MIMAT0027666')
        self.assertEqual(res_symbol, "MIR6883")

    def test_convert_mirbase_id_to_mature_mir_ids(self):
        ret_set = QMB.convert_mirbase_id_to_mature_mir_ids('MI0014240')
        known_set = {'MIMAT0015079'}
        self.assertSetEqual(ret_set, known_set)


if __name__ == '__main__':
    unittest.main()
