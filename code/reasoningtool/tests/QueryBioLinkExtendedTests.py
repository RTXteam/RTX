import unittest
from QueryBioLinkExtended import QueryBioLinkExtended as QBLEx


class QueryBioLinkExtendedTestCase(unittest.TestCase):

    def test_get_anatomy_entity(self):
        extended_info_json = QBLEx.get_anatomy_entity('UBERON:0004476')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, '{"xrefs": null, "taxon": {"id": null, "label": null}, "categories": ["anatomical entity"], "types": null, "description": null, "replaced_by": null, "consider": null, "synonyms": [{"val": "set of muscles of shoulder", "xrefs": null, "pred": "synonym"}, {"val": "muscle group of shoulder", "xrefs": null, "pred": "synonym"}], "deprecated": null, "id": "UBERON:0004476", "label": "musculature of shoulder"}')

    def test_get_phenotype_entity(self):
        extended_info_json = QBLEx.get_phenotype_entity('HP:0011515')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, '{"xrefs": null, "taxon": {"id": null, "label": null}, "categories": ["Phenotype"], "types": null, "description": null, "replaced_by": null, "consider": null, "synonyms": null, "deprecated": null, "id": "HP:0011515", "label": "Abnormal stereopsis"}')

    def test_get_disease_entity(self):
        extended_info_json = QBLEx.get_disease_entity('DOID:3965')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, '{"xrefs": null, "taxon": {"id": null, "label": null}, "categories": ["disease", "quality"], "types": null, "description": null, "replaced_by": null, "consider": null, "synonyms": null, "deprecated": null, "id": "DOID:3965", "label": null}')

    def test_get_bio_process_entity(self):
        extended_info_json = QBLEx.get_bio_process_entity('GO:0097289')
        self.assertIsNotNone(extended_info_json)
        self.assertEqual(extended_info_json, '{"taxon": {"id": null, "label": null}, "xrefs": null, "categories": ["cellular process", "biological process"], "deprecated": null, "replaced_by": null, "description": null, "synonyms": [{"val": "alpha-ribazole metabolism", "xrefs": null, "pred": "synonym"}], "types": null, "consider": null, "id": "GO:0097289", "label": "alpha-ribazole metabolic process"}')


if __name__ == '__main__':
    unittest.main()