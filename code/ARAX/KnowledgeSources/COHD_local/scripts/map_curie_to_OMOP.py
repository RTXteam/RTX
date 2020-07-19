
#import python modules
import pandas as pd
import os
import sys
import pickle
import argparse
import multiprocessing
import itertools
from contextlib import redirect_stderr
import re
import requests

#import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

class MapCurieToOMOP:

    #### Constructor
    def __init__(self, kg="KG1"):
        """
        :param kg (str): the name of knowledge provider (optional) e.g. "KG1" or "KG2"
        """
        kg = kg.upper()
        self.kg = kg
        self.get_synonyms_done = False
        self.synonymizer = NodeSynonymizer()

        ## set up the path of KGmetadata
        pre_path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'data', 'KGmetadata'])

        if kg=="KG1":
            fpath = pre_path + "/NodeNamesDescriptions_KG1.tsv"
        elif kg=="KG2":
            fpath = pre_path + "/NodeNamesDescriptions_KG2.tsv"
        else:
            raise ValueError("The parameter 'kg' only accepts 'KG1' or 'KG2'")

        ## read KGmetadata
        try:
            self.kpdata = pd.read_csv(fpath, sep="\t", header=None, names=['curie', 'name', 'type'])
        except FileNotFoundError:
            raise FileNotFoundError("Please go to $RTX/data/KGmetadata and run 'python3 KGNodeIndex.py -b' first")

        self.kpdata_dict = dict()
        for row_index in range(self.kpdata.shape[0]):
            if self.kpdata.loc[row_index,'curie'] not in self.kpdata_dict:
                self.kpdata_dict[self.kpdata.loc[row_index, 'curie']] = {'name': {self.kpdata.loc[row_index, 'name']}, 'type': {self.kpdata.loc[row_index, 'type']}}
            else:
                self.kpdata_dict[self.kpdata.loc[row_index, 'curie']]['name'].update([self.kpdata.loc[row_index, 'name']])
                self.kpdata_dict[self.kpdata.loc[row_index, 'curie']]['type'].update([self.kpdata.loc[row_index, 'type']])




    def get_synonyms(self, curie_type):
        """Retrieve the synonyms of nodes with certain type

        :param curie_type (str or list): the type of curie nodes in specified knowledge provider (Required) e.g., "disease", "phenotypic_feature", ['disease', 'phenotypic_feature']
        return: a dict containing synonym list, name and type for each node
        """

        ## check the input parameters
        if isinstance(curie_type, str):
            pass
        elif isinstance(curie_type, list):
            pass
        else:
            raise ValueError("The parameter 'curie_type' should be str or list")

        ## use NodeSynonymizer to find the node synonyms and their biomedical vocabularies
        if isinstance(curie_type, str):

            if curie_type not in set(self.kpdata['type']):
                raise ValueError(f"The curie type '{curie_type}' is not a category in {self.kg}. Please check your spelling.")
            else:
                self.synonyms_dict = dict()
                for curie in self.kpdata_dict:
                    if curie_type in self.kpdata_dict[curie]['type']:
                        res = self.synonymizer.get_normalizer_results(curie, kg_name=self.kg)
                        synonym_list = list(set([row['identifier'] for row in res[curie]['equivalent_identifiers']]))
                        self.synonyms_dict[curie] = {'name': self.kpdata_dict[curie]['name'], 'type': self.kpdata_dict[curie]['type'], 'synonyms': synonym_list}

        else:

            for index in range(len(curie_type)):
                type = curie_type[index]
                if type not in set(self.kpdata['type']):
                    raise ValueError(f"The curie type '{type}' is not a category in {self.kg}. Please check your spelling.")
                else:
                    pass

            self.synonyms_dict  = dict()
            for curie in self.kpdata_dict:
                if len(self.kpdata_dict[curie]['type'].intersection(set(curie_type)))>0:
                    res = self.synonymizer.get_normalizer_results(curie, kg_name=self.kg)
                    synonym_list = list(set([row['identifier'] for row in res[curie]['equivalent_identifiers']]))
                    self.synonyms_dict[curie] = {'name': self.kpdata_dict[curie]['name'], 'type': self.kpdata_dict[curie]['type'], 'synonyms': synonym_list}

        self.get_synonyms_done = True

    def _parallel_get_OMOP(self, synonym):

        try:
            vocabulary_id, concept_code = synonym.split(':')
        except ValueError:
            vocabulary_id, concept_code = synonym.split(':')[1:]
        if vocabulary_id not in ['ATC', 'CVX', 'HCPCS', 'ICD10', 'ICD-10', 'ICD10CM', 'ICD-9', 'MESH', 'NDFRT', 'RXNORM', 'SNOMEDCT', 'SNOMEDCT_VET', 'MEDDRA']:
            return []
        else:
            if vocabulary_id == "ICD-10":
                synonym = synonym.replace('ICD-10', 'ICD10')
            elif vocabulary_id == "ICD-9":
                synonym = synonym.replace('ICD-9', 'ICD9CM')
            elif vocabulary_id == "MESH":
                synonym = synonym.replace('MESH', 'MeSH')
            elif vocabulary_id == "RXNORM":
                synonym = synonym.replace('RXNORM', 'RxNorm')
            elif vocabulary_id == "SNOMEDCT":
                synonym = synonym.replace('SNOMEDCT', 'SNOMED')
            elif vocabulary_id == "SNOMEDCT_VET":
                synonym = synonym.replace('SNOMEDCT_VET', 'SNOMED')
            elif vocabulary_id == "MEDDRA":
                synonym = synonym.replace('MEDDRA', 'MedDRA')
            else:
                pass

            concept_id = self.concepts_table_select.loc[self.concepts_table_select['curie_name'] == synonym, 'concept_id']
            return list(concept_id)



    def map_curie_to_OMOP(self, pre_run_dict=None):
        """Map curies to OMOP ids based on the synonyms returned from NodeSynonymizer

        :param pre_run_dict(optional, str or dict): the path of result saved as pickle file returned from 'get_synonyms' method or the dict object returned from 'get_synonyms' method e.g. 'synonyms_kg1.pkl' or kg2_synonyms
        return: a dict containing OMOP id list,synonym list, name and type for each node
        """

        if pre_run_dict==None:
            if not self.get_synonyms_done:
                print(f"Please run 'get_synonyms' method first before run this method.")
                return {}
        else:
            if isinstance(pre_run_dict, str):
                if os.path.exists(pre_run_dict):
                    with open(pre_run_dict, 'rb') as file:
                        self.synonyms_dict = pickle.load(file)
                else:
                    print(f"Can't find {pre_run_dict}")
                    return {}
            elif isinstance(pre_run_dict, dict):
                self.synonyms_dict = pre_run_dict
            else:
                print(f"The parameter 'pre_run_dict' is not a str or a dict.")
                return {}

        infolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        try:
            # if self.kg == "KG1":
            #     infile_path = infolder + '/Athena_tables/CONCEPT_KG1.txt'
            #     concepts_table = pd.read_csv(infile_path, sep='\t', index_col=None)
            # else:
            #     infile_path = infolder + '/Athena_tables/CONCEPT_KG2.txt'
            #     concepts_table = pd.read_csv(infile_path, sep='\t', index_col=None)
            infile_path = infolder + '/Athena_tables/ALL_CONCEPT_filtered.txt'
            concepts_table = pd.read_csv(infile_path, sep='\t', index_col=None)
        except FileNotFoundError:
            print(f"Can't find {infile_path}")
            return {}

        # if self.kg == "KG1":
        #     select = ['ATC', 'MeSH', 'ICD10', 'ICD10CM', 'ICD9CM', 'RxNorm', 'SNOMED', 'MedDRA']
        # else:
        select = ['ATC', 'CVX', 'HCPCS', 'ICD10', 'ICD10CM', 'ICD9CM', 'MeSH', 'NDFRT', 'RxNorm', 'SNOMED', 'MedDRA']

        concepts_table_select = concepts_table.loc[[concepts_table.loc[index, 'vocabulary_id'] in select for index in range(concepts_table.shape[0])], ['concept_id', 'vocabulary_id', 'concept_code']]
        concepts_table_select['curie_name'] = concepts_table_select[['vocabulary_id', 'concept_code']].apply(lambda x: str(x[0]) + ":" + str(x[1]), axis=1)
        concepts_table_select.drop(columns=['vocabulary_id', 'concept_code'])
        self.concepts_table_select = concepts_table_select.drop(columns=['vocabulary_id', 'concept_code'])

        for key in self.synonyms_dict:
            print(key)
            synonym_list = self.synonyms_dict[key]['synonyms']
            OMOP_concept_list = [elem for elem in itertools.chain.from_iterable([OMOP_list for OMOP_list in map(self._parallel_get_OMOP, synonym_list)])]
            self.synonyms_dict[key]["concept_ids"] = list(set(OMOP_concept_list))


def main():
    print(f"Processing KG1",flush=True)
    kg1_CtoM = MapCurieToOMOP(kg="KG1")
    kg1_CtoM.get_synonyms(curie_type=["disease", "phenotypic_feature", "chemical_substance"])
    res = kg1_CtoM.synonyms_dict
    print(f"Total curies: {len(res)}")
    outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
    with open(outfolder + "/synonyms_kg1.pkl", 'wb') as file:
        pickle.dump(res, file)
    kg1_CtoM.map_curie_to_OMOP()
    res = kg1_CtoM.synonyms_dict
    outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
    with open(outfolder + '/synonyms_kg1_with_concepts.pkl', 'wb') as file:
        pickle.dump(res, file)
    # with open("synonyms_kg1.pkl", 'wb') as file:
    #     pickle.dump(res, file)
    # vocabulary_id = set([identifier.split(":")[0] for identifier in set(itertools.chain.from_iterable([res[curie]['synonyms'] for curie in res]))])
    # print(f"The biomedical vocabulary ids are: {list(vocabulary_id)}")

    print(f"Processing KG2",flush=True)
    kg2_CtoM = MapCurieToOMOP(kg="KG2")
    kg2_CtoM.get_synonyms(curie_type=["disease", "phenotypic_feature", "chemical_substance", "drug"])
    res = kg2_CtoM.synonyms_dict
    print(f"Total curies: {len(res)}")
    outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
    with open(outfolder + "/synonyms_kg2.pkl", 'wb') as file:
        pickle.dump(res, file)
    kg2_CtoM.map_curie_to_OMOP()
    # infolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
    # with open(infolder + "/synonyms_kg2.pkl", 'rb') as file:
    #     data_dict = pickle.load(file)
    # kg2_CtoM.map_curie_to_OMOP(pre_run_dict=data_dict)
    res = kg2_CtoM.synonyms_dict
    outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
    with open(outfolder + '/synonyms_kg2_with_concepts.pkl', 'wb') as file:
        pickle.dump(res, file)



####################################################################################################

if __name__ == "__main__":
    main()

