import unittest
from QueryUniprot import QueryUniprot


class QueryUniprotTestCase(unittest.TestCase):
    def test_uniprot_id_to_reactome_pathways(self):
        res_set = QueryUniprot.uniprot_id_to_reactome_pathways("P68871")
        known_set = {'R-HSA-983231', 'R-HSA-2168880', 'R-HSA-1237044',
                     'R-HSA-6798695', 'R-HSA-1247673'}

        self.assertSetEqual(res_set, known_set)


if __name__ == '__main__':
    unittest.main()
