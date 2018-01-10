import unittest
from QueryDisGeNet import QueryDisGeNet


class QueryDisGeNetTestCase(unittest.TestCase):
    def test_query_mesh_id_to_uniprot_ids_desc(self):
        ret_dict = QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc('D016779')

        known_dict = {'P35228': 'NOS2', 'P17927': 'CR1', 'P01375': 'TNF',
                      'P09601': 'HMOX1', 'P15260': 'IFNGR1', 'P29460': 'IL12B',
                      'Q96D42': 'HAVCR1', 'P05112': 'IL4', 'P17181': 'IFNAR1',
                      'P16671': 'CD36', 'P17948': 'FLT1', 'P03956': 'MMP1',
                      'P15692': 'VEGFA', 'P39060': 'COL18A1', 'P12821': 'ACE',
                      'P01584': 'IL1B', 'P14778': 'IL1R1', 'P29474': 'NOS3',
                      'Q9NR96': 'TLR9', 'P01889': 'HLA-B', 'P03989': 'HLA-B',
                      'P10319': 'HLA-B'}

        self.assertDictEqual(ret_dict, known_dict)

if __name__ == '__main__':
    unittest.main()
