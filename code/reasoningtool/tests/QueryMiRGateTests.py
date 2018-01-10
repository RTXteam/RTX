import unittest
from QueryMiRGate import QueryMiRGate as QMG


class QueryMiRGateTestCase(unittest.TestCase):
    def test_get_microrna_ids_that_regulate_gene_symbol(self):
        res_ids = QMG.get_microrna_ids_that_regulate_gene_symbol('HMOX1')
        known_ids = {'MIMAT0002174', 'MIMAT0000077', 'MIMAT0021021', 'MIMAT0023252',
                     'MIMAT0016901', 'MIMAT0019723', 'MIMAT0019941', 'MIMAT0018996',
                     'MIMAT0015029', 'MIMAT0019227', 'MIMAT0014989', 'MIMAT0015078',
                     'MIMAT0005920', 'MIMAT0014978', 'MIMAT0024616', 'MIMAT0019012',
                     'MIMAT0022726', 'MIMAT0018965', 'MIMAT0019913', 'MIMAT0014990',
                     'MIMAT0019028', 'MIMAT0019806', 'MIMAT0015238', 'MIMAT0025852',
                     'MIMAT0019844', 'MIMAT0005905', 'MIMAT0023696', 'MIMAT0005871',
                     'MIMAT0019829', 'MIMAT0019041', 'MIMAT0019699', 'MIMAT0004776',
                     'MIMAT0019218'}

        self.assertSetEqual(res_ids, known_ids)

    def test_get_microrna_ids_that_regulate_gene_symbol(self):
        # TODO
        pass


if __name__ == '__main__':
    unittest.main()
