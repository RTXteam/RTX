from QueryMyChem import QueryMyChem
from SynonymMapper import SynonymMapper

import os, sys

try:
    from QueryUMLSApi import QueryUMLSApi
except ImportError:
    insert_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) + "/../SemMedDB/")
    print(insert_dir)
    sys.path.insert(0, insert_dir)
    from QueryUMLSApi import QueryUMLS


class DrugMapper:

    @staticmethod
    def map_drug_to_hp_with_side_effects(chembl_id):
        """
        mapping between a drug and human phenotypes corresponding to side effects

        :param chembl_id: The CHEMBL ID for a drug

        :return: A set of strings containing the found hp ids or empty set if none where found
        """
        hp_set = set()
        if not isinstance(chembl_id, str):
            return hp_set
        umls_array = QueryMyChem.get_drug_side_effects(chembl_id)
        if len(umls_array) == 0:
            return hp_set
        sm = SynonymMapper()
        for umls_id in umls_array:
            hp_ids = sm.get_all_from_oxo(umls_id, 'HP')
            if hp_ids != None:
                for hp_id in hp_ids:
                    hp_set.add(hp_id)
        return hp_set

    @staticmethod
    def map_drug_to_UMLS_with_indications(chembl_id):
        """
        mapping between a drug and UMLS ids corresponding to indications

        :param chembl_id: The CHEMBL ID for a drug

        :return: A set of strings containing the found UMLS ids or empty set if none where found
        """
        umls_set = set()
        if not isinstance(chembl_id, str):
            return umls_set
        indications = QueryMyChem.get_drug_indications(chembl_id)
        tgt = QueryUMLS.get_ticket_gen()

        for indication in indications:
            if 'snomed_name' in indication.keys():
                cuis = QueryUMLS.get_cuis_from_string_precision(indication['snomed_name'], tgt)
                for cui in cuis:
                    umls_set.add(cui)
        return umls_set

        # print(umls_set)
        # if len(umls_set) == 0:
        #     return hp_set
        # sm = SynonymMapper()
        # for umls_id in umls_set:
        #     hp_ids = sm.get_all_from_oxo(umls_id, 'HP')
        #     if hp_ids != None:
        #         for hp_id in hp_ids:
        #             hp_set.add(hp_id)
        # return hp_set

    @staticmethod
    def map_drug_to_ontology_with_indications(chembl_id):
        """
        mapping between a drug and Disease Ontology IDs and/or Human Phenotype Ontology IDs corresponding to indications

        :param chembl_id: The CHEMBL ID for a drug

        :return: A set of strings containing the found hp ids or empty set if none where found
        """
        hp_onto_set = set()
        disease_onto_set = set()
        if not isinstance(chembl_id, str):
            return {"hp_onto": hp_onto_set, "disease_onto": disease_onto_set}
        indications = QueryMyChem.get_drug_indications(chembl_id)
        sm = SynonymMapper()
        for indication in indications:
            if 'snomed_id' in indication.keys():
                oxo_results = sm.get_all_from_oxo('SNOMEDCT:' + indication['snomed_id'], ['DOID', 'OMIM', 'HP'])
                if oxo_results is not None:
                    for oxo_result in oxo_results:
                        if oxo_result[:4] == "DOID" or oxo_result[:4] == "OMIM":
                            disease_onto_set.add(oxo_result)
                        if oxo_result[:2] == "HP":
                            hp_onto_set.add(oxo_result)
        return {"hp_onto": hp_onto_set, "disease_onto": disease_onto_set}


if __name__ == '__main__':
    hp_set = DrugMapper.map_drug_to_hp_with_side_effects("KWHRDNMACVLHCE-UHFFFAOYSA-N")
    print(hp_set)
    print(len(hp_set))

    hp_set = DrugMapper.map_drug_to_hp_with_side_effects("CHEMBL521")
    print(hp_set)
    print(len(hp_set))

    umls_set = DrugMapper.map_drug_to_UMLS_with_indications("CHEMBL521")
    print(umls_set)

    onto_set = DrugMapper.map_drug_to_ontology_with_indications("CHEMBL521")
    print(onto_set)
