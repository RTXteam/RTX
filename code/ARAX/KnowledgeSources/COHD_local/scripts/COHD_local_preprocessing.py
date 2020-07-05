# This script will auto-download the data from the given data source and have different functions to process the data

#import python modules
import pandas as pd
import os
import sys
import pickle
import argparse
import multiprocessing
import itertools

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


    def _get_OMOP_id(self, index_and_curie):
        """Call the 'get_xref_to_OMOP' or 'find_concept_ids' method from QueryCOHD to map CURIES to OMOP concept ids.

        :param index_and_curie(tuple): a tuple contain index and curie id (required) e.g. (1, "DOID:8398")
        return: a list of OMOP concept ids
        """
        index, curie = index_and_curie
        print(f"{index} {curie}", flush=True)

        if curie.split('.')[0] == 'CHEMBL':
            if len(self.kpdata_dict[curie]['name']) == 0:
                OMOP_list = []
            elif len(self.kpdata_dict[curie]['name']) == 1 and list(self.kpdata_dict[curie]['name'])[0]!="":
                OMOP_list = list(set([str(x['concept_id']) for x in QueryCOHD.find_concept_ids(list(self.kpdata_dict[curie]['name'])[0], domain="Drug", dataset_id=3)]))
            else:
                OMOP_list = list(set(itertools.chain.from_iterable([[str(x['concept_id']) for x in QueryCOHD.find_concept_ids(name, domain="Drug", dataset_id=3)] for name in self.kpdata_dict[curie]['name'] if name!=""])))

        else:
            OMOP_list = list(set([str(x['omop_standard_concept_id']) for x in QueryCOHD.get_xref_to_OMOP(curie, 1)]))

        return OMOP_list

    def map_curies_with_specified_type_to_OMOP(self, curie_type=None):
        """Map the curies with specified type to OMOP standard concepts

        :param curie_type (str or list): the category of curie nodes in specified knowledge provider (Optional, if not specified, then use all curie nodes) e.g., "disease", "phenotypic_feature", ['disease', 'phenotypic_feature']
        return: a dict containing curie id, curie name, curie type and OMOP concept ids.
        """

        ## check the input parameters
        if isinstance(curie_type, str):
            pass
        elif isinstance(curie_type, list):
            pass
        elif curie_type==None:
            pass
        else:
            raise ValueError("The parameter 'curie_type' should be str or list or None")

        ## use oxo to map curies to OMOP concept ids
        if curie_type==None:

            curie_list = list(set(self.kpdata['curie']))
            curie_list = list(zip(range(len(curie_list)), curie_list))
            with multiprocessing.Pool() as executor:
                curie_OMOP_list = [OMOP_list for OMOP_list in executor.map(self._get_OMOP_id, curie_list)]
            curie_OMOP_dict = dict()
            for index, curie in curie_list:
                curie_OMOP_dict[curie] = {'name': self.kpdata_dict[curie]['name'],
                                          'type': self.kpdata_dict[curie]['type'],
                                          'OMOP_list': curie_OMOP_list[index]}

        else:

            if isinstance(curie_type, str):

                if curie_type not in set(self.kpdata['type']):
                    raise ValueError(f"The curie type '{curie_type}' is not a category in {self.kg}. Please check your spelling.")
                else:
                    sub_kpdata = self.kpdata.loc[self.kpdata['type']==curie_type,:].reset_index().drop(columns=['index'])
                    curie_list = list(set(sub_kpdata['curie']))
                    curie_list = list(zip(range(len(curie_list)), curie_list))
                    with multiprocessing.Pool() as executor:
                        curie_OMOP_list = [OMOP_list for OMOP_list in executor.map(self._get_OMOP_id, curie_list)]
                    curie_OMOP_dict = dict()
                    for index, curie in curie_list:
                        curie_OMOP_dict[curie] = {'name': self.kpdata_dict[curie]['name'],
                                                  'type': self.kpdata_dict[curie]['type'],
                                                  'OMOP_list': curie_OMOP_list[index]}
            else:

                for type in curie_type:
                    if type not in set(self.kpdata['type']):
                        raise ValueError(f"The curie type '{type}' is not a category in {self.kg}. Please check your spelling.")
                    else:
                        pass

                sub_kpdata = self.kpdata.loc[[self.kpdata.loc[x,'type'] in curie_type for x in range(self.kpdata.shape[0])], :].reset_index().drop(columns=['index'])
                curie_list = list(set(sub_kpdata['curie']))
                curie_list = list(zip(range(len(curie_list)), curie_list))
                with multiprocessing.Pool() as executor:
                    curie_OMOP_list = [OMOP_list for OMOP_list in executor.map(self._get_OMOP_id, curie_list)]
                curie_OMOP_dict = dict()
                for index, curie in curie_list:
                    curie_OMOP_dict[curie] = {'name': self.kpdata_dict[curie]['name'],
                                              'type': self.kpdata_dict[curie]['type'],
                                              'OMOP_list': curie_OMOP_list[index]}

        return curie_OMOP_dict


def main():
    parser = argparse.ArgumentParser(description="Test each function", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--test', action="store_true", help="If set, run a test for each function", default=False)
    args = parser.parse_args()

    if not args.test:
        parser.print_help()
        return
    else:
        print("============= Testing mapping of curies to OMOP =============", flush=True)
        kg1_CtoM = MapCurieToOMOP(kg="KG1")
        res = kg1_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance"])
        with open('/home/ubuntu/work/RTX/code/ARAX/KnowledgeSources/COHD_local/data/KG1_OMOP_mapping.pkl', 'wb') as file:
             pickle.dump(res, file)

        # kg2_CtoM = MapCurieToOMOP(kg="KG2")
        # res = kg2_CtoM.map_curies_with_specified_type_to_OMOP(curie_type=["disease", "phenotypic_feature", "chemical_substance", "drug"])
        # with open('/home/ubuntu/work/RTX/code/ARAX/KnowledgeSources/COHD_local/data/KG2_OMOP_mapping.pkl', 'wb') as file:
        #     pickle.dump(res, file)


####################################################################################################

if __name__ == "__main__":
    main()
