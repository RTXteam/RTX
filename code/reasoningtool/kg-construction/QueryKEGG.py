''' This module defines the class QueryKEGG. QueryKEGG class is designed
to communicate with KEGG APIs and their corresponding data sources. The
available methods include:

*   map_kegg_compound_to_enzyme_commission_ids(kegg_id)

    Description:
        map kegg compond id to enzyme commission ids

    Args:
        kegg_id (str): The ID of the kegg compound, e.g., "KEGG:C00022"

    Returns:
        ids (set): a set of the enzyme commission ids, or empty set if no enzyme commission id can be obtained or the
                    response status code is not 200.
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
import sys


class QueryKEGG:
    TIMEOUT_SEC = 120
    API_BASE_URL = ' http://rest.kegg.jp'
    HANDLER_MAP = {
        'map_kegg_compound_to_enzyme_commission_ids': 'link/ec/{id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryKEGG.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryKEGG.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryKEGG for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryKEGG for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    # returns a list of dictionary, which contains a concept ID and a concept name, based on a single node label
    # like "acetaminophen" or "heart disease", or an empty list if no concept IDs could be obtained for the given label
    @staticmethod
    def map_kegg_compound_to_enzyme_commission_ids(kegg_id):
        res_set = set()
        if not isinstance(kegg_id, str):
            return res_set
        kegg_id = kegg_id[5:]
        handler = QueryKEGG.HANDLER_MAP['map_kegg_compound_to_enzyme_commission_ids'].format(id=kegg_id)
        res = QueryKEGG.__access_api(handler)
        if res is not None:
            tab_pos = res.find('\t')
            while tab_pos != -1:
                return_pos = res.find('\n')
                ec_id = res[tab_pos+1:return_pos]
                res_set.add(ec_id)
                res = res[return_pos+1:]
                tab_pos = res.find('\t')
        return res_set

if __name__ == '__main__':
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00022'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00100'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00200'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('GO:2342343'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids(1000))
