
''' This module defines the class QueryBioLinkExtended. QueryBioLinkExtended class is designed
to communicate with Monarch APIs and their corresponding data sources. The
available methods include:
    * query anatomy entity by ID
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


class QueryBioLinkExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://api.monarchinitiative.org/api/bioentity'
    HANDLER_MAP = {
        'get_anatomy': 'anatomy/{anatomy_id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryBioLinkExtended.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryBioLinkExtended.TIMEOUT_SEC)
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
    def get_anatomy_entity(anatomy_id):
        handler = QueryBioLinkExtended.HANDLER_MAP['get_anatomy'].format(anatomy_id=anatomy_id)
        results = QueryBioLinkExtended.__access_api(handler)
        result_str = 'UNKNOWN'
        if results is not None:
            result_str = str(results)
            #   replace double quotes with single quotes
            result_str = result_str.replace('"', "'")
        return result_str


if __name__ == '__main__':
    print(QueryBioLinkExtended.get_anatomy_entity('UBERON:0004476'))
