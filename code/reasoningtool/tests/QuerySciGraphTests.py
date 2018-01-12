import unittest
from QuerySciGraph import QuerySciGraph


class QuerySciGraphTestCase(unittest.TestCase):
    def test_get_disont_ids_for_mesh_id(self):
        disont_ids = QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D005199')
        known_ids = {'DOID:13636'}
        self.assertSetEqual(disont_ids, known_ids)

    def test_query_sub_phenotypes_for_phenotype(self):
        sub_phenotypes = QuerySciGraph.query_sub_phenotypes_for_phenotype("HP:0000107")  # Renal cyst
        known_phenotypes = {'HP:0100877': 'Renal diverticulum',
                            'HP:0000108': 'Renal corticomedullary cysts',
                            'HP:0000803': 'Renal cortical cysts',
                            'HP:0000003': 'Multicystic kidney dysplasia',
                            'HP:0008659': 'Multiple small medullary renal cysts',
                            'HP:0005562': 'Multiple renal cysts',
                            'HP:0000800': 'Cystic renal dysplasia',
                            'HP:0012581': 'Solitary renal cyst'}
        self.assertDictEqual(sub_phenotypes, known_phenotypes)


if __name__ == '__main__':
    unittest.main()
