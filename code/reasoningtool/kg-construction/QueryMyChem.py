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
        'get_chemical_substance': 'chem/{id}',
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
        result_str = 'UNKNOWN'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def __get_description(entity_type, entity_id):
        handler = QueryMyChem.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryMyChem.__access_api(handler)
        result_str = 'UNKNOWN'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            if "chebi" in json_dict.keys():
                if "definition" in json_dict['chebi']:
                    result_str = json_dict['chebi']['definition']
        return result_str

    @staticmethod
    def get_chemical_substance_entity(chemical_substance_id):
        if chemical_substance_id[:7] == "ChEMBL:":
            chemical_substance_id = chemical_substance_id.replace("ChEMBL:", "CHEMBL")
        return QueryMyChem.__get_entity("get_chemical_substance", chemical_substance_id)

    @staticmethod
    def get_chemical_substance_description(chemical_substance_id):
        if chemical_substance_id[:7] == "ChEMBL:":
            chemical_substance_id = chemical_substance_id.replace("ChEMBL:", "CHEMBL")
        return QueryMyChem.__get_description("get_chemical_substance", chemical_substance_id)
    
    @staticmethod
    def get_mesh_id(chemical_substance_id):
        if chemical_substance_id[:7] == "ChEMBL:":
            chemical_substance_id = chemical_substance_id.replace("ChEMBL:", "CHEMBL")
        handler = 'chem/' + chemical_substance_id + '?fields=drugcentral.xref.mesh_descriptor_ui'

        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
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
        if chemical_substance_id[:7] == "ChEMBL:":
            chemical_substance_id = chemical_substance_id.replace("ChEMBL:", "CHEMBL")
        handler = 'chem/' + chemical_substance_id + '?fields=drugcentral.xref.umlscui'

        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            #print(url, file=sys.stderr)
            #print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
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
