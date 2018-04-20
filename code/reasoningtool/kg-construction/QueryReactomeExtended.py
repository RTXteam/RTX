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

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')


class QueryReactomeExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://reactome.org/ContentService'
    HANDLER_MAP = {
        'get_pathway': 'data/pathway/{id}/containedEvents',
    }

    @staticmethod
    def __access_api(handler):

        url = QueryReactomeExtended.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryReactomeExtended.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryBioLink for URL: ' + url, file=sys.stderr)
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
        result_str = 'UNKNOWN'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    #   example of pathway_id: Reactome:R-HSA-70326
    def get_pathway_entity(pathway_id):
        if pathway_id[:9] == "Reactome:":
            pathway_id = pathway_id[9:]
        return QueryReactomeExtended.__get_entity("get_pathway", pathway_id)


if __name__ == '__main__':
    def save_to_test_file(key, value):
        f = open('tests/query_test_data.json', 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('Reactome:R-HSA-70326', QueryReactomeExtended.get_pathway_entity('Reactome:R-HSA-70326'))