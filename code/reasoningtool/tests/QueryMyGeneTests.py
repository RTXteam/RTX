import unittest
from QueryMyGene import QueryMyGene


class QueryMyGeneTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mg = QueryMyGene()

    def test_convert_gene_symbol_to_uniprot_id(self):
        uniprot_ids = self.mg.convert_gene_symbol_to_uniprot_id('A2M')
        known_ids = {'P01023'}
        self.assertSetEqual(uniprot_ids, known_ids)

    def test_convert_uniprot_id_to_gene_symbol(self):
        gene_symbols = self.mg.convert_uniprot_id_to_gene_symbol('Q05925')
        know_symbols = {'EN1'}
        self.assertSetEqual(gene_symbols, know_symbols)

    def test_convert_uniprot_id_to_entrez_gene_ID(self):
        entrez_ids = self.mg.convert_uniprot_id_to_entrez_gene_ID("P09601")
        known_ids = {3162}
        self.assertSetEqual(entrez_ids, known_ids)

    def test_convert_gene_symbol_to_entrez_gene_ID(self):
        entrez_ids = self.mg.convert_gene_symbol_to_entrez_gene_ID('MIR96')
        known_ids = {407053}
        self.assertSetEqual(entrez_ids, known_ids)

    def test_convert_entrez_gene_ID_to_mirbase_ID(self):
        mirbase_ids = self.mg.convert_entrez_gene_ID_to_mirbase_ID(407053)
        known_ids = {'MI0000098'}
        self.assertSetEqual(mirbase_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
