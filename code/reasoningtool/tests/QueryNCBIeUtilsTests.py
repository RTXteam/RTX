import unittest
from QueryNCBIeUtils import QueryNCBIeUtils


class QueryNCBIeUtilsTestCase(unittest.TestCase):
    def test_get_clinvar_uids_for_disease_or_phenotype_string(self):
        res_set = QueryNCBIeUtils.get_clinvar_uids_for_disease_or_phenotype_string("Parkinson's disease")
        # TODO too many IDs in the result; how to evaluate the correctness?
        self.assertTrue(len(res_set) > 0)

    def test_get_mesh_uids_for_mesh_term(self):
        res_uid = QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Leukemia, Promyelocytic, Acute')
        known_uid = ['68015473']
        self.assertListEqual(res_uid, known_uid)

    def test_get_mesh_uid_for_medgen_uid(self):
        mesh_uid = QueryNCBIeUtils.get_mesh_uid_for_medgen_uid(41393)
        known_uid = {68003550}
        self.assertSetEqual(mesh_uid, known_uid)

    def test_get_mesh_terms_for_mesh_uid(self):
        mesh_terms = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(68003550)
        known_terms = ['Cystic Fibrosis', 'Fibrosis, Cystic', 'Mucoviscidosis',
                       'Pulmonary Cystic Fibrosis', 'Cystic Fibrosis, Pulmonary',
                       'Pancreatic Cystic Fibrosis', 'Cystic Fibrosis, Pancreatic',
                       'Fibrocystic Disease of Pancreas', 'Pancreas Fibrocystic Disease',
                       'Pancreas Fibrocystic Diseases', 'Cystic Fibrosis of Pancreas']
        self.assertSetEqual(set(mesh_terms), set(known_terms))

    def test_get_mesh_terms_for_omim_id(self):
        mesh_terms = QueryNCBIeUtils.get_mesh_terms_for_omim_id(219700)  # OMIM preferred name: "CYSTIC FIBROSIS"
        known_terms = ['Cystic Fibrosis', 'Fibrosis, Cystic', 'Mucoviscidosis',
                       'Pulmonary Cystic Fibrosis', 'Cystic Fibrosis, Pulmonary',
                       'Pancreatic Cystic Fibrosis', 'Cystic Fibrosis, Pancreatic',
                       'Fibrocystic Disease of Pancreas', 'Pancreas Fibrocystic Disease',
                       'Pancreas Fibrocystic Diseases', 'Cystic Fibrosis of Pancreas']
        self.assertSetEqual(set(mesh_terms), set(known_terms))

    def test_get_medgen_uid_for_omim_id(self):
        medgen_ids = QueryNCBIeUtils.get_medgen_uid_for_omim_id(219550)
        known_ids = {346587}
        self.assertSetEqual(medgen_ids, known_ids)

    def test_get_pubmed_hits_count(self):
        hits = QueryNCBIeUtils.get_pubmed_hits_count('"Cholera"[MeSH Terms]')
        self.assertEqual(hits, 8104)

    def test_normalized_google_distance(self):
        ngd = QueryNCBIeUtils.normalized_google_distance("Cystic Fibrosis", "Cholera")
        self.assertAlmostEqual(ngd, 0.69697006)

    def test_is_mesh_term(self):
        self.assertTrue(QueryNCBIeUtils.is_mesh_term("Cholera"))
        self.assertFalse(QueryNCBIeUtils.is_mesh_term("Foo"))





if __name__ == '__main__':
    unittest.main()
