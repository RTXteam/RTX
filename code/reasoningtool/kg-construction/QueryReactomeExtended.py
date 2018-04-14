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


# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')


class QueryReactomeExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://reactome.org/ContentService'
    HANDLER_MAP = {
        'get_pathway': '/data/pathway/{id}/containedEvents',
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

        return res.json()

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryReactomeExtended.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryReactomeExtended.__access_api(handler)
        result_str = 'UNKNOWN'
        if results is not None:
            result_str = str(results)
            #   replace double quotes with single quotes
            result_str = result_str.replace("'", '"')
        return result_str

    @staticmethod
    def get_pathway_entity(pathway_id):
        return QueryReactomeExtended.__get_entity("get_pathway", pathway_id)


if __name__ == '__main__':
    print(QueryReactomeExtended.get_pathway_entity('R-HSA-5579024'))
