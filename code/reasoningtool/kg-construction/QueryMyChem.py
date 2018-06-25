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

import requests
import requests_cache
import sys
import json

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')


class QueryMyChem:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://mychem.info/v1'
    HANDLER_MAP = {
        'get_chemical_substance':   'chem/{id}',
        'get_drug':                 'chem/{id}'
    }

    @staticmethod
    def __access_api(handler):

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
                if "definition" in json_dict['chebi']:
                    result_str = json_dict['chebi']['definition']
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
        if 'drugcentral' in id_json.keys():
            return id_json['drugcentral']['xref']['mesh_descriptor_ui']
        else:
            return None

    @staticmethod
    def get_cui(chemical_substance_id):
        if chemical_substance_id[:7].upper() == "CHEMBL:":
            chemical_substance_id = "CHEMBL" + chemical_substance_id[7:]
        handler = 'chem/' + chemical_substance_id + '?fields=drugcentral.xref.umlscui'

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
            #print(url, file=sys.stderr)
            #print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        id_json = res.json()
        if 'drugcentral' in id_json.keys():
            return id_json['drugcentral']['xref']['umlscui']
        else:
            return None

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
        if results is not None:
            json_dict = json.loads(results)
            if "sider" in json_dict.keys():
                for se in json_dict['sider']:
                    if 'meddra' in se.keys():
                        if 'umls_id' in se['meddra']:
                            side_effects_set.add("UMLS:" + se['meddra']['umls_id'])
        return side_effects_set

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
                    {'relation': 'indication', 'snomed_id': '315642008', 'snomed_name': 'Influenza-like symptoms'},
                    {'relation': 'indication', 'snomed_id': '76948002', 'snomed_name': 'Severe pain'},
                    ...
                ],
            'contraindications':
                [
                    {'relation': 'contraindication', 'snomed_id': '24526004', 'snomed_name': 'Inflammatory bowel disease'},
                    {'relation': 'contraindication', 'snomed_id': '116290004', 'snomed_name': 'Acute abdominal pain'},
                    {'relation': 'contraindication', 'snomed_id': '13645005', 'snomed_name': 'Chronic obstructive lung disease'},
                    ...
                ]
            }
        """
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
                if "drug_use" in drugcentral.keys():
                    drug_uses = drugcentral['drug_use']
                    if isinstance(drug_uses, list):
                        for drug_use in drug_uses:
                            if 'relation' in drug_use.keys() and 'snomed_id' in drug_use.keys():
                                if drug_use['relation'] == 'indication' and drug_use not in indications:
                                    indications.append(drug_use)
                                if drug_use['relation'] == 'contraindication' and drug_use not in contraindications:
                                    contraindications.append(drug_use)
                    elif isinstance(drug_uses, dict):
                        if 'relation' in drug_uses.keys() and 'snomed_id' in drug_uses.keys():
                            if drug_uses['relation'] == 'indication' and drug_uses not in indications:
                                indications.append(drug_uses)
                            if drug_uses['relation'] == 'contraindication' and drug_uses not in contraindications:
                                contraindications.append(drug_uses)
        return {'indications': indications, "contraindications": contraindications}


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

    # umls_array = QueryMyChem.get_drug_side_effects("KWHRDNMACVLHCE-UHFFFAOYSA-N")
    # print(umls_array)
    # print(len(umls_array))
    #
    # umls_array = QueryMyChem.get_drug_side_effects("CHEMBL:521")
    # print(umls_array)
    # print(len(umls_array))

    # drug_use = QueryMyChem.get_drug_use("CHEMBL1082")
    # print(drug_use['indications'])
    # print(drug_use['contraindications'])