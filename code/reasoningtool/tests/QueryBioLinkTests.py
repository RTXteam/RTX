import unittest
from QueryBioLink import QueryBioLink as QBL


class QueryBioLinkTestCase(unittest.TestCase):
    def test_get_label_for_disease(self):
        # unknown_resp = QBL.get_label_for_disease('XXX')
        # self.assertEqual(unknown_resp, 'UNKNOWN')

        chlr_label = QBL.get_label_for_disease('DOID:1498')  # cholera
        self.assertIsNone(chlr_label)

        pd_label = QBL.get_label_for_disease('OMIM:605543')  # Parkinson’s disease 4
        self.assertEqual(pd_label, "Parkinson Disease 4, Autosomal Dominant")

    def test_get_phenotypes_for_disease_desc(self):
        ret_dict = QBL.get_phenotypes_for_disease_desc('OMIM:605543')  # Parkinson’s disease 4

        known_dict = {'HP:0000726': 'Dementia',
                      'HP:0001824': 'Weight loss',
                      'HP:0002459': 'Dysautonomia',
                      'HP:0100315': 'Lewy bodies',
                      'HP:0011999': 'Paranoia',
                      'HP:0001278': 'Orthostatic hypotension',
                      'HP:0000738': 'Hallucinations',
                      'HP:0001300': 'Parkinsonism'}

        self.assertDictEqual(ret_dict, known_dict)

    def test_get_diseases_for_gene_desc(self):
        empty_dict = QBL.get_diseases_for_gene_desc('NCBIGene:407053')  # MIR96
        self.assertEqual(len(empty_dict), 0)

        # TODO find an NCBIGene that `get_diseases_for_gene_desc` would return a non-empty result

    def test_get_genes_for_disease_desc(self):
        pd_genes = QBL.get_genes_for_disease_desc('OMIM:605543')  # Parkinson’s disease 4
        self.assertEqual(len(pd_genes), 1)
        self.assertEqual(pd_genes[0], 'HGNC:11138')

    def test_get_label_for_phenotype(self):
        mcd_label = QBL.get_label_for_phenotype('HP:0000003')  # Multicystic kidney dysplasia
        self.assertEqual(mcd_label, "Multicystic kidney dysplasia")

    def test_get_phenotypes_for_gene(self):
        # NEK1, NIMA related kinase 1
        nek1_list = QBL.get_phenotypes_for_gene('NCBIGene:4750')

        known_list = ['HP:0000003', 'HP:0000054', 'HP:0000062', 'HP:0000105',
                      'HP:0000110', 'HP:0000171', 'HP:0000204', 'HP:0000248',
                      'HP:0000773', 'HP:0000774', 'HP:0000888', 'HP:0000895',
                      'HP:0001274', 'HP:0001302', 'HP:0001320', 'HP:0001395',
                      'HP:0001629', 'HP:0001631', 'HP:0001762', 'HP:0001789',
                      'HP:0002023', 'HP:0002089', 'HP:0002350', 'HP:0002566',
                      'HP:0002980', 'HP:0003016', 'HP:0003022', 'HP:0003038',
                      'HP:0005054', 'HP:0005257', 'HP:0005349', 'HP:0005766',
                      'HP:0005817', 'HP:0005873', 'HP:0006426', 'HP:0006956',
                      'HP:0010454', 'HP:0010579', 'HP:0100259']

        # Sequence does not matter here
        self.assertSetEqual(set(nek1_list), set(known_list))

    def test_get_phenotypes_for_gene_desc(self):
        # Test for issue #22
        # CFTR, cystic fibrosis transmembrane conductance regulator
        cftr_dict = QBL.get_phenotypes_for_gene_desc('NCBIGene:1080')

        known_dict = {'HP:0000952': 'Jaundice',
                      'HP:0011227': 'Elevated C-reactive protein level',
                      'HP:0030247': 'Splanchnic vein thrombosis',
                      'HP:0012379': 'Abnormal enzyme/coenzyme activity',
                      'HP:0001974': 'Leukocytosis'}

        self.assertDictEqual(cftr_dict, known_dict)

    def test_get_anatomies_for_gene(self):
        mir96_dict = QBL.get_anatomies_for_gene('NCBIGene:407053')  # MIR96

        known_dict = {'UBERON:0000007': 'pituitary gland',
                      'UBERON:0001301': 'epididymis',
                      'UBERON:0000074': 'renal glomerulus',
                      'UBERON:0000006': 'islet of Langerhans'}

        self.assertDictEqual(mir96_dict, known_dict)

    def test_get_genes_for_anatomy(self):
        iol_list = QBL.get_genes_for_anatomy('UBERON:0000006')  # islet of Langerhans

        known_list = ['MGI:1929735', 'HGNC:28826', 'HGNC:31579', 'HGNC:28995',
                      'HGNC:24172', 'HGNC:6130', 'MGI:2429955', 'MGI:1922935',
                      'MGI:1927126', 'HGNC:11513', 'MGI:3647725', 'HGNC:1960',
                      'MGI:1922977', 'HGNC:6172', 'MGI:1922469', 'HGNC:3518',
                      'MGI:97010', 'ENSEMBL:ENSG00000237404', 'HGNC:20253',
                      'HGNC:14676', 'MGI:1915416', 'MGI:1891697', 'HGNC:30237',
                      'HGNC:12970', 'HGNC:30766', 'HGNC:51534', 'ENSEMBL:ENSG00000271946',
                      'HGNC:17013', 'HGNC:25481', 'MGI:104755', 'MGI:1336199',
                      'ENSEMBL:ENSG00000261159', 'MGI:98003', 'MGI:1916344', 'HGNC:28412',
                      'MGI:88082', 'MGI:2656825', 'MGI:1918345', 'HGNC:20189', 'HGNC:33526',
                      'HGNC:31481', 'ENSEMBL:ENSG00000248632', 'MGI:3615306', 'MGI:109177',
                      'HGNC:2697', 'MGI:1342304', 'HGNC:3816', 'HGNC:11656', 'HGNC:29332',
                      'HGNC:6294', 'HGNC:13787', 'HGNC:18994', 'MGI:2387188', 'MGI:3584508',
                      'ENSEMBL:ENSG00000244306', 'HGNC:29101', 'MGI:1919247', 'HGNC:23433',
                      'HGNC:31393', 'MGI:1347084', 'MGI:1316650', 'MGI:2179507', 'MGI:96163',
                      'MGI:2146012', 'MGI:1916043', 'HGNC:10435', 'HGNC:48629', 'HGNC:23094',
                      'HGNC:25139', 'MGI:2444946', 'HGNC:34236', 'HGNC:26466', 'HGNC:3725',
                      'MGI:2141207', 'HGNC:50580', 'HGNC:18294', 'HGNC:33754', 'MGI:1924150',
                      'HGNC:12499', 'HGNC:17451', 'NCBIGene:100506691', 'HGNC:2522',
                      'MGI:106199', 'HGNC:17811', 'HGNC:8001', 'ENSEMBL:ENSG00000167765',
                      'HGNC:33520', 'HGNC:7200', 'HGNC:11996', 'HGNC:29503', 'HGNC:30021',
                      'MGI:2139593', 'HGNC:24825', 'ENSEMBL:ENSMUSG00000093459',
                      'ENSEMBL:ENSG00000265179', 'HGNC:18696', 'MGI:5504148', 'HGNC:1553',
                      'MGI:1353654', 'MGI:88139']

        # Sequence does not matter here
        self.assertSetEqual(set(iol_list), set(known_list))

    def test_get_anatomies_for_phenotype(self):
        mcd_dict = QBL.get_anatomies_for_phenotype('HP:0000003')  # Multicystic kidney dysplasia

        known_dict = {'UBERON:0002113': 'kidney'}

        self.assertDictEqual(mcd_dict, known_dict)


if __name__ == '__main__':
    unittest.main()
