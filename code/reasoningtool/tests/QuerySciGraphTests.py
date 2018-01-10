import unittest
from QuerySciGraph import QuerySciGraph


# TODO complete tests for other functions
class QuerySciGraphTestCase(unittest.TestCase):
    def test_get_disont_ids_for_mesh_id(self):
        disont_ids = QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D005199')
        known_ids = {'DOID:13636'}

        self.assertSetEqual(disont_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
