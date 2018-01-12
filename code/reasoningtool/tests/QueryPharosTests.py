import unittest
from QueryPharos import QueryPharos


class QueryPharosTestCase(unittest.TestCase):
    def test_query_drug_name_to_targets(self):
        targets = QueryPharos.query_drug_name_to_targets("lovastatin")
        known_targets = [{'id': 19672, 'name': '3-hydroxy-3-methylglutaryl-coenzyme A reductase'},
                         {'id': 14711, 'name': 'Integrin alpha-L'},
                         {'id': 3939, 'name': 'Farnesyl pyrophosphate synthase'},
                         {'id': 14764, 'name': 'Integrin beta-3'},
                         {'id': 13844, 'name': 'Cytochrome P450 2D6'},
                         {'id': 16824, 'name': 'Prostacyclin receptor'},
                         {'id': 8600, 'name': 'Prostaglandin G/H synthase 2'},
                         {'id': 18746, 'name': 'Cytochrome P450 3A5'},
                         {'id': 17657, 'name': 'Serine/threonine-protein kinase mTOR'},
                         {'id': 7520, 'name': 'C-C chemokine receptor type 5'}]
        self.assertListEqual(targets, known_targets)

    def test_query_target_to_diseases(self):
        diseases = QueryPharos.query_target_to_diseases("16824")
        known_diseases = [{'id': '37', 'name': 'ulcerative colitis'},
                          {'id': '2163', 'name': 'Heart Diseases'},
                          {'id': '574', 'name': 'Asthma, Aspirin-Induced'},
                          {'id': '31', 'name': 'osteosarcoma'},
                          {'id': '95', 'name': 'lung adenocarcinoma'},
                          {'id': '1516', 'name': 'severe asthma'},
                          {'id': '39', 'name': "Crohn's disease"},
                          {'id': '195', 'name': 'Hypertension'},
                          {'id': '1335', 'name': 'Primary pulmonary hypertension'},
                          {'id': '9901', 'name': 'Arteriosclerosis obliterans'},
                          {'id': '4429', 'name': 'Intermittent claudication'},
                          {'id': '192', 'name': 'Atherosclerosis'},
                          {'id': '193', 'name': 'Coronary artery disease'},
                          {'id': '245', 'name': 'pulmonary arterial hypertension'},
                          {'id': '1273', 'name': 'Pulmonary hypertension'},
                          {'id': '3746', 'name': 'Nasal discharge'},
                          {'id': '501', 'name': 'Cough'},
                          {'id': '1371', 'name': 'Nasal congestion'},
                          {'id': '142', 'name': 'Allergic rhinitis'},
                          {'id': '1350', 'name': 'Rhinitis'},
                          {'id': '1024', 'name': 'Common cold'}]
        self.assertListEqual(diseases, known_diseases)

    def test_query_target_to_drugs(self):
        drugs = QueryPharos.query_target_to_drugs("16824")
        known_drugs = [{'id': 8411409, 'name': 'selexipag', 'action': 'AGONIST'},
                       {'id': 8411420, 'name': 'iloprost', 'action': 'AGONIST'},
                       {'id': 8099182, 'name': 'epoprostenol', 'action': 'AGONIST'},
                       {'id': 8411432, 'name': 'beraprost', 'action': 'AGONIST'},
                       {'id': 8411443, 'name': 'treprostinil', 'action': 'AGONIST'}]
        self.assertListEqual(drugs, known_drugs)

    def test_query_drug_to_targets(self):
        targets = QueryPharos.query_drug_to_targets("254599")
        known_targets = [{'id': 10000655, 'name': 'HMGCR'}]
        self.assertListEqual(targets, known_targets)

    def test_query_target_name(self):
        target_name = QueryPharos.query_target_name("16824")
        self.assertEqual(target_name, "Prostacyclin receptor")

    def test_query_target_uniprot_accession(self):
        term = QueryPharos.query_target_uniprot_accession("19672")
        self.assertEqual(term, "P04035")

    def test_query_disease_name(self):
        disease_name = QueryPharos.query_disease_name("501")
        self.assertEqual(disease_name, "Cough")

    def test_query_drug_name(self):
        drug_name = QueryPharos.query_drug_name("254599")
        self.assertEqual(drug_name, "lovastatin")

    def test_query_drug_id_by_name(self):
        drug_id = QueryPharos.query_drug_id_by_name('lovastatin')
        self.assertEqual(drug_id, 254599)

    def test_query_disease_id_by_name(self):
        disease_id = QueryPharos.query_disease_id_by_name("Cough")
        self.assertEqual(disease_id, 501)


if __name__ == '__main__':
    unittest.main()
