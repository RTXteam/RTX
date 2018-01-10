import unittest
from QueryReactome import QueryReactome


# TODO complete tests for other functions
class QueryReactomeTestCase(unittest.TestCase):
    def test_query_uniprot_id_to_interacting_uniprot_ids_desc(self):
        res_uniprot_ids = QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('P68871')
        known_ids = {'P69905': 'HBA', 'P02008': 'HBAZ'}

        self.assertDictEqual(res_uniprot_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
