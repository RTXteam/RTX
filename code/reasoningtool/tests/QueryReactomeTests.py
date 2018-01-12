import unittest
from QueryReactome import QueryReactome


class QueryReactomeTestCase(unittest.TestCase):
    def test_query_uniprot_id_to_reactome_pathway_ids_desc(self):
        uniprot_ids = QueryReactome.query_uniprot_id_to_reactome_pathway_ids_desc('P68871')
        # TODO too many IDs here; how to evaluate correctness
        self.assertTrue(len(uniprot_ids) > 0)

    def test_query_reactome_pathway_id_to_uniprot_ids_desc(self):
        pw_ids = QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc('R-HSA-5423646')
        known_ids = {'P08684': 'CYP3A4',
                     'P20815': 'CYP3A5',
                     'P10620': 'MGST1',
                     'O14880': 'MGST3',
                     'Q99735': 'MGST2',
                     'Q9H4B8': 'DPEP3',
                     'Q9H4A9': 'DPEP2',
                     'P16444': 'DPEP1',
                     'Q16696': 'CYP2A13',
                     'Q03154': 'ACY1',
                     'Q96HD9': 'ACY3',
                     'Q6P531': 'GGT6',
                     'P36269': 'GGT5',
                     'A6NGU5': 'GGT3P',
                     'Q9UJ14': 'GGT7',
                     'P19440': 'GGT1',
                     'P05177': 'CYP1A2',
                     'O95154': 'AKR7A3',
                     'Q8NHP1': 'AKR7L',
                     'O43488': 'AKR7A2'}
        self.assertDictEqual(pw_ids, known_ids)

    def test_query_uniprot_id_to_interacting_uniprot_ids_desc(self):
        res_uniprot_ids = QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('P68871')
        known_ids = {'P69905': 'HBA', 'P02008': 'HBAZ'}

        self.assertDictEqual(res_uniprot_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
