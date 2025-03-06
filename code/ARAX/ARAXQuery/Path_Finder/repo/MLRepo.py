import sys
import os

import numpy as np
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from feature_extractor import get_neighbors_info
from feature_extractor import get_np_array_features
from repo.Repository import Repository
from repo.NodeDegreeRepo import NodeDegreeRepo
from repo.NGDRepository import NGDRepository
from model.Node import Node


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class MLRepo(Repository):

    def __init__(self, repo, degree_repo=NodeDegreeRepo(), ngd_repo=NGDRepository(),
                 node_synonymizer=NodeSynonymizer()):
        self.repo = repo
        self.degree_repo = degree_repo
        self.ngd_repo = ngd_repo
        self.node_synonymizer = node_synonymizer
        self.sorted_category_list = ['Activity', 'Agent', 'AnatomicalEntity', 'Behavior', 'BehavioralFeature',
                                     'BiologicalEntity', 'BiologicalProcess', 'Cell', 'CellLine', 'CellularComponent',
                                     'ChemicalEntity', 'ChemicalMixture', 'ClinicalAttribute', 'Cohort',
                                     'ComplexMolecularMixture', 'Device', 'Disease', 'DiseaseOrPhenotypicFeature',
                                     'Drug', 'EnvironmentalProcess', 'Event', 'Exon', 'Food', 'Gene', 'GeneFamily',
                                     'GenomicEntity', 'GeographicLocation', 'GrossAnatomicalStructure', 'Human',
                                     'IndividualOrganism', 'InformationContentEntity', 'LifeStage', 'MaterialSample',
                                     'MicroRNA', 'MolecularActivity', 'MolecularEntity', 'MolecularMixture',
                                     'NamedThing', 'NoncodingRNAProduct', 'NucleicAcidEntity', 'OrganismAttribute',
                                     'OrganismTaxon', 'PathologicalProcess', 'Pathway', 'Phenomenon',
                                     'PhenotypicFeature', 'PhysicalEntity', 'PhysiologicalProcess', 'Polypeptide',
                                     'PopulationOfIndividualOrganisms', 'Procedure', 'Protein', 'Publication',
                                     'RNAProduct', 'RetrievalSource', 'SmallMolecule', 'Transcript', 'Treatment']
        self.edge_category_to_idx = {'biolink:related_to': 0, 'biolink:close_match': 1, 'biolink:subclass_of': 2,
                                     'biolink:interacts_with': 3,
                                     'biolink:treats_or_applied_or_studied_to_treat': 4, 'biolink:affects': 5,
                                     'biolink:has_input': 6,
                                     'biolink:causes': 7, 'biolink:disrupts': 8,
                                     'biolink:preventative_for_condition': 9,
                                     'biolink:predisposes_to_condition': 10, 'biolink:produces': 11,
                                     'biolink:coexists_with': 12,
                                     'biolink:precedes': 13, 'biolink:exacerbates_condition': 14,
                                     'biolink:manifestation_of': 15,
                                     'biolink:located_in': 16, 'biolink:diagnoses': 17, 'biolink:occurs_in': 18,
                                     'biolink:has_participant': 19,
                                     'biolink:in_clinical_trials_for': 20, 'biolink:treats': 21,
                                     'biolink:contraindicated_in': 22,
                                     'biolink:physically_interacts_with': 23, 'biolink:has_metabolite': 24,
                                     'biolink:has_member': 25,
                                     'biolink:has_part': 26, 'biolink:transcribed_from': 27, 'biolink:regulates': 28,
                                     'biolink:gene_associated_with_condition': 29, 'biolink:translates_to': 30,
                                     'biolink:enables': 31,
                                     'biolink:actively_involved_in': 32, 'biolink:capable_of': 33,
                                     'biolink:colocalizes_with': 34,
                                     'biolink:in_taxon': 35, 'biolink:expressed_in': 36, 'biolink:gene_product_of': 37,
                                     'biolink:directly_physically_interacts_with': 38, 'biolink:contributes_to': 39,
                                     'biolink:applied_to_treat': 40,
                                     'biolink:biomarker_for': 41, 'biolink:overlaps': 42, 'biolink:has_phenotype': 43,
                                     'biolink:same_as': 44,
                                     'biolink:has_output': 45, 'biolink:chemically_similar_to': 46,
                                     'biolink:derives_from': 47,
                                     'biolink:is_sequence_variant_of': 48, 'biolink:associated_with': 49,
                                     'biolink:correlated_with': 50,
                                     'biolink:disease_has_location': 51, 'biolink:exact_match': 52,
                                     'biolink:temporally_related_to': 53,
                                     'biolink:composed_primarily_of': 54, 'biolink:has_plasma_membrane_part': 55,
                                     'biolink:has_not_completed': 56,
                                     'biolink:develops_from': 57, 'biolink:has_increased_amount': 58,
                                     'biolink:lacks_part': 59,
                                     'biolink:has_decreased_amount': 60, 'biolink:opposite_of': 61,
                                     'biolink:beneficial_in_models_for': 62,
                                     'biolink:disease_has_basis_in': 63,
                                     'biolink:indirectly_physically_interacts_with': 64}
        self.category_to_idx = {cat_name: idx for idx, cat_name in enumerate(self.sorted_category_list)}

    def get_neighbors(self, node, limit=-1):
        if limit <= 0:
            raise Exception(f"The limit:{limit} could not be negative or zero.")
        content_by_curie = get_neighbors_info(node.id, self.ngd_repo, self.repo)

        if content_by_curie is None:
            return []

        X_list = []
        curie_list = []
        for key, value in content_by_curie.items():
            curie_list.append(key)
            X_list.append(get_np_array_features(value, self.category_to_idx, self.edge_category_to_idx))

        X = np.empty((len(X_list), 125), dtype=float)

        for i in range(len(X_list)):
            X[i] = X_list[i]

        dtest = xgb.DMatrix(X)

        bst_loaded = xgb.Booster()
        bst_loaded.load_model(os.path.dirname(os.path.abspath(__file__)) + '/pathfinder_xgboost_model')

        scores = bst_loaded.predict(dtest)

        probabilities = sigmoid(scores)

        ranked_items = sorted(
            zip(curie_list, probabilities),
            key=lambda x: x[1],
            reverse=True
        )

        return [Node(id=item[0], weight=float(item[1])) for item in
                ranked_items[0:limit]]

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
