''' This module defines the class QueryReactomeExtended. QueryReactomeExtended class is designed
to communicate with Reactome APIs and their corresponding data sources. The available methods include:
    * query pathway entity by ID
'''


__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import requests_cache
import sys
import json


class QueryReactomeExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://reactome.org/ContentService'
    HANDLER_MAP = {
        'get_pathway': 'data/pathway/{id}/containedEvents',
        'get_pathway_desc': 'data/query/{id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryReactomeExtended.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryReactomeExtended.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryReactome for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryReactome for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryReactomeExtended.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryReactomeExtended.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def __get_desc(entity_type, entity_id):
        handler = QueryReactomeExtended.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryReactomeExtended.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            if 'summation' in json_dict.keys():
                summation = json_dict['summation']
                if len(summation) > 0:
                    if 'text' in summation[0].keys():
                        result_str = summation[0]['text']
        return result_str

    @staticmethod
    #   example of pathway_id: REACT:R-HSA-70326
    def get_pathway_entity(pathway_id):
        if pathway_id[:6] == "REACT:":
            pathway_id = pathway_id[6:]
        return QueryReactomeExtended.__get_entity("get_pathway", pathway_id)

    @staticmethod
    #   example of pathway_id: Reactome:R-HSA-70326
    def get_pathway_desc(pathway_id):
        if pathway_id[:6] == "REACT:":
            pathway_id = pathway_id[6:]
        return QueryReactomeExtended.__get_desc("get_pathway_desc", pathway_id)


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

    save_to_test_file('tests/query_test_data.json', 'REACT:R-HSA-70326', QueryReactomeExtended.get_pathway_entity('REACT:R-HSA-70326'))
    save_to_test_file('tests/query_desc_test_data.json', 'REACT:R-HSA-70326', QueryReactomeExtended.get_pathway_desc('REACT:R-HSA-70326'))
    save_to_test_file('tests/query_desc_test_data.json', 'REACT:R-HSA-703260', QueryReactomeExtended.get_pathway_desc('REACT:R-HSA-703260'))
    print(QueryReactomeExtended.get_pathway_desc('REACT:R-HSA-703260'))
