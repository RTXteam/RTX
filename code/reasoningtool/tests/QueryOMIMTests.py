import unittest
from QueryOMIM import QueryOMIM


class QueryOMIMTestCase(unittest.TestCase):
    def setUp(self):
        self.qo = QueryOMIM()

    # test issue 1
    def test_disease_mim_to_gene_symbols_and_uniprot_ids(self):
        ret_dict = self.qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603918')
        known_dict = {'gene_symbols': set(), 'uniprot_ids': set()}

        self.assertDictEqual(ret_dict, known_dict)


if __name__ == '__main__':
    unittest.main()
