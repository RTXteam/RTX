''' This module defines the class QueryMyChem. QueryMyChem class is designed
to communicate with MyChem APIs and their corresponding data sources. The available methods include:

    get_chemical_substance_entity : query chemical substance properties by ID

'''

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey', 'Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

# import requests
# import requests_cache
from cache_control_helper import CacheControlHelper

import sys
import json

class QueryMyChem:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://mychem.info/v1'
    HANDLER_MAP = {
        'get_chemical_substance': 'chem/{id}',
        'get_drug': 'chem/{id}',
        'get_pubchem_info': 'query?q=pubchem.cid:{cid}'
    }

    @staticmethod
    def __access_api(handler):

        requests = CacheControlHelper()
        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryMyChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryMyChem.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryMyChem.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def __get_description(entity_type, entity_id):
        handler = QueryMyChem.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryMyChem.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            if "chebi" in json_dict.keys():
                if type(json_dict['chebi']) is dict and "definition" in json_dict['chebi'].keys():
                    result_str = json_dict['chebi']['definition']
                if type(json_dict['chebi']) is list and "definition" in json_dict['chebi'][0].keys():
                    result_str = json_dict['chebi'][0]['definition']
        return result_str

    @staticmethod
    def get_chemical_substance_entity(chemical_substance_id):
        if chemical_substance_id[:7].upper() == "CHEMBL:":
            chemical_substance_id = "CHEMBL" + chemical_substance_id[7:]
        return QueryMyChem.__get_entity("get_chemical_substance", chemical_substance_id)

    @staticmethod
    def get_chemical_substance_description(chemical_substance_id):
        if chemical_substance_id[:7].upper() == "CHEMBL:":
            chemical_substance_id = "CHEMBL" + chemical_substance_id[7:]
        return QueryMyChem.__get_description("get_chemical_substance", chemical_substance_id)

    @staticmethod
    def get_mesh_id(chemical_substance_id):
        if chemical_substance_id[:7].upper() == "CHEMBL:":
            chemical_substance_id = "CHEMBL" + chemical_substance_id[7:]
        handler = 'chem/' + chemical_substance_id + '?fields=drugcentral.xref.mesh_descriptor_ui'

        requests = CacheControlHelper()
        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryMyChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        id_json = res.json()
        res = None
        if 'drugcentral' in id_json.keys():
            if 'xref' in id_json['drugcentral'].keys():
                if 'mesh_descriptor_ui' in id_json['drugcentral']['xref'].keys():
                    res = id_json['drugcentral']['xref']['mesh_descriptor_ui']
        return res

    @staticmethod
    def get_cui(chemical_substance_id):
        if chemical_substance_id[:7].upper() == "CHEMBL:":
            chemical_substance_id = "CHEMBL" + chemical_substance_id[7:]
        handler = 'chem/' + chemical_substance_id + '?fields=drugcentral.xref.umlscui'

        requests = CacheControlHelper()
        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryMyChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            # print(url, file=sys.stderr)
            # print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        id_json = res.json()
        res = None
        if 'drugcentral' in id_json.keys():
            if 'xref' in id_json['drugcentral'].keys():
                if 'umlscui' in id_json['drugcentral']['xref'].keys():
                    res = id_json['drugcentral']['xref']['umlscui']
        return res

    @staticmethod
    def get_drug_side_effects(chembl_id):
        """
        Retrieving the side effects of a drug from MyChem

        :param chembl_id: The CHEMBL ID for a drug
        :return: A set of strings containing the founded umls ids, or empty set if none were found
        """
        side_effects_set = set()
        if not isinstance(chembl_id, str):
            return side_effects_set
        if chembl_id[:7].upper() == "CHEMBL:":
            chembl_id = "CHEMBL" + chembl_id[7:]
        handler = QueryMyChem.HANDLER_MAP['get_drug'].format(id=chembl_id) + "?fields=sider"
        results = QueryMyChem.__access_api(handler)
        # with requests_cache.disabled():
        #     results = QueryMyChem.__access_api(handler)
        #     with open('uncached_urls.log', 'a+') as f:
        #         print(QueryMyChem.API_BASE_URL + '/' + handler, file=f)
        if results is not None:
            json_dict = json.loads(results)
            if "sider" in json_dict.keys():
                for se in json_dict['sider']:
                    if 'meddra' in se.keys():
                        if 'umls_id' in se['meddra'].keys():
                            side_effects_set.add("UMLS:" + se['meddra']['umls_id'])
        return side_effects_set

    @staticmethod
    def get_meddra_codes_for_side_effects(chembl_id):
        """
        Retrieving the MedDRA codes for a drug; Curated by DrugCentral. Queries MyChem.info to retrieve the codes.
        MedDRA codes are then used to get drug side effects. Use as an alternative to get_drug_side_effects(chembl_id).
        :param chembl_id: The CHEMBL ID for a drug
        :return: A set of strings containing MedDRA codes, or empty set if none were found
        """
        meddra_code_set = set()
        if not isinstance(chembl_id, str):
            return meddra_code_set
        if chembl_id[:7].upper() == "CHEMBL:":
            chembl_id = "CHEMBL" + chembl_id[7:]
        pubchem_id = QueryMyChem.get_pubchem_cid(chembl_id)
        if pubchem_id is None:
            return meddra_code_set
        handler = QueryMyChem.HANDLER_MAP['get_pubchem_info'].format(cid=pubchem_id)
        results = QueryMyChem.__access_api(handler)
        # with requests_cache.disabled():
        #     results = QueryMyChem.__access_api(handler)
        #     with open('uncached_urls.log', 'a+') as f:
        #         print(QueryMyChem.API_BASE_URL + '/' + handler, file=f)
        if results is not None and pubchem_id is not None:
            json_dict = json.loads(results)
            if 'hits' in json_dict.keys() and len(json_dict['hits']) > 0:
                hits = json_dict['hits'][0]
                if 'drugcentral' in hits.keys():
                    drugcentral = hits['drugcentral']
                    if isinstance(drugcentral, dict) and 'fda_adverse_event' in drugcentral.keys():
                        for drug in drugcentral['fda_adverse_event']:
                            if isinstance(drug, dict) and 'meddra_code' in drug.keys():
                                meddra_code_set.add("MEDDRA:" + str(drug['meddra_code']))
        return meddra_code_set

    @staticmethod
    def get_pubchem_cid(chembl_id):
        """
        Retrive pubchem cid given a CHEMBL ID from MyChem.info
        :param chembl_id: The CHEMBL ID for a drug
        :return: pubchem cid for the drug/compound
        """
        pubchem_cid = None
        if not isinstance(chembl_id, str):
            return None
        if chembl_id[:7].upper() == "CHEMBL:":
            chembl_id = "CHEMBL" + chembl_id[7:]
        handler = QueryMyChem.HANDLER_MAP['get_drug'].format(id=chembl_id) + "?fields=chebi"
        results = QueryMyChem.__access_api(handler)
        # with requests_cache.disabled():
        #     results = QueryMyChem.__access_api(handler)
        #     with open('uncached_urls.log', 'a+') as f:
        #         print(QueryMyChem.API_BASE_URL + '/' + handler, file=f)
        if results is not None:
            json_dict = json.loads(results)
            if 'chebi' in json_dict.keys():
                if isinstance(json_dict['chebi'], dict) and 'xref' in json_dict['chebi'].keys():
                    if isinstance(json_dict["chebi"]["xref"], dict) and 'pubchem' in json_dict["chebi"]["xref"].keys():
                        if isinstance(json_dict["chebi"]["xref"]["pubchem"], dict) and 'cid' in json_dict["chebi"]["xref"]["pubchem"].keys():
                            pubchem_cid = json_dict["chebi"]["xref"]["pubchem"]["cid"]
        return pubchem_cid

    @staticmethod
    def get_drug_use(chembl_id):
        """
        Retrieving the indication and contraindication of a drug from MyChem

        :param chembl_id: The CHEMBL ID for a drug
        :return: A dictionary with two fields ('indication' and 'contraindication'). Each field is an array containing
            'snomed_id' and 'snomed_name'.

            Example:
            {'indications':
                [
                    {'concept_name': 'Nosocomial Pneumonia due to Klebsiella Pneumoniae'},
                    {'concept_name': 'Acute bacterial sinusitis',
                     'cui_semantic_type': 'T047',
                     'snomed_concept_id': 75498004,
                     'snomed_full_name': 'Acute bacterial sinusitis',
                     'umls_cui': 'C0275556'},
                    {'concept_name': 'Acute Moraxella catarrhalis bronchitis',
                     'cui_semantic_type': 'T047',
                     'snomed_concept_id': 195722003,
                     'snomed_full_name': 'Acute Moraxella catarrhalis bronchitis',
                     'umls_cui': 'C0339932'},
                    ...
                ],
            'contraindications':
                [
                    {'concept_name': 'Diabetes mellitus',
                     'cui_semantic_type': 'T047',
                     'snomed_concept_id': 73211009,
                     'snomed_full_name': 'Diabetes mellitus',
                     'umls_cui': 'C0011849'},
                    {'concept_name': 'Pancytopenia',
                     'cui_semantic_type': 'T047',
                     'snomed_concept_id': 127034005,
                     'snomed_full_name': 'Pancytopenia',
                     'umls_cui': 'C0030312'},
                    ...
                ]
            }
        """
        print(chembl_id, file=sys.stderr)
        indications = []
        contraindications = []
        if not isinstance(chembl_id, str):
            return {'indications': indications, "contraindications": contraindications}
        if chembl_id[:7].upper() == "CHEMBL:":
            chembl_id = "CHEMBL" + chembl_id[7:]

        handler = QueryMyChem.HANDLER_MAP['get_drug'].format(id=chembl_id)
        results = QueryMyChem.__access_api(handler)
        if results is not None:
            json_dict = json.loads(results)
            if "drugcentral" in json_dict.keys():
                drugcentral = json_dict['drugcentral']
                if isinstance(drugcentral, list):
                    drugcentral = drugcentral[0]
                if isinstance(drugcentral, dict) and "drug_use" in drugcentral.keys():
                    drug_uses = drugcentral['drug_use']
                    if QueryMyChem.__has_dirty_cache(drug_uses):
                        indications, contraindications = QueryMyChem.__handle_dirty_cache(drug_uses)
                    else:
                        indications, contraindications = QueryMyChem.__handle_clean_cache(drug_uses)
        return {'indications': indications, "contraindications": contraindications}

    @staticmethod
    def __has_dirty_cache(drug_uses):
        if isinstance(drug_uses, list):
            d_u = drug_uses[0]
            if isinstance(d_u, dict) and 'snomed_id' in d_u.keys():
                return True
        if isinstance(drug_uses, dict) and 'snomed_id' in drug_uses.keys():
            return True
        return False

    @staticmethod
    def __handle_clean_cache(drug_uses):
        indications = []
        contraindications = []
        if isinstance(drug_uses, list):
            drug_uses = drug_uses[0]
        if isinstance(drug_uses, dict) and 'contraindication' in drug_uses.keys():
            if isinstance(drug_uses['contraindication'], list):
                contraindications = drug_uses['contraindication']
            elif isinstance(drug_uses['contraindication'], dict):
                contraindications.append(drug_uses['contraindication'])
        if isinstance(drug_uses, dict) and 'indication' in drug_uses.keys():
            if isinstance(drug_uses['indication'], list):
                indications = drug_uses['indication']
            elif isinstance(drug_uses['indication'], dict):
                indications.append(drug_uses['indication'])
        return indications, contraindications

    @staticmethod
    def __handle_dirty_cache(drug_uses):
        indications = []
        contraindications = []
        if isinstance(drug_uses, list):
            for drug_use in drug_uses:
                if isinstance(drug_use, dict) and 'relation' in drug_use.keys() and 'snomed_id' in drug_use.keys():
                    drug_use['snomed_concept_id'] = drug_use['snomed_id']
                    if drug_use['relation'] == 'indication':
                        indications.append(drug_use)
                    elif drug_use['relation'] == 'contraindication':
                        contraindications.append(drug_use)
        if isinstance(drug_uses, dict):
            if 'relation' in drug_uses.keys():
                drug_uses['snomed_concept_id'] = drug_uses['snomed_id']
                if drug_uses['relation'] == 'indication':
                    indications.append(drug_uses)
                elif drug_uses['relation'] == 'contraindication':
                    contraindications.append(drug_uses)
        return indications, contraindications


if __name__ == '__main__':

    def save_to_test_file(filename, key, value):
        f = open(filename, 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('tests/query_test_data.json', 'ChEMBL:1200766',
                      QueryMyChem.get_chemical_substance_entity('ChEMBL:1200766'))
    save_to_test_file('tests/query_desc_test_data.json', 'ChEMBL:154',
                      QueryMyChem.get_chemical_substance_description('ChEMBL:154'))
    save_to_test_file('tests/query_desc_test_data.json', 'ChEMBL:20883',
                      QueryMyChem.get_chemical_substance_description('ChEMBL:20883'))   # no definition field
    save_to_test_file('tests/query_desc_test_data.json', 'ChEMBL:110101020',
                      QueryMyChem.get_chemical_substance_description('ChEMBL:110101020'))   # wrong id

    print(QueryMyChem.get_chemical_substance_description('CHEMBL:58832'))

    # umls_array = QueryMyChem.get_drug_side_effects("CHEMBL521")
    # print(umls_array)
    # print(len(umls_array))
    # #

    # print(QueryMyChem.get_fda_adverse_events('CHEMBL:699'))
    umls_array = QueryMyChem.get_drug_side_effects("CHEMBL:699")
    print(umls_array)
    print(len(umls_array))
    print(len(QueryMyChem.get_drug_side_effects("CHEMBL:1908841")))
    print(len(QueryMyChem.get_drug_side_effects("CHEMBL:655")))
    drug_use = QueryMyChem.get_drug_use("CHEMBL20883")
    print(str(len(drug_use['indications'])) + str(drug_use['indications']))
    print(str(len(drug_use['contraindications'])) + str(drug_use['contraindications']))
    print(QueryMyChem.get_pubchem_cid("CHEMBL452231"))
    print(QueryMyChem.get_meddra_codes_for_side_effects("CHEMBL1755"))
