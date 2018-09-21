# A collection of scripts to interact with Columbia open health data

import os
import sys
import argparse
import math

# PyCharm doesn't play well with relative imports + python console + terminal
try:
    from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import ReasoningUtilities as RU

import FormatOutput
import networkx as nx

try:
    from QueryCOHD import QueryCOHD
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from QueryCOHD import QueryCOHD

import CustomExceptions


class COHDUtilities:
    def __init__(self):
        None

    @staticmethod
    def get_conditions_treating(drug_description, conservative=False):
        """
        Get all the conditions that are associated with a drug.
        :param drug_description: string (eg. 'Naproxen')
        :param conservative: bool (True= use exact matching for mapping drug to COHD, False = use all synonyms returned by COHD)
        :return: dictionary of dictionaries (eg. keys are concept IDs, values look like:
        {'associated_concept_id': 134736,
        'associated_concept_name': 'Backache',
        'concept_count': 112,
        'concept_frequency': 2.101665438505926e-05,
        'concept_id': 1115008}
        """

        # Get the concept ID of the drug
        drug_concepts = QueryCOHD.find_concept_ids(drug_description)
        drug_ids = []
        if conservative:
            for concept in drug_concepts:
                if concept['concept_name'].lower() == drug_description.lower():
                    drug_ids.append(concept['concept_id'])
        if not conservative:
            for concept in drug_concepts:
                drug_ids.append(concept['concept_id'])

        # get all the associated conditions
        associated_concepts = []
        for drug_id in drug_ids:
            associated_concepts += QueryCOHD.get_associated_concept_domain_freq(str(drug_id), "Condition")
        print(len(associated_concepts))

        # go through and sum them all up (no need for conservative flag since that will only be a single one)
        # get all the unique condition ids
        associated_concept_ids = set()
        for concept in associated_concepts:
            associated_concept_ids.add(concept['associated_concept_id'])

        # go through the associated conditions, summing up the concept counts
        result_dict = dict()
        for associated_concept in associated_concepts:
            id = associated_concept['associated_concept_id']
            if id in result_dict:
                result_dict[id]['concept_count'] += associated_concept['concept_count']
            else:
                result_dict[id] = associated_concept

        # We'll need to adjust the frequencies in terms of the total patients treated with this drug
        total_associated_condition_counts = 0
        for id in result_dict:
            total_associated_condition_counts += result_dict[id]['concept_count']

        for id in result_dict:
            result_dict[id]['concept_frequency'] = result_dict[id]['concept_count'] / float(
                total_associated_condition_counts)

        return result_dict

    @staticmethod
    def get_obs_exp_ratio(drug_description, disease_description, conservative=False):
        """
        Get the natural logarithm of Observed count / Expected count on the drug and the disease
        :param drug_description: string (eg. 'Naproxen')
        :param disease_description: string (eg. 'Neonatal disorder')
        :param conservative: bool (True= use exact matching for mapping drug to COHD, False = use all synonyms returned by COHD)
        :return: the natural logarithm of the ratio between the observed count and expected count on the drug and the disease
        """
        # Get the concept ID of the drug
        drug_concepts = QueryCOHD.find_concept_ids(drug_description, dataset_id=3)
        drug_ids = []
        if conservative:
            for concept in drug_concepts:
                if concept['concept_name'].lower() == drug_description.lower():
                    drug_ids.append(concept['concept_id'])
        if not conservative:
            for concept in drug_concepts:
                drug_ids.append(concept['concept_id'])

        # Get the concept ID of the disease
        disease_concepts = QueryCOHD.find_concept_ids(disease_description, dataset_id=3)
        disease_ids = []
        for concept in disease_concepts:
            if conservative:
                if concept['concept_name'].lower() == disease_description.lower():
                    disease_ids.append(concept['concept_id'])
            else:
                disease_ids.append(concept['concept_id'])

        # print("number of the drug ids: %d" % len(drug_ids))
        # print("number of the disease ids: %d" % len(disease_ids))

        # sum the observed count and expected count
        observed_count = 0
        expected_count = 0
        for drug_id in drug_ids:
            for disease_id in disease_ids:
                results = QueryCOHD.get_obs_exp_ratio(str(drug_id), str(disease_id), dataset_id=3)
                for result in results:
                    if 'expected_count' in result.keys():
                        expected_count += result['expected_count']
                    if 'observed_count' in result.keys():
                        observed_count += result['observed_count']

        if expected_count == 0:
            return float('-inf')
        # print("observed_count = %f, expected_count = %f" % (observed_count, expected_count))
        return math.exp(observed_count / expected_count)


if __name__ == "__main__":
    q = COHDUtilities()
    print(q.get_conditions_treating('Naproxen', conservative=True))
    print("\n")
    print(q.get_conditions_treating('Naproxen', conservative=False))
    print("\n")
    print(q.get_obs_exp_ratio("Naproxen", "Neonatal disorder", conservative=False))
    print("\n")
    print(q.get_obs_exp_ratio("Naproxen", "Developmental speech disorder", conservative=False))
    print("\n")
    print(q.get_obs_exp_ratio("Naproxen", "Gestation abnormality", conservative=False))