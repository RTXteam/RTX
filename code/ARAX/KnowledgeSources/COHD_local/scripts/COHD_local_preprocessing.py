# This script will auto-download the data from the given data source and have different functions to process the data

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
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'reasoningtool', 'kg-construction']))
from QueryCOHD import QueryCOHD


def download_COHD_database(url, out_loc, out_format):
    pass #TODO

class MapCurieToOMOP:

    #### Constructor
    def __init__(self, kg="KG1"):
        """
        :param kg (str): the name of knowledge provider (optional) e.g. "KG1" or "KG2"
        """

        self.kg = kg

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


    def _get_OMOP_id(self, index_curie_datasetid_domain):
        """Call the 'get_xref_to_OMOP' or 'find_concept_ids' method from QueryCOHD to map CURIES to OMOP concept ids.

        :param index_curie_and_datasetid(tuple): a tuple contain index, curie id and the best dataset id and domain used in 'QueryCOHD.find_concept_ids' (required) e.g. (1, "DOID:8398", 3, "Drug")
        return: a list of OMOP concept ids
        """
        index, curie, bestid, domain = index_curie_datasetid_domain

        ## choose the best dataset id and the second best dataset id
        dataset_list = [0,1,2,3]
        first_id = dataset_list.pop(bestid)
        second_id = dataset_list.pop()

        print(f"{index} {curie}", flush=True)

        if curie.split(':')[0] not in ['EFO', 'DOID', 'OMIM', 'MESH', 'UBERON', 'HP']:
            if len(self.kpdata_dict[curie]['name']) == 0:
                OMOP_list = []
            elif len(self.kpdata_dict[curie]['name']) == 1 and list(self.kpdata_dict[curie]['name'])[0]!="":
                OMOP_list = list(set([str(x['concept_id']) for x in QueryCOHD.find_concept_ids(list(self.kpdata_dict[curie]['name'])[0], domain=domain, dataset_id=first_id)]))
                if len(OMOP_list)!=0:
                    pass
                else:
                    OMOP_list = list(set([str(x['concept_id']) for x in QueryCOHD.find_concept_ids(list(self.kpdata_dict[curie]['name'])[0], domain=domain, dataset_id=second_id)]))
                    if len(OMOP_list) != 0:
                        pass
                    else:
                        OMOP_list = []
            else:
                OMOP_list = list(set(itertools.chain.from_iterable([[str(x['concept_id']) for name in self.kpdata_dict[curie]['name'] if name!="" for x in QueryCOHD.find_concept_ids(name, domain=domain, dataset_id=first_id)]])))
                if len(OMOP_list) != 0:
                    pass
                else:
                    OMOP_list = list(set(itertools.chain.from_iterable([[str(x['concept_id']) for name in self.kpdata_dict[curie]['name'] if name != "" for x in QueryCOHD.find_concept_ids(name, domain=domain, dataset_id=second_id)]])))
                    if len(OMOP_list) != 0:
                        pass
                    else:
                        OMOP_list = []
        else:
            OMOP_list = list(set([str(x['omop_standard_concept_id']) for x in QueryCOHD.get_xref_to_OMOP(curie, 1)]))
            if len(OMOP_list)!=0:
                pass
            else:
                OMOP_list = list(set([str(x['omop_standard_concept_id']) for x in QueryCOHD.get_xref_to_OMOP(curie, 2)]))
                if len(OMOP_list) != 0:
                    pass
                else:
                    OMOP_list = list(set([str(x['omop_standard_concept_id']) for x in QueryCOHD.get_xref_to_OMOP(curie, 3)]))
                    if len(OMOP_list) != 0:
                        pass
                    else:
                        OMOP_list = []

        return OMOP_list

    def map_curies_with_specified_type_to_OMOP(self, curie_type, domain, best_dataset_id=3):
        """Map the curies with specified type to OMOP standard concepts

        :param curie_type (str or list): the category of curie nodes in specified knowledge provider (Required) e.g., "disease", "phenotypic_feature", ['disease', 'phenotypic_feature']
        :param domain (str or list): the domain (e.g., "Condition", "Drug", "Procedure") option in findConceptIDs API in the Columbia Open Health Data (COHD) (Required, if it is list, each element in list should correspond to 'curie_type') e.g. "Drug", ["Drug","Condition"]
        :param best_dataset_id (int): the dataset id used in findConceptIDs API in the Columbia Open Health Data (COHD) (Optional, two options: 2 or 3)
        return: a dict containing curie id, curie name, curie type and OMOP concept ids.
        """

        ## check the input parameters
        if isinstance(curie_type, str):
            pass
        elif isinstance(curie_type, list):
            pass
        else:
            raise ValueError("The parameter 'curie_type' should be str or list")

        domain_allowable = ['Condition', 'Device', 'Drug', 'Ethnicity', 'Gender', 'Measurement', 'Observation', 'Procedure', 'Race', 'Relationship']
        if isinstance(domain, str):
            if domain in domain_allowable:
                pass
            else:
                raise ValueError(f"The curie type '{domain}' is not in the allowable list {domain_allowable}.")
        elif isinstance(domain, list):
            nonaccpted_type = []
            has_error = False
            for elem in domain:
                if elem in domain_allowable:
                    pass
                else:
                    has_error = True
                    nonaccpted_type.extend(elem)
            if has_error:
                raise ValueError(f"The curie type '{nonaccpted_type}' is not in the allowable list {domain_allowable}.")
        else:
            raise ValueError("The parameter 'domain' should be str or list")

        if best_dataset_id==2 or best_dataset_id==3:
            pass
        else:
            raise ValueError("The parameter 'best_dataset_id' should be 2 or 3")

        ## Check if the parameter 'curie_type' has the same type as the parameter 'domain'
        if isinstance(curie_type, str):
            if isinstance(domain, str):
                pass
            else:
                raise ValueError("The parameter 'domain' should be str as the parameter 'curie_type' is str")
        else:
            if isinstance(domain, list):
                if len(curie_type) == len(domain):
                    pass
                else:
                    raise ValueError("If the parameters 'curie_type' and 'domain' are list, they should have same length and correspond to each other.")
            else:
                raise ValueError("The parameter 'domain' should be list as the parameter 'curie_type' is list")

        ## use oxo to map curies to OMOP concept ids
        if isinstance(curie_type, str):

            if curie_type not in set(self.kpdata['type']):
                raise ValueError(f"The curie type '{curie_type}' is not a category in {self.kg}. Please check your spelling.")
            else:
                sub_kpdata = self.kpdata.loc[self.kpdata['type']==curie_type,:].reset_index().drop(columns=['index'])
                curie_list = list(set(sub_kpdata['curie']))
                curie_list = list(zip(range(len(curie_list)), curie_list, itertools.cycle([best_dataset_id]), itertools.cycle([domain])))
                with multiprocessing.Pool(processes=30) as executor:
                    curie_OMOP_list = [OMOP_list for OMOP_list in executor.map(self._get_OMOP_id, curie_list)]
                curie_OMOP_dict = dict()
                for index, curie, _, _ in curie_list:
                    curie_OMOP_dict[curie] = {'name': self.kpdata_dict[curie]['name'],
                                              'type': self.kpdata_dict[curie]['type'],
                                              'OMOP_list': curie_OMOP_list[index]}
        else:

            curie_to_domain = dict()
            for index in range(len(curie_type)):
                type = curie_type[index]
                if type not in set(self.kpdata['type']):
                    raise ValueError(f"The curie type '{type}' is not a category in {self.kg}. Please check your spelling.")
                else:
                    curie_to_domain[type] = domain[index]
                    pass

            print("here1", flush=True)
            sub_kpdata = self.kpdata.loc[[self.kpdata.loc[x,'type'] in curie_type for x in range(self.kpdata.shape[0])],:].reset_index().drop(columns=['index'])
            print("here2", flush=True)
            curie_list = list(set(sub_kpdata['curie']))
            sub_kpdata = sub_kpdata.set_index('curie')
            type_list = list(sub_kpdata.loc[curie_list, 'type'])
            print("here3", flush=True)
            domain_list = [curie_to_domain[elem] for elem in type_list]
            curie_list = list(zip(range(len(curie_list)), curie_list, itertools.cycle([best_dataset_id]), domain_list))
            print("here4", flush=True)
            with multiprocessing.Pool(processes=30) as executor:
                curie_OMOP_list = [OMOP_list for OMOP_list in executor.map(self._get_OMOP_id, curie_list)]
            curie_OMOP_dict = dict()
            for index, curie, _, _ in curie_list:
                curie_OMOP_dict[curie] = {'name': self.kpdata_dict[curie]['name'],
                                          'type': self.kpdata_dict[curie]['type'],
                                          'OMOP_list': curie_OMOP_list[index]}

        return curie_OMOP_dict


def main():
    parser = argparse.ArgumentParser(description="Test each function", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--test', action="store_true", help="If set, run a test for each function", default=False)
    args = parser.parse_args()

    DEBUG=True

    if not args.test:
        parser.print_help()
        return
    else:
        print("============= Testing mapping of curies to OMOP =============", flush=True)
        if DEBUG:
            print('processing KG2', flush=True)
        kg2_CtoM = MapCurieToOMOP(kg="KG2")
        outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        with open('./error_kg2.log', 'w') as stderr, redirect_stderr(stderr):
            res = kg2_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance", "drug"], domain=['Condition', 'Condition', 'Drug', 'Drug'], best_dataset_id=3)
            with open(outfolder + '/KG2_OMOP_mapping.pkl', 'wb') as file:
                pickle.dump(res, file)
        # if DEBUG:
        #     print('processing KG1', flush=True)
        # kg1_CtoM = MapCurieToOMOP(kg="KG1")
        # outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        # with open('./error_kg1.log', 'w') as stderr, redirect_stderr(stderr):
        #     res = kg1_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance"], domain=['Condition','Condition','Drug'], best_dataset_id=3)
        #     with open(outfolder + '/KG1_OMOP_mapping.pkl', 'wb') as file:
        #         pickle.dump(res, file)

        ## Check if there are any requests failed. If so, re-request.
        # error_file_stat = os.stat(outfolder + '/error.log')
        # if error_file_stat.st_size == 0:
        #     with open(outfolder + '/KG1_OMOP_mapping.pkl', 'wb') as file:
        #         pickle.dump(res, file)
        # else:
        #     with open(outfolder + '/error.log','r') as file:
        #         content_list = file.readlines()
        #         error_link = [content_list[x].replace('Status code 502 for url: ', '').replace('\n', '') for x in range(len(content_list)) if content_list[x].find('Status code 502') != -1]
        #
        #     os.remove(outfolder + '/error.log')
        #     with open('./error.log', 'w') as stderr, redirect_stderr(stderr):
        #         for link in error_link:
        #             if link.find('xrefToOMOP') != -1:
        #                 curie = re.search('curie=(.+?)\&', link).group(1)
        #                 if len(res[curie]['OMOP_list'])==0:
        #                     req_res = requests.get(link)
        #                     if req_res.status_code == 200:
        #                         if len(req_res.json()['results']) == 0:
        #                             res[curie]['OMOP_list'] = list(set(req_res.json()['results']))
        #                         else:
        #                             res[curie]['OMOP_list'] = list(set([str(x['omop_standard_concept_id']) for x in req_res.json()['results']]))
        #                     elif req_res.status_code == 502:
        #                         req_res = requests.get(link)
        #                         if req_res.status_code == 200:
        #                             res[curie]['OMOP_list'] = list(set(req_res.json()['results']))
        #                         else:
        #                             print(f"The curie id {curie} can't be converted to OMOP id", file=sys.stderr)
        #                     else:
        #                         print(f"The curie id {curie} can't be converted to OMOP id", file=sys.stderr)
        #
        #             else:
        #                 curie_name = re.search('q=(.+?)\&', link).group(1)
        #                 curie_list = [key for key in res if key.split('.')[0] == 'CHEMBL' and curie_name in res[key]['name']]
        #                 for curie in curie_list:
        #                     OMOP_list = list(set(itertools.chain.from_iterable([[str(x['concept_id']) for name in res[curie]['name'] if name!="" for x in QueryCOHD.find_concept_ids(name, domain="Drug", dataset_id=3)]])))
        #                     res[curie]['OMOP_list'] = OMOP_list

            # with open(outfolder + '/KG1_OMOP_mapping.pkl', 'wb') as file:
            #     pickle.dump(res, file)
        #
        # if DEBUG:
        #     print('processing KG2', flush=True)
        # kg2_CtoM = MapCurieToOMOP(kg="KG2")
        # outfolder = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        # with open('./error_kg2.log', 'w') as stderr, redirect_stderr(stderr):
        #     res = kg2_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance", "drug"], domain=['Condition','Condition','Drug','Drug'], best_dataset_id=3)
        #     with open(outfolder + '/KG2_OMOP_mapping.pkl', 'wb') as file:
        #         pickle.dump(res, file)
        # kg2_CtoM = MapCurieToOMOP(kg="KG2")
        # res = kg2_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance", "drug"])
        # with open('/home/ubuntu/work/RTX/code/ARAX/KnowledgeSources/COHD_local/data/KG2_OMOP_mapping.pkl', 'wb') as file:
        #     pickle.dump(res, file)


####################################################################################################

if __name__ == "__main__":
    main()
