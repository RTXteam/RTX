import unittest
from QueryMyGene import QueryMyGene


# TODO complete tests for other functions
class QueryMyGeneTestCase(unittest.TestCase):
    def setUp(self):
        self.mg = QueryMyGene()

    def test_convert_gene_symbol_to_uniprot_id(self):
        gene_symbol = self.mg.convert_gene_symbol_to_uniprot_id('A2M')
        known_symbol = {'P01023'}
        self.assertSetEqual(gene_symbol, known_symbol)


if __name__ == '__main__':
    unittest.main()
