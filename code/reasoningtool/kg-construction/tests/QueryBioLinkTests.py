import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryBioLink import QueryBioLink as QBL


def get_from_test_file(key):
    f = open('query_test_data.json', 'r')
    test_data = f.read()
    try:
        test_data_dict = json.loads(test_data)
        f.close()
        return test_data_dict[key]
    except ValueError:
        f.close()
        return None


class QueryBioLinkTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):
        result = QBL.get_anatomy_entity('UBERON:0004476')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertDictEqual(json.loads(result), json.loads(get_from_test_file('UBERON:0004476')))

        # invalid id, code == 500
        result = QBL.get_anatomy_entity('UBERON:000447600')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_phenotype_entity(self):
        result = QBL.get_phenotype_entity('HP:0011515')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('HP:0011515')))

        # invalid id, code == 500
        result = QBL.get_phenotype_entity('HP:00115150')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_disease_entity(self):
        result = QBL.get_disease_entity('DOID:3965')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('DOID:3965')))

        # invalid id, code == 500
        result = QBL.get_disease_entity('DOID:39650')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_bio_process_entity(self):
        result = QBL.get_bio_process_entity('GO:0097289')
        self.assertIsNotNone(result)
        if result != "None":
            self.assertEqual(json.loads(result), json.loads(get_from_test_file('GO:0097289')))

        # invalid id, code == 500
        result = QBL.get_bio_process_entity('GO:00972890')
        self.assertIsNotNone(result)
        self.assertEqual(result, "None")

    def test_get_label_for_disease(self):
        # unknown_resp = QBL.get_label_for_disease('XXX')
        # self.assertEqual(unknown_resp, 'UNKNOWN')

        chlr_label = QBL.get_label_for_disease('DOID:1498')  # cholera
        #  self.assertIsNone(chlr_label)
        self.assertEqual(chlr_label, "cholera")

        pd_label = QBL.get_label_for_disease('OMIM:605543')  # Parkinson’s disease 4
        self.assertEqual(pd_label, "autosomal dominant Parkinson disease 4")

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
        known_list = ['HP:0000003', 'HP:0000023', 'HP:0000054', 'HP:0000062',
                      'HP:0000089', 'HP:0000105', 'HP:0000110', 'HP:0000171',
                      'HP:0000204', 'HP:0000248', 'HP:0000256', 'HP:0000286',
                      'HP:0000348', 'HP:0000358', 'HP:0000369', 'HP:0000377',
                      'HP:0000470', 'HP:0000695', 'HP:0000773', 'HP:0000774',
                      'HP:0000800', 'HP:0000882', 'HP:0000888', 'HP:0000895',
                      'HP:0001169', 'HP:0001274', 'HP:0001302', 'HP:0001320',
                      'HP:0001360', 'HP:0001395', 'HP:0001405', 'HP:0001511',
                      'HP:0001538', 'HP:0001539', 'HP:0001541', 'HP:0001561',
                      'HP:0001629', 'HP:0001631', 'HP:0001643', 'HP:0001655',
                      'HP:0001744', 'HP:0001762', 'HP:0001769', 'HP:0001773',
                      'HP:0001789', 'HP:0001831', 'HP:0002023', 'HP:0002089',
                      'HP:0002093', 'HP:0002240', 'HP:0002323', 'HP:0002350',
                      'HP:0002557', 'HP:0002566', 'HP:0002979', 'HP:0002980',
                      'HP:0003016', 'HP:0003022', 'HP:0003026', 'HP:0003038',
                      'HP:0003811', 'HP:0005054', 'HP:0005257', 'HP:0005349',
                      'HP:0005766', 'HP:0005817', 'HP:0005873', 'HP:0006426',
                      'HP:0006488', 'HP:0006610', 'HP:0006956', 'HP:0008501',
                      'HP:0008873', 'HP:0009381', 'HP:0010306', 'HP:0010442',
                      'HP:0010454', 'HP:0010579', 'HP:0012368', 'HP:0100259',
                      'HP:0100750']


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
        known_list = ['HGNC:1298', 'ENSEMBL:ENSG00000221639', 'HGNC:6357', 'HGNC:37207',
                      'HGNC:378', 'MGI:108094', 'HGNC:40742', 'MGI:3694898', 'MGI:3697701',
                      'HGNC:16713', 'ENSEMBL:ENSG00000260329', 'MGI:1351502', 'MGI:1277193',
                      'MGI:1914926', 'HGNC:6081', 'HGNC:29161', 'HGNC:16523', 'HGNC:16015',
                      'MGI:1920185', 'HGNC:24483', 'HGNC:2458', 'HGNC:23472', 'HGNC:25538',
                      'MGI:1924233', 'HGNC:31602', 'HGNC:7517', 'HGNC:28510', 'HGNC:9772',
                      'HGNC:41140', 'HGNC:4057', 'HGNC:17407', 'HGNC:29859', 'HGNC:51653',
                      'HGNC:20711', 'MGI:88588', 'MGI:3642232', 'HGNC:42000', 'MGI:1916998',
                      'HGNC:491', 'HGNC:28177', 'MGI:2177763', 'MGI:1914721', 'HGNC:18003',
                      'HGNC:13812', 'HGNC:23817', 'HGNC:13452', 'MGI:2148019', 'HGNC:3391',
                      'HGNC:15518', 'HGNC:28145', 'MGI:96432', 'HGNC:23488', 'ENSEMBL:ENSG00000233895',
                      'HGNC:28695', 'MGI:3036267', 'MGI:5477162', 'MGI:88175', 'HGNC:10808',
                      'HGNC:23467', 'MGI:109589', 'HGNC:26777', 'MGI:108471', 'HGNC:3528', 'HGNC:18817',
                      'ENSEMBL:ENSG00000177764', 'HGNC:5192', 'MGI:109124', 'MGI:1336885', 'MGI:88610',
                      'HGNC:25629', 'HGNC:17859', 'MGI:2685955', 'HGNC:21222', 'HGNC:52164', 'HGNC:29612',
                      'HGNC:24913', 'MGI:2159649', 'HGNC:6532', 'HGNC:29125', 'HGNC:1706', 'MGI:1917904',
                      'HGNC:1388', 'HGNC:1960', 'ENSEMBL:ENSG00000260526', 'HGNC:16275', 'MGI:1922469',
                      'HGNC:3518', 'HGNC:6172', 'MGI:97010', 'ENSEMBL:ENSG00000121848', 'HGNC:24045',
                      'HGNC:6003', 'HGNC:24172', 'MGI:2429955', 'HGNC:6130', 'MGI:1927126', 'HGNC:11513',
                      'MGI:1922935', 'MGI:1922977', 'HGNC:26460']

        # Sequence does not matter here
        self.assertSetEqual(set(iol_list), set(known_list))

    def test_get_anatomies_for_phenotype(self):
        mcd_dict = QBL.get_anatomies_for_phenotype('HP:0000003')  # Multicystic kidney dysplasia

        known_dict = {'UBERON:0002113': 'kidney'}

        self.assertDictEqual(mcd_dict, known_dict)

    def test_map_disease_to_phenotype(self):

        results = QBL.map_disease_to_phenotype("OMIM:605543")
        self.assertIsNotNone(results)
        self.assertEqual(['HP:0000726', 'HP:0000738', 'HP:0001278', 'HP:0001300',
                          'HP:0001824', 'HP:0002459', 'HP:0011999', 'HP:0100315'], results)

        results = QBL.map_disease_to_phenotype("DOID:3218")
        self.assertIsNotNone(results)
        self.assertEqual(57, len(results))

        #   invalid parameter
        results = QBL.map_disease_to_phenotype(605543)
        self.assertEqual([], results)

        #   invalid parameter
        results = QBL.map_disease_to_phenotype("OMIM_605543")
        self.assertEqual([], results)

        #   invalid parameter
        results = QBL.map_disease_to_phenotype("DOID_14477")
        self.assertEqual([], results)

if __name__ == '__main__':
    unittest.main()