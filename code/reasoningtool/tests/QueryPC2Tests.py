import unittest
from QueryPC2 import QueryPC2


class QueryPC2TestCase(unittest.TestCase):
    def test_pathway_id_to_uniprot_ids(self):
        pw_id = QueryPC2.pathway_id_to_uniprot_ids("R-HSA-1480926")
        # TODO find a pathway id such that the return value is not empty
        pass

    def test_uniprot_id_to_reactome_pathways(self):
        ret_set = QueryPC2.uniprot_id_to_reactome_pathways("P68871")
        known_set = {'R-HSA-5653656', 'R-HSA-109582', 'R-HSA-2173782',
                     'R-HSA-168256', 'R-HSA-382551', 'R-HSA-168249', 'R-HSA-1480926'}
        self.assertSetEqual(ret_set, known_set)


if __name__ == '__main__':
    unittest.main()
