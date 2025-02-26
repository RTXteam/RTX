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
        self.category_to_idx = {cat_name: idx for idx, cat_name in enumerate(self.sorted_category_list)}

    def get_neighbors(self, node, limit=-1):
        if limit <= 0:
            raise Exception(f"The limit:{limit} could not be negative or zero.")
        content_by_curie = get_neighbors_info(node.id, self.node_synonymizer, self.ngd_repo, self.repo)
        X_list = []
        curie_list = []
        for key, value in content_by_curie.items():
            curie_list.append(key)
            X_list.append(get_np_array_features(value, self.category_to_idx))

        X = np.empty((len(X_list), 60), dtype=float)

        for i in range(len(X_list)):
            X[i] = X_list[i]

        dtest = xgb.DMatrix(X)

        bst_loaded = xgb.Booster()
        bst_loaded.load_model(os.path.dirname(os.path.abspath(__file__)) + '/model')

        scores = bst_loaded.predict(dtest)

        ranked_items = sorted(
            zip(curie_list, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [Node(item[0]) for item in
                ranked_items[0:limit]]

    def get_node_degree(self, node):
        return self.degree_repo.get_node_degree(node)
